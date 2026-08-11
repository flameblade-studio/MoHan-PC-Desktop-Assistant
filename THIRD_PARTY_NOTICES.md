# 第三方聲明／第三方声明／Third-Party Notices／第三者ソフトウェアに関する通知

## 繁體中文

### 概要

MoHan Desktop Assistant 採用 MIT License，但其原始碼及 Release 安裝包會使用依各自授權條款提供的第三方元件。`LICENSE` 中的墨寒 MIT License 不會變更這些第三方條款。

### 直接 Python 相依套件

| 元件 | 目前固定版本 | 授權 |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 條款） |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

### Preview 封裝工具

Linux x86_64 功能受限 Preview 使用官方 [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) 組裝。建置流程會下載上游 `continuous` x86_64 資產，但只有在其 SHA-256 等於 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` 時才接受。所記錄的上游來源 commit 為 `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`，GitHub 資產 ID 為 `324406882`。

`appimagetool` 仍受其自身的上游授權條款約束。

### 封裝所含執行階段元件

Windows 單一目錄安裝包亦可能包含 Python（PSF License）、Qt 及 Shiboken（LGPL／GPL／商業條款）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain），以及它們所需的執行階段函式庫。macOS 與 Linux 功能受限 Preview 安裝包只包含 `requirements-preview.txt` 宣告的較小 Preview 相依集合。

封裝版面會將動態連結的 Qt／PySide 函式庫保留為 `_internal` 下的獨立檔案，讓接收者可以檢查或替換這些函式庫。對應的 Qt for Python 原始碼 Release 可從 [Qt 官方下載封存](https://download.qt.io/official_releases/QtForPython/)取得。

完整授權文字及原始碼連結可在各上游專案與已安裝套件的中繼資料中取得。散布者應檢查實際交付的精確相依版本，並保留所有上游著作權及授權聲明。

### Windows 安裝程式語言檔

隨附的 `installer/languages/ChineseTraditional.isl` 是來自 [Inno Setup 原始碼儲存庫](https://github.com/jrsoftware/issrc)的官方繁體中文訊息翻譯，固定於來源 commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）。該檔案依 [Inno Setup 授權](https://jrsoftware.org/files/is/license.txt)散布，並保留檔頭中的上游翻譯者資訊。

### 服務與商標

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE 及其他服務名稱均為其各自權利人的商標。API 存取、雲端生成語音、OAuth 使用及服務配額均受各供應商自身條款約束。

## 简体中文

### 概要

MoHan Desktop Assistant 采用 MIT License，但其源代码及 Release 安装包会使用依各自许可条款提供的第三方组件。`LICENSE` 中的墨寒 MIT License 不会变更这些第三方条款。

### 直接 Python 依赖包

| 组件 | 当前固定版本 | 许可 |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 条款） |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

### Preview 封装工具

Linux x86_64 功能受限 Preview 使用官方 [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) 组装。构建流程会下载上游 `continuous` x86_64 资产，但只有在其 SHA-256 等于 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` 时才接受。所记录的上游源 commit 为 `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`，GitHub 资产 ID 为 `324406882`。

`appimagetool` 仍受其自身的上游许可条款约束。

### 封装所含运行时组件

Windows 单一目录安装包也可能包含 Python（PSF License）、Qt 及 Shiboken（LGPL／GPL／商业条款）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain），以及它们所需的运行时库。macOS 与 Linux 功能受限 Preview 安装包只包含 `requirements-preview.txt` 声明的较小 Preview 依赖集合。

封装布局会将动态链接的 Qt／PySide 库保留为 `_internal` 下的独立文件，让接收者可以检查或替换这些库。对应的 Qt for Python 源代码 Release 可从 [Qt 官方下载存档](https://download.qt.io/official_releases/QtForPython/)取得。

完整许可文本及源代码链接可在各上游项目与已安装软件包的元数据中取得。分发者应检查实际交付的精确依赖版本，并保留所有上游著作权及许可声明。

### Windows 安装程序语言文件

随附的 `installer/languages/ChineseTraditional.isl` 是来自 [Inno Setup 源代码仓库](https://github.com/jrsoftware/issrc)的官方繁体中文消息翻译，固定于源 commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）。该文件依 [Inno Setup 许可](https://jrsoftware.org/files/is/license.txt)分发，并保留文件头中的上游翻译者信息。

### 服务与商标

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE 及其他服务名称均为其各自权利人的商标。API 访问、云端生成语音、OAuth 使用及服务配额均受各提供商自身条款约束。

## English

### Overview

MoHan Desktop Assistant is MIT licensed, but its source and Release packages use third-party components under their own license terms. Nothing in the MoHan MIT License in `LICENSE` changes those third-party terms.

### Direct Python dependencies

| Component | Current pinned version | License |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License (Microsoft Speech SDK terms) |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

### Preview packaging tool

The Linux x86_64 limited Preview is assembled with the official [AppImage `appimagetool`](https://github.com/AppImage/appimagetool). The build downloads the upstream `continuous` x86_64 asset but accepts it only when its SHA-256 equals `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`. The recorded upstream source commit is `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`, and the GitHub asset ID is `324406882`.

`appimagetool` remains governed by its own upstream license.

### Runtime components included by packaging

The Windows one-directory package may also contain Python (PSF License), Qt and Shiboken (LGPL/GPL/commercial terms), NumPy (BSD-3-Clause), CFFI (MIT), PortAudio (MIT), OpenSSL (Apache-2.0), SQLite (public domain), and their required runtime libraries. The macOS and Linux limited Preview packages contain only the smaller Preview dependency set declared in `requirements-preview.txt`.

The packaged layout keeps dynamically linked Qt/PySide libraries as separate files under `_internal`, so recipients can inspect or replace those libraries. Corresponding Qt for Python source releases are available from the [official Qt download archive](https://download.qt.io/official_releases/QtForPython/).

Complete license texts and source links are available in each upstream project and installed package metadata. Distributors should review the exact dependency versions they ship and preserve all upstream copyright and license notices.

### Windows installer language file

The bundled `installer/languages/ChineseTraditional.isl` file is the official Traditional Chinese message translation from the [Inno Setup source repository](https://github.com/jrsoftware/issrc), pinned to source commit `0c0b463621963243e430420b6c633039e562e1e3` (blob `8eb13d2c45e9d434aa5435a2877234418186ad87`). It is distributed under the [Inno Setup license](https://jrsoftware.org/files/is/license.txt) and retains its upstream translator credits in the file header.

### Services and trademarks

OpenAI, Microsoft, Google, GitHub, Home Assistant, LINE, and other service names are trademarks of their respective owners. API access, cloud-generated voices, OAuth use, and service quotas are governed by each provider's own terms.

## 日本語

### 概要

MoHan Desktop Assistant は MIT License で提供されますが、そのソースコードと Release パッケージは、独自のライセンス条件を持つ第三者コンポーネントを使用します。`LICENSE` に記載された墨寒の MIT License が、それらの第三者条件を変更することはありません。

### Python の直接依存パッケージ

| コンポーネント | 現在の固定バージョン | ライセンス |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 条件） |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |

### Preview パッケージ作成ツール

Linux x86_64 の機能制限付き Preview は、公式の [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) で組み立てられます。ビルドは上流の `continuous` x86_64 アセットをダウンロードしますが、その SHA-256 が `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` と一致する場合にのみ受け入れます。記録されている上流ソースの commit は `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`、GitHub アセット ID は `324406882` です。

`appimagetool` には、引き続き上流独自のライセンスが適用されます。

### パッケージに含まれるランタイムコンポーネント

Windows のワンディレクトリパッケージには、Python（PSF License）、Qt および Shiboken（LGPL／GPL／商用条件）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain）、ならびにそれらに必要なランタイムライブラリが含まれる場合があります。macOS および Linux の機能制限付き Preview パッケージには、`requirements-preview.txt` で宣言された小規模な Preview 依存セットだけが含まれます。

パッケージでは、動的リンクされる Qt／PySide ライブラリを `_internal` 配下の個別ファイルとして保持するため、受領者はこれらのライブラリを確認または置換できます。対応する Qt for Python のソース Release は、[Qt 公式ダウンロードアーカイブ](https://download.qt.io/official_releases/QtForPython/)から取得できます。

完全なライセンス本文とソースへのリンクは、各上流プロジェクトおよびインストール済みパッケージのメタデータで確認できます。配布者は、実際に出荷する正確な依存バージョンを確認し、上流の著作権表示とライセンス表示をすべて保持してください。

### Windows インストーラーの言語ファイル

同梱の `installer/languages/ChineseTraditional.isl` は、[Inno Setup ソースリポジトリ](https://github.com/jrsoftware/issrc)による公式の繁体字中国語メッセージ翻訳であり、ソース commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）に固定されています。このファイルは [Inno Setup ライセンス](https://jrsoftware.org/files/is/license.txt)に基づいて配布され、ファイルヘッダーにある上流翻訳者のクレジットを保持します。

### サービスと商標

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE、およびその他のサービス名は、それぞれの権利者の商標です。API アクセス、クラウド生成音声、OAuth の使用、サービス利用枠には、各プロバイダー独自の規約が適用されます。
