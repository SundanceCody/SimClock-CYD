# SPDX-License-Identifier: MIT
# See the LICENSE file; third-party notices are in THIRD_PARTY_NOTICES.md
# test_display.py - check the screen orientation
#
# 1. In Thonny, stop main.py (Ctrl+C), then open this file and press Run (F5).
# 2. Turn the board to LANDSCAPE (long side horizontal). It shows 4 test
#    screens, 4 seconds each. Look for the screen that is upright, readable
#    (NOT mirrored), black background, white text, and fills the whole screen
#    with no static. Each screen has coloured squares in its corners:
#        top-left = red, top-right = green, bottom-right = blue, bottom-left = yellow
# 3. The console and the screen show the MADCTL value. Use it like this in main.py:
#        MADCTL_OVERRIDE = 0x48      (or whichever value looked right)
#    If it is 0x48 or 0x88 you can instead just use ROTATION = 0 (0x48) or 1 (0x88).

import time
import ili9341
from ili9341 import BLACK

RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0

# All four landscape variants (the swap bit 0x20 is left CLEARED on purpose).
VARIANTS = [0x48, 0x88, 0x08, 0xC8]

tft = ili9341.ILI9341(madctl=0x48)
W, H = tft.WIDTH, tft.HEIGHT

for n, madctl in enumerate(VARIANTS, 1):
    tft.set_madctl(madctl)
    tft.fill(BLACK)
    s = 30
    tft.fill_rect(0, 0, s, s, RED)
    tft.fill_rect(W - s, 0, s, s, GREEN)
    tft.fill_rect(W - s, H - s, s, s, BLUE)
    tft.fill_rect(0, H - s, s, s, YELLOW)
    tft.text("#%d" % n, 112, 60, 6)
    tft.text("MADCTL = 0x%02X" % madctl, 96, 130, 2)
    tft.text("Upright and readable?", 56, 160, 2)
    print("Screen #%d: MADCTL=0x%02X" % (n, madctl))
    time.sleep(4)

print("Done. Use the MADCTL value of the screen that looked right.")
