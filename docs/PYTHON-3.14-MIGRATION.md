# Python 3.14 migration / Python 3.14 遷移 / Python 3.14 迁移 / Python 3.14 移行

## 繁體中文

`v2.1.0-rc.1` 的原始碼、Windows CI、安全稽核與正式封裝統一使用
Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由專案內部的 PCM16 音訊層取代，涵蓋音量
調整、立體聲轉單聲道及 Realtime 串流重採樣，避免增加新的第三方供應鏈依賴。

升級不會搬移或重建使用者資料庫。既有 RC3 的設定、對話、記憶與工作資料仍
沿用原本位置。Python 3.12 只保留作為開發回歸參考；`v2.1.0-rc.1` 發布物不得
以 Python 3.12 封裝。若需回復舊版，只移除程式本體並安裝經驗證的先前版本，
不得刪除使用者資料目錄。

## 简体中文

`v2.1.0-rc.1` 的源代码、Windows CI、安全审计与正式打包统一使用
Python 3.14.x。
Python 3.13 起移除的 `audioop` 已由项目内部的 PCM16 音频层取代，涵盖音量
调整、立体声转单声道及 Realtime 流式重采样，避免增加新的第三方供应链依赖。

升级不会迁移或重建用户数据库。已有 RC3 的设置、对话、记忆与工作数据继续
使用原有位置。Python 3.12 仅保留作为开发回归参考；`v2.1.0-rc.1` 发布文件
不得使用 Python 3.12 打包。若需要回退，只移除程序本体并安装已验证的先前
版本，同时不得删除用户数据目录。

## English

`v2.1.0-rc.1` standardizes source validation, Windows CI, security auditing,
and release packaging on Python 3.14.x. The `audioop` module removed in Python 3.13 is
replaced by an in-project PCM16 layer for gain, stereo-to-mono mixing, and
stateful Realtime stream resampling. This avoids adding another third-party
supply-chain dependency.

The upgrade neither moves nor recreates the user database. Existing RC3
settings, conversations, memories, and work data keep their current location.
Python 3.12 remains only as a development regression reference;
`v2.1.0-rc.1` artifacts must not be packaged with it. To roll back, remove only
the application and install a previously verified version without deleting the
user data directory.

## 日本語

`v2.1.0-rc.1` のソース検証、Windows CI、セキュリティ監査、配布物は
Python 3.14.x に統一されています。Python 3.13 で削除された `audioop` は、
音量調整、ステレオからモノラルへの変換、Realtime ストリームの状態付き
リサンプリングを行うプロジェクト内の PCM16 層へ置き換えました。新しい
外部依存関係は追加していません。

この移行では利用者データベースを移動・再作成しません。RC3 で保存された
設定、会話、記憶、作業データも同じ場所で引き続き利用します。Python 3.12 は
開発時の回帰確認用としてのみ残し、`v2.1.0-rc.1` の配布物には使用しません。
以前の版へ戻す場合も、利用者データを削除せず、アプリ本体だけを入れ替えて
ください。
