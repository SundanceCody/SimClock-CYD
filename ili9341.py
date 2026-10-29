# SPDX-License-Identifier: MIT
# See the LICENSE file; third-party notices are in THIRD_PARTY_NOTICES.md
# ili9341.py - minimal display driver for the ESP32-2432S028R ("CYD")
#
# Portions of this file (the display power-up register sequence) are derived
# from micropython-ili9341 by rdagger, used under the MIT License:
#   https://github.com/rdagger/micropython-ili9341
# The upstream copyright notice is in that project's LICENSE file; see also
# THIRD_PARTY_NOTICES.md. The rest of this file is original to SimClock.
#
# ORIENTATION: this CYD's panel is natively landscape (320 wide x 240 tall).
# On it the usual "swap rows/columns" bit (MV, 0x20) turns the picture into
# PORTRAIT, so it must stay CLEARED. Only the mirror bits are used:
#
#   MADCTL 0x08  native landscape, but mirrored   (not usable)
#   MADCTL 0x48  upright landscape  -> ROTATION 0
#   MADCTL 0x88  upright landscape, turned 180 degrees -> ROTATION 1
#   MADCTL 0xC8  mirrored the other way           (not usable)
#
# If your board behaves differently, run test_display.py and put the MADCTL
# value that looks right into MADCTL_OVERRIDE in main.py.
#
# Only what the SimClock needs is included: fill a rectangle and draw scaled
# text using MicroPython's built-in 8x8 font.

import time
import framebuf
from machine import Pin, SPI, PWM

BLACK = 0x0000
WHITE = 0xFFFF

# CYD (ESP32-2432S028R) display wiring
PIN_SCK = 14
PIN_MOSI = 13
PIN_MISO = 12
PIN_CS = 15
PIN_DC = 2
PIN_BACKLIGHT = 21  # a few board revisions use 27 instead

_MADCTL = {0: 0x48, 1: 0x88}


class ILI9341:
    WIDTH = 320   # landscape
    HEIGHT = 240

    def __init__(self, rotation=0, invert=False, baudrate=20_000_000, madctl=None,
                 backlight=100):
        self.spi = SPI(1, baudrate=baudrate, polarity=0, phase=0,
                       sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=Pin(PIN_MISO))
        self.cs = Pin(PIN_CS, Pin.OUT, value=1)
        self.dc = Pin(PIN_DC, Pin.OUT, value=0)
        self.backlight = Pin(PIN_BACKLIGHT, Pin.OUT, value=0)
        self._pwm = None

        self._glyph = bytearray(8)
        self._fb = framebuf.FrameBuffer(self._glyph, 8, 8, framebuf.MONO_HLSB)

        if madctl is None:
            madctl = _MADCTL.get(rotation, 0x48)
        self._init_display(madctl, invert)
        self.fill(BLACK)
        self.set_backlight(backlight)

    # --- low level -------------------------------------------------------
    def _cmd(self, cmd, data=None):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes((cmd,)))
        if data:
            self.dc.value(1)
            self.spi.write(data)
        self.cs.value(1)

    def _data(self, buf):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def _init_display(self, madctl, invert):
        self._cmd(0x01)                            # software reset
        time.sleep_ms(150)
        self._cmd(0xCF, b'\x00\xC1\x30')           # power control B
        self._cmd(0xED, b'\x64\x03\x12\x81')       # power-on sequence control
        self._cmd(0xE8, b'\x85\x00\x78')           # driver timing control A
        self._cmd(0xCB, b'\x39\x2C\x00\x34\x02')   # power control A
        self._cmd(0xF7, b'\x20')                   # pump ratio control
        self._cmd(0xEA, b'\x00\x00')               # driver timing control B
        self._cmd(0xC0, b'\x23')                   # power control 1
        self._cmd(0xC1, b'\x10')                   # power control 2
        self._cmd(0xC5, b'\x3E\x28')               # VCOM control 1
        self._cmd(0xC7, b'\x86')                   # VCOM control 2
        self._cmd(0x36, bytes((madctl,)))          # orientation / colour order
        self._cmd(0x37, b'\x00\x00')               # vertical scroll start
        self._cmd(0x3A, b'\x55')                   # 16-bit colour
        self._cmd(0xB1, b'\x00\x18')               # frame rate
        self._cmd(0xB6, b'\x08\x82\x27')           # display function control
        self._cmd(0xF2, b'\x00')                   # 3-gamma off
        self._cmd(0x26, b'\x01')                   # gamma curve
        self._cmd(0xE0, b'\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00')
        self._cmd(0xE1, b'\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F')
        self._cmd(0x11)                            # sleep out
        time.sleep_ms(120)
        self._cmd(0x21 if invert else 0x20)        # inversion on/off
        self._cmd(0x29)                            # display on
        time.sleep_ms(100)

    def set_backlight(self, percent):
        """Backlight brightness, 5-100 %. 100 = plain on (no PWM)."""
        percent = max(5, min(100, int(percent)))
        if percent >= 100:
            if self._pwm is not None:
                self._pwm.deinit()
                self._pwm = None
            self.backlight = Pin(PIN_BACKLIGHT, Pin.OUT, value=1)
            return
        duty = percent * 65535 // 100
        if self._pwm is None:
            self._pwm = PWM(Pin(PIN_BACKLIGHT), freq=5000, duty_u16=duty)
        else:
            self._pwm.duty_u16(duty)

    def set_madctl(self, value):
        """Change orientation / colour order on the fly (used by test_display.py)."""
        self._cmd(0x36, bytes((value,)))

    def set_invert(self, on):
        self._cmd(0x21 if on else 0x20)

    def _window(self, x0, y0, x1, y1):
        self._cmd(0x2A, bytes((x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)))
        self._cmd(0x2B, bytes((y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF)))
        self._cmd(0x2C)

    # --- drawing ---------------------------------------------------------
    def fill_rect(self, x, y, w, h, color):
        # clip to the screen so a bad window can never garble the display
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        w = min(w, self.WIDTH - x)
        h = min(h, self.HEIGHT - y)
        if w <= 0 or h <= 0:
            return
        self._window(x, y, x + w - 1, y + h - 1)
        total = w * h
        n = min(total, 1024)
        chunk = bytes((color >> 8, color & 0xFF)) * n
        view = memoryview(chunk)
        self.dc.value(1)
        self.cs.value(0)
        while total > 0:
            k = min(total, n)
            self.spi.write(view[:k * 2])
            total -= k
        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.WIDTH, self.HEIGHT, color)

    def char(self, ch, x, y, scale=1, fg=WHITE, bg=BLACK):
        """Draw one 8x8 character, enlarged by 'scale', at pixel (x, y)."""
        size = 8 * scale
        if x < 0 or y < 0 or x + size > self.WIDTH or y + size > self.HEIGHT:
            return
        fb = self._fb
        fb.fill(0)
        fb.text(ch, 0, 0, 1)
        fgb = bytes((fg >> 8, fg & 0xFF)) * scale
        bgb = bytes((bg >> 8, bg & 0xFF)) * scale
        rowlen = size * 2
        out = bytearray(rowlen * size)
        pos = 0
        for r in range(8):
            bits = self._glyph[r]
            row = b''.join(fgb if (bits >> (7 - c)) & 1 else bgb for c in range(8))
            for _ in range(scale):
                out[pos:pos + rowlen] = row
                pos += rowlen
        self._window(x, y, x + size - 1, y + size - 1)
        self._data(out)

    def text(self, s, x, y, scale=1, fg=WHITE, bg=BLACK):
        for i, ch in enumerate(s):
            self.char(ch, x + i * 8 * scale, y, scale, fg, bg)
