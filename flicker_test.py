# SPDX-License-Identifier: MIT
# See the LICENSE file; third-party notices are in THIRD_PARTY_NOTICES.md
# flicker_test.py - find out what causes the faint flicker
#
# 1. In Thonny, stop main.py (Ctrl+C), open this file and press Run (F5).
# 2. The screen turns plain grey (easiest to spot flicker on) with a small label.
#    Nothing is redrawn during a phase, so any flicker is NOT caused by drawing.
# 3. Watch the screen during each 30-second phase and note in which phases you
#    still see the faint flicker:
#
#      A  Wi-Fi OFF                       <- if it flickers here, it is not Wi-Fi
#                                            (try another USB cable / port / charger)
#      B  Wi-Fi ON, full power (20 dBm)   <- the current default behaviour
#      C  Wi-Fi ON, 11 dBm                <- main.py's new default
#      D  Wi-Fi ON, 20 dBm, light at 60%
#      E  Wi-Fi ON, 11 dBm, light at 60%
#
# Then set WIFI_TX_POWER and BACKLIGHT_PERCENT in main.py to the quietest phase.

import time
import network
import ili9341

ROTATION = 0        # same as in main.py
PHASE_SECONDS = 30

GREY = 0x8410
BLACK = 0x0000

# (label, wifi tx power in dBm or None for off, backlight %)
PHASES = [
    ("A  Wi-Fi OFF", None, 100),
    ("B  Wi-Fi ON 20 dBm", 20, 100),
    ("C  Wi-Fi ON 11 dBm", 11, 100),
    ("D  20 dBm, light 60%", 20, 60),
    ("E  11 dBm, light 60%", 11, 60),
]

tft = ili9341.ILI9341(rotation=ROTATION)
ap = network.WLAN(network.AP_IF)
ap.active(False)

for label, power, level in PHASES:
    if power is None:
        ap.active(False)
    else:
        ap.active(True)
        ap.config(essid="SimClock", password="simulation",
                  authmode=network.AUTH_WPA_WPA2_PSK)
        ap.config(txpower=power)
    tft.set_backlight(level)
    tft.fill(GREY)
    tft.text(label, 8, 8, 2, BLACK, GREY)
    print("Phase:", label)
    time.sleep(PHASE_SECONDS)

ap.active(False)
tft.set_backlight(100)
tft.fill(BLACK)
tft.text("Test finished", 8, 8, 2)
print("Done. Tell me in which phases you saw the flicker.")
