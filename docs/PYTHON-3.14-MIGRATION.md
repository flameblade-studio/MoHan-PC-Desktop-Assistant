# Python 3.14 遷移／Python 3.14 迁移／Python 3.14 migration／Python 3.14 移行

## 繁體中文

`v2.1.0-rc.1` 的原始碼、Windows CI、安全稽核與正式封裝統一使用
Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由專案內部的 PCM16 音訊層取代，涵蓋音量
調整、立體聲轉單聲道及 Realtime 串流重採樣，讓第三方供應鏈依賴集合維持原狀。

升級會完整保留使用者資料庫及其現有位置。既有 RC3 的設定、對話、記憶與工作資料仍
沿用原本位置。Python 3.12 的用途限定為開發回歸參考；`v2.1.0-rc.1` 發布物統一
以 Python 3.14.x 封裝。若需回復舊版，只替換程式本體並安裝經驗證的先前版本，
使用者資料目錄保持完整。

## 简体中文

`v2.1.0-rc.1` 的源代码、Windows CI、安全审计与正式打包统一使用
Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由项目内部的 PCM16 音频层取代，涵盖音量
调整、立体声转单声道及 Realtime 流式重采样，让第三方供应链依赖集合保持原状。

升级会完整保留用户数据库及其现有位置。已有 RC3 的设置、对话、记忆与工作数据继续
使用原有位置。Python 3.12 的用途限定为开发回归参考；`v2.1.0-rc.1` 发布文件统一
使用 Python 3.14.x 打包。若需要回退，只替换程序本体并安装已验证的先前
版本，用户数据目录保持完整。

## English

`v2.1.0-rc.1` standardizes source validation, Windows CI, security auditing,
and release packaging on Python 3.14.x. The `audioop` module removed in Python 3.13 is
replaced by an in-project PCM16 layer for gain, stereo-to-mono mixing, and
stateful Realtime stream resampling. This keeps the third-party supply-chain dependency set unchanged.

The upgrade preserves the user database and its current location. Existing RC3
settings, conversations, memories, and work data keep their current location.
Python 3.12 is scoped to development regression reference;
`v2.1.0-rc.1` artifacts use Python 3.14.x for packaging. To roll back, replace the application with a previously verified version while preserving the
user data directory.

## 日本語

`v2.1.0-rc.1` のソース検証、Windows CI、セキュリティ監査、配布物は
Python 3.14.x に統一されています。Python 3.13 で削除された `audioop` は、
音量調整、ステレオからモノラルへの変換、Realtime ストリームの状態付き
リサンプリングを行うプロジェクト内の PCM16 層へ置き換えました。外部依存関係の集合を従来どおり維持します。

この移行では利用者データベースと現在の保存場所を完全に維持します。RC3 で保存された
設定、会話、記憶、作業データも同じ場所で引き続き利用します。Python 3.12 の用途は開発時の回帰確認に限定し、`v2.1.0-rc.1` の配布物は Python 3.14.x で統一します。
以前の版へ戻す場合も、利用者データを完全に保持し、アプリ本体だけを入れ替えてください。
