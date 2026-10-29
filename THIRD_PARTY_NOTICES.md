# Third-party notices

SimClock is released under the MIT License (see `LICENSE`). It contains or
relies on the following third-party material.

## micropython-ili9341 by rdagger  (MIT License)

- Source: https://github.com/rdagger/micropython-ili9341
- Used in: `ili9341.py`. The display power-up register sequence follows the one
  in this library. No other code was copied; the drawing, text and
  orientation code is original to this project.
- Licence: MIT. The upstream copyright notice is in that repository's LICENSE
  file: https://github.com/rdagger/micropython-ili9341/blob/master/LICENSE
  (Paste the exact copyright line from that file below if you redistribute
  this project outside your organisation.)

    Upstream copyright line:
	MIT License

	Copyright (c) 2020

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
	SOFTWARE.

## MicroPython  (MIT License)

- https://micropython.org - the firmware the clock runs on. Not included in
  this project; modules used at runtime (`framebuf`, `network`, `asyncio`,
  `machine`, `json`, `socket`, `time`) come from the firmware. The 8x8 text
  font drawn on the screen is the one built into MicroPython's `framebuf`.

## Not used

No third-party JavaScript, CSS, fonts, images or CDN resources are used by the
web page. The fast-forward symbol is the Unicode character U+23E9.
