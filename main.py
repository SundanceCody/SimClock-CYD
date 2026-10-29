# SPDX-License-Identifier: MIT
# See the LICENSE file; third-party notices are in THIRD_PARTY_NOTICES.md
# main.py - SimClock for the ESP32-2432S028R (CYD)
#
# * Wi-Fi access point "SimClock" at 10.0.0.1
# * Tiny web server + DNS "catch-all" so phones/laptops pop up the page
#   automatically (captive portal)
# * Software clock (starts 12:00 AM, Jan 1, 2000) shown on the CYD screen
#
# Files that must be on the board (same folder, i.e. the root):
#   main.py  ili9341.py  index.html  style.css  script.js

import gc
import json
import socket
import time
import network
from machine import RTC

try:
    import asyncio
except ImportError:          # older MicroPython builds
    import uasyncio as asyncio

# ---------------------------------------------------------------- settings
SSID = "SimClock"
PASSWORD = "simulation"
IP = "10.0.0.1"
NETMASK = "255.255.255.0"

ROTATION = 0           # landscape. If the screen is upside down, use 1.
INVERT_COLORS = False  # set True if black/white appear swapped
MADCTL_OVERRIDE = None # advanced: value found with test_display.py (e.g. 0x88);
                       # when set, it replaces ROTATION
SHOW_SECONDS = True    # show seconds on the CYD screen, beside the AM/PM

# Faint-flicker mitigation (see flicker_test.py to find what helps on your board)
WIFI_TX_POWER = 11     # Wi-Fi transmit power in dBm (2-20). Lower = smaller current
                       # spikes, shorter range. 11 is plenty for one room. None = default.
BACKLIGHT_PERCENT = 100  # 5-100. Dimming the backlight also lowers current draw.

FAST_FORWARD_SECONDS = 5 * 60
MIN_YEAR, MAX_YEAR = 2000, 2050

DAYS = ("Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun.")

# ------------------------------------------------------------------- clock
rtc = RTC()


def set_clock(lt):
    """lt is a time.localtime()-style tuple."""
    rtc.datetime((lt[0], lt[1], lt[2], lt[6], lt[3], lt[4], lt[5], 0))


def fmt_time(tm, seconds=True):
    h12 = tm[3] % 12 or 12
    ampm = "AM" if tm[3] < 12 else "PM"
    if seconds:
        return "%d:%02d:%02d %s" % (h12, tm[4], tm[5], ampm)
    return "%d:%02d %s" % (h12, tm[4], ampm)


def fmt_date(tm):
    return "%s %02d/%02d/%04d" % (DAYS[tm[6]], tm[1], tm[2], tm[0])


# Start at 12:00 AM, January 1, 2000
set_clock(time.localtime(time.mktime((2000, 1, 1, 0, 0, 0, 0, 0))))

# ----------------------------------------------------------------- Wi-Fi AP
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, password=PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
try:
    ap.config(max_clients=8)
except Exception:
    pass
if WIFI_TX_POWER is not None:
    try:
        ap.config(txpower=WIFI_TX_POWER)
    except Exception as e:
        print("Could not set Wi-Fi TX power:", repr(e))
# (ip, netmask, gateway, dns) - DNS points back at us for the captive portal
ap.ifconfig((IP, NETMASK, IP, IP))
print("Access point up:", SSID, ap.ifconfig())

# ----------------------------------------------------------------- display
try:
    import ili9341
    tft = ili9341.ILI9341(rotation=ROTATION, invert=INVERT_COLORS,
                          madctl=MADCTL_OVERRIDE, backlight=BACKLIGHT_PERCENT)
except Exception as e:
    print("Display init failed:", repr(e))
    tft = None

BIG = 6        # scale for HH:MM  (48 px tall)
SMALL = 3      # scale for seconds / AM-PM (24 px tall)
DATE = 2       # scale for the date line (16 px tall)
GAP = 8
TIME_Y = 76
DATE_Y = TIME_Y + 8 * BIG + 24

_last = {"layout": None, "big": "", "sec": "", "ampm": "", "date": ""}


def draw_diff(text, old, x0, y, scale):
    """Draw only the characters that changed (fixed-width font)."""
    for i, ch in enumerate(text):
        if i >= len(old) or old[i] != ch:
            tft.char(ch, x0 + i * 8 * scale, y, scale)


def render():
    if tft is None:
        return
    tm = time.localtime()
    big = "%d:%02d" % (tm[3] % 12 or 12, tm[4])
    ampm = "AM" if tm[3] < 12 else "PM"
    sec = "%02d" % tm[5] if SHOW_SECONDS else ""
    date = fmt_date(tm)

    big_w = len(big) * 8 * BIG
    total_w = big_w + GAP + 2 * 8 * SMALL
    x0 = (tft.WIDTH - total_w) // 2
    small_x = x0 + big_w + GAP

    if _last["layout"] != len(big):          # width changed (e.g. 9:59 -> 10:00)
        tft.fill_rect(0, TIME_Y, tft.WIDTH, 8 * BIG, 0x0000)
        _last["layout"] = len(big)
        _last["big"] = _last["sec"] = _last["ampm"] = ""

    draw_diff(big, _last["big"], x0, TIME_Y, BIG)
    draw_diff(sec, _last["sec"], small_x, TIME_Y, SMALL)
    draw_diff(ampm, _last["ampm"], small_x, TIME_Y + 8 * BIG - 8 * SMALL, SMALL)
    date_x = (tft.WIDTH - len(date) * 8 * DATE) // 2
    draw_diff(date, _last["date"], date_x, DATE_Y, DATE)

    _last["big"], _last["sec"], _last["ampm"], _last["date"] = big, sec, ampm, date


async def display_task():
    while True:
        try:
            render()
        except Exception as e:
            print("render error:", repr(e))
        await asyncio.sleep_ms(100)


# --------------------------------------------------------- captive-portal DNS
class CaptiveDNS:
    """Answers every DNS lookup with our own IP address."""

    def __init__(self, ip):
        self.ip = bytes(int(p) for p in ip.split("."))

    def answer(self, q):
        if len(q) < 17:
            return None
        i = 12
        while i < len(q) and q[i] != 0:      # walk the question name
            i += q[i] + 1
        qend = i + 5
        if qend > len(q):
            return None
        qtype = (q[i + 1] << 8) | q[i + 2]
        question = q[12:qend]
        if qtype == 1:                        # A record -> our IP
            return (q[0:2] + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00" + question +
                    b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + self.ip)
        # anything else (AAAA etc.): empty answer so clients fall back to IPv4
        return q[0:2] + b"\x81\x80\x00\x01\x00\x00\x00\x00\x00\x00" + question

    async def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind(("0.0.0.0", 53))
        while True:
            try:
                data, addr = sock.recvfrom(256)
            except OSError:
                await asyncio.sleep_ms(20)
                continue
            try:
                reply = self.answer(data)
                if reply:
                    sock.sendto(reply, addr)
            except Exception as e:
                print("dns error:", repr(e))


# ---------------------------------------------------------------- web server
TYPES = {
    "html": "text/html; charset=utf-8",
    "css": "text/css; charset=utf-8",
    "js": "application/javascript; charset=utf-8",
}


async def respond(writer, status, ctype, body=b"", extra=""):
    if isinstance(body, str):
        body = body.encode()
    head = ("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n%s\r\n"
            % (status, ctype, len(body), extra))
    writer.write(head.encode())
    if body:
        writer.write(body)
    await writer.drain()


async def send_file(writer, name):
    try:
        with open(name, "rb") as f:
            body = f.read()
    except OSError:
        await respond(writer, "404 Not Found", "text/plain", "Missing file: " + name)
        return
    await respond(writer, "200 OK", TYPES[name.rsplit(".", 1)[1]], body)


def api_set(body):
    d = json.loads(body)
    y, mo, da, h, mi = int(d["y"]), int(d["mo"]), int(d["d"]), int(d["h"]), int(d["mi"])
    if not (MIN_YEAR <= y <= MAX_YEAR and 1 <= mo <= 12 and 1 <= da <= 31
            and 0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError("out of range")
    lt = time.localtime(time.mktime((y, mo, da, h, mi, 0, 0, 0)))
    if lt[1] != mo or lt[2] != da:           # e.g. Feb 30 rolled over
        raise ValueError("invalid date")
    set_clock(lt)


async def route(writer, method, path, host, body):
    # Anything not addressed to us (captive-portal probes, random sites)
    # is bounced to our page.
    if host != IP:
        await respond(writer, "302 Found", "text/plain", "",
                      "Location: http://%s/\r\n" % IP)
        return

    if method == "GET":
        if path in ("/", "/index.html"):
            return await send_file(writer, "index.html")
        if path == "/style.css":
            return await send_file(writer, "style.css")
        if path == "/script.js":
            return await send_file(writer, "script.js")
        if path == "/api/time":
            tm = time.localtime()
            return await respond(writer, "200 OK", "application/json",
                                 json.dumps({"time": fmt_time(tm), "date": fmt_date(tm)}))
    elif method == "POST":
        if path == "/api/set":
            try:
                api_set(body)
            except Exception as e:
                print("set error:", repr(e))
                return await respond(writer, "400 Bad Request", "application/json",
                                     json.dumps({"ok": False, "error": "Invalid date or time"}))
            return await respond(writer, "200 OK", "application/json", '{"ok": true}')
        if path == "/api/ff":
            set_clock(time.localtime(time.time() + FAST_FORWARD_SECONDS))
            return await respond(writer, "200 OK", "application/json", '{"ok": true}')

    await respond(writer, "404 Not Found", "text/plain", "Not found")


async def handle(reader, writer):
    try:
        line = await asyncio.wait_for(reader.readline(), 5)
        if not line:
            return
        parts = line.decode().split()
        if len(parts) < 2:
            return
        method, target = parts[0], parts[1]
        headers = {}
        for _ in range(40):
            h = await asyncio.wait_for(reader.readline(), 5)
            if not h or h in (b"\r\n", b"\n"):
                break
            k, sep, v = h.decode().partition(":")
            headers[k.strip().lower()] = v.strip()
        body = b""
        n = int(headers.get("content-length", "0") or 0)
        if 0 < n <= 1024:
            body = await asyncio.wait_for(reader.readexactly(n), 5)
        path = target.split("?")[0]
        host = headers.get("host", "").split(":")[0]
        await route(writer, method, path, host, body)
    except Exception as e:
        print("request error:", repr(e))
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        gc.collect()


async def main():
    await asyncio.start_server(handle, "0.0.0.0", 80)
    asyncio.create_task(CaptiveDNS(IP).run())
    asyncio.create_task(display_task())
    print("SimClock running. Connect to Wi-Fi '%s' and open http://%s/" % (SSID, IP))
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
