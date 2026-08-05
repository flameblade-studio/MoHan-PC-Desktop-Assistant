# Third-party notices

MoHan Desktop Assistant is MIT licensed, but its source and release packages
use third-party components under their own licenses. Nothing in the MoHan MIT
License changes those terms.

## Direct Python dependencies

| Component | Current pinned version | License |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

## Preview packaging tool

The Linux x86_64 limited Preview is assembled with the official
[AppImage `appimagetool`](https://github.com/AppImage/appimagetool). The build
downloads the upstream `continuous` x86_64 asset but accepts it only when its
SHA-256 is
`a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`.
The recorded upstream source commit is
`8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81` and the GitHub asset ID is
`324406882`. `appimagetool` remains governed by its own upstream license.

## Runtime components included by packaging

The Windows one-directory package may also contain Python (PSF License), Qt and
Shiboken (LGPL/GPL/commercial terms), NumPy (BSD-3-Clause), CFFI (MIT),
PortAudio (MIT), OpenSSL (Apache-2.0), SQLite (public domain), and their required
runtime libraries. The macOS and Linux limited Preview packages contain only
the smaller Preview dependency set declared in `requirements-preview.txt`.

The packaged layout keeps dynamically linked Qt/PySide libraries as separate
files under `_internal`, so recipients can inspect or replace those libraries.
Corresponding Qt for Python source releases are available from the
[official Qt download archive](https://download.qt.io/official_releases/QtForPython/).

Complete license texts and source links are available in each upstream project
and installed package metadata. Distributors should review the exact dependency
versions they ship and preserve all upstream copyright and license notices.

## Windows installer language

The bundled `installer/languages/ChineseTraditional.isl` file is the official
Traditional Chinese message translation from the
[Inno Setup source repository](https://github.com/jrsoftware/issrc), pinned to
source commit `0c0b463621963243e430420b6c633039e562e1e3` (blob
`8eb13d2c45e9d434aa5435a2877234418186ad87`). It is distributed under the
[Inno Setup license](https://jrsoftware.org/files/is/license.txt) and retains
its upstream translator credits in the file header.

## Services and trademarks

OpenAI, Microsoft, Google, GitHub, Home Assistant, LINE, and other service names
are trademarks of their respective owners. API access, cloud-generated voices,
OAuth use, and service quotas are governed by the provider's own terms.
