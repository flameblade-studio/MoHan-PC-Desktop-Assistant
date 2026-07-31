# Third-party notices

MoHan Desktop Assistant is MIT licensed, but its source and Windows package use
third-party components under their own licenses. Nothing in the MoHan MIT
License changes those terms.

## Direct Python dependencies

| Component | Version used for v2.0.10 RC | License |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.3 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

## Runtime components included by packaging

The Windows one-directory package may also contain Python (PSF License), Qt and
Shiboken (LGPL/GPL/commercial terms), NumPy (BSD-3-Clause), CFFI (MIT),
PortAudio (MIT), OpenSSL (Apache-2.0), SQLite (public domain), and their required
runtime libraries.

The packaged layout keeps dynamically linked Qt/PySide libraries as separate
files under `_internal`, so recipients can inspect or replace those libraries.
Corresponding Qt for Python source releases are available from the
[official Qt download archive](https://download.qt.io/official_releases/QtForPython/).

Complete license texts and source links are available in each upstream project
and installed package metadata. Distributors should review the exact dependency
versions they ship and preserve all upstream copyright and license notices.

## Services and trademarks

OpenAI, Microsoft, Google, GitHub, Home Assistant, LINE, and other service names
are trademarks of their respective owners. API access, cloud-generated voices,
OAuth use, and service quotas are governed by the provider's own terms.
