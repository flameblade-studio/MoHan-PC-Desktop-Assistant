# Python 3.14 migration / Python 3.14 遷移 / Python 3.14 迁移

## 繁體中文

RC4 的原始碼、Windows CI、安全稽核與正式封裝統一使用 Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由專案內部的 PCM16 音訊層取代，涵蓋音量
調整、立體聲轉單聲道及 Realtime 串流重採樣，避免增加新的第三方供應鏈依賴。

升級不會搬移或重建使用者資料庫。RC3 的設定、對話、記憶與工作資料仍沿用
既有資料位置。開發期間保留 Python 3.12 環境只供回歸與回復驗證；RC4 安裝包
不得以 Python 3.12 封裝。若 RC4 候選版驗證失敗，可移除 RC4 並重新執行已
驗證的 RC3 安裝包，且不得刪除使用者資料目錄。

## 简体中文

RC4 的源代码、Windows CI、安全审计与正式打包统一使用 Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由项目内部的 PCM16 音频层取代，涵盖音量
调整、立体声转单声道及 Realtime 流式重采样，避免增加新的第三方供应链依赖。

升级不会迁移或重建用户数据库。RC3 的设置、对话、记忆与工作数据继续使用
原有数据位置。开发期间保留 Python 3.12 环境仅用于回归与回退验证；RC4 安装
包不得使用 Python 3.12 打包。若 RC4 候选版验证失败，可移除 RC4 并重新运行
已验证的 RC3 安装包，同时不得删除用户数据目录。

## English

RC4 standardizes source validation, Windows CI, security auditing, and release
packaging on Python 3.14.x. The `audioop` module removed in Python 3.13 is
replaced by an in-project PCM16 layer for gain, stereo-to-mono mixing, and
stateful Realtime stream resampling. This avoids adding another third-party
supply-chain dependency.

The upgrade neither moves nor recreates the user database. Existing RC3
settings, conversations, memories, and work data keep their current location.
Python 3.12 remains available during development only for regression and
rollback validation; RC4 artifacts must not be packaged with it. If RC4
candidate validation fails, remove RC4 and reinstall the verified RC3 package
without deleting the user data directory.
