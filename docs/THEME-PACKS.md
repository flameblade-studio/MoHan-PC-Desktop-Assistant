# 墨寒主題包／墨寒主题包／MoHan Theme Packs／墨寒テーマパック

## 繁體中文

主題包是版本化、純宣告式 ZIP，只能包含 `manifest.json` 與一個選用的 PNG 或安全 SVG 背景。它不執行 Python、JavaScript、外掛或腳本。核心提供檢查、原子安裝、列出與還原內建主題；控制台 UI 結構由應用程式本體掌握。第 2 版會記錄套件宣告為炎劍官方、使用者自製或未來的墨寒自創草稿，並保存來源類型、作者、授權，以及參考素材未被直接打包的聲明。目前公開版只顯示炎劍官方與使用者自製套件。

使用者只需下載並上傳一個自含式檔案，不需要旁附資料夾、相依主題或網路下載。上傳只會安裝；選取後可先預覽，按控制台右下「保存設定」才正式啟用，按「取消」則還原先前主題。非目前使用中的外部主題可由使用者確認後完整刪除；內建主題不可刪除。日後製作新風格時，只需以固定範本填入四語名稱、語意色彩、字型、圓角與選用背景，即可快速產生同一種單檔主題包。

目前刻意不開放自主生成佈景主題：控制台沒有生成入口，背景服務不會自動生成或下載，也不會送出生成請求。套件來源管線預留 `mohan-generated` 給未來通過稽核的供應器，因此日後正式開放時不必推翻主題包生命週期，也不會破壞炎劍官方與使用者自製套件的隔離。

主題只能設定穩定的語意設計 token：`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus`，以及字型、圓角和固定角色的背景資產。不得宣告分頁索引、頁數、頁面名稱、widget `objectName`、版面座標、功能子頁清單或結構 selector。缺少的 token 使用內建預設值；未知且格式合法的 token 會被忽略，讓舊主題可直接套用新增或刪減功能後的控制台。非法型別或危險資產一律拒絕。

Manifest 必須含完整繁中、簡中、英文、日文名稱。色彩使用 `#RRGGBB` 或 `#RRGGBBAA`。封裝上限為 16 MiB、單一成員 12 MiB、解壓總量 16 MiB、壓縮比 100:1、背景 4096×4096。重複或額外成員、絕對路徑、反斜線、`..`、SVG 腳本、事件、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD 與 entity 均會被拒絕。

凌霄內建主題包提供預設 `ink-gold`「墨金・凌霄」、可選的 `celadon`「霧靄青瓷」與 `crimson`「赤焰劍光」。它們共用 `apply_flagship_theme` 的結構化 QSS，並各自提供一般與高對比完整色板；`TEXT_ON_SURFACE_PAIRS` 每一組都維持至少 4.5:1。C 主題把 `cinnabar` 調成暗赤紫，讓危險狀態不會與赤金主色混在一起；預設仍是 `ink-gold`。

## 简体中文

主题包是版本化、纯声明式 ZIP，只能包含 `manifest.json` 与一个可选的 PNG 或安全 SVG 背景。它不执行 Python、JavaScript、插件或脚本。核心提供检查、原子安装、列出与恢复内置主题；控制台 UI 结构由应用程序本体掌握。第 2 版会记录套件声明为炎剑官方、用户自制或未来的墨寒自创草稿，并保存来源类型、作者、许可，以及参考素材未被直接打包的声明。目前公开版只显示炎剑官方与用户自制套件。

用户只需下载并上传一个自包含文件，不需要附带文件夹、依赖主题或网络下载。上传只会安装；选取后可以先预览，按控制台右下“保存设置”才正式启用，按“取消”则恢复先前主题。当前未使用的外部主题可由用户确认后完整删除；内置主题不可删除。日后制作新风格时，只需用固定模板填写四语名称、语义颜色、字体、圆角与可选背景，即可快速生成相同格式的单文件主题包。

目前刻意不开放自主生成界面主题：控制台没有生成入口，后台服务不会自动生成或下载，也不会发送生成请求。套件来源管线预留 `mohan-generated` 给未来通过审核的提供方，因此日后正式开放时不必推翻主题包生命周期，也不会破坏炎剑官方与用户自制套件的隔离。

主题只能设置稳定的语义设计 token：`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus`，以及字体、圆角和固定角色的背景资产。不得声明分页索引、页数、页面名称、widget `objectName`、布局坐标、功能子页清单或结构 selector。缺少的 token 使用内置默认值；未知且格式合法的 token 会被忽略，使旧主题可直接应用于增删功能后的控制台。非法类型或危险资产一律拒绝。

Manifest 必须包含完整繁中、简中、英文、日文名称。颜色使用 `#RRGGBB` 或 `#RRGGBBAA`。封装上限为 16 MiB、单个成员 12 MiB、解压总量 16 MiB、压缩比 100:1、背景 4096×4096。重复或额外成员、绝对路径、反斜线、`..`、SVG 脚本、事件、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD 与 entity 均会被拒绝。

凌霄内置主题包提供默认 `ink-gold`“墨金・凌霄”、可选的 `celadon`“雾霭青瓷”与 `crimson`“赤焰剑光”。它们共用 `apply_flagship_theme` 的结构化 QSS，并各自提供普通与高对比完整色板；`TEXT_ON_SURFACE_PAIRS` 每一组都保持至少 4.5:1。C 主题将 `cinnabar` 调为暗赤紫，让危险状态不会与赤金主色混在一起；默认仍为 `ink-gold`。

## English

A theme pack is a versioned, declarative ZIP containing only `manifest.json` and one optional PNG or safe SVG background. It never executes Python, JavaScript, plugins, or scripts. The core validates, atomically installs, lists, and restores the built-in theme; the application owns the control-panel structure. Version 2 records whether the pack declares itself as Flameblade official, user-authored, or a future MoHan-generated draft, together with source kind, author, license, and confirmation that reference assets are not embedded. The current public product exposes only Flameblade official and user-authored packages.

The user downloads and uploads one self-contained file; no sidecar folder, dependent theme, or network download is allowed. Uploading only installs the pack. A selection may be previewed, becomes persistent only after the control panel's global Save action, and is reverted by Cancel. The user may confirm removal of any inactive external theme, while the built-in theme is never removable. A fixed authoring template lets us turn a planned visual direction into the same single-file pack by supplying four-language names, semantic colors, a font, a radius, and an optional background.

Autonomous theme generation is intentionally unavailable in the current release: there is no control-panel entry, background task, automatic download, or generation request. The package provenance channel reserves `mohan-generated` for a future audited provider, so enabling it later will not require replacing the theme package lifecycle or weakening official/user package isolation.

Themes may set only stable semantic design tokens: `window`, `background`, `card`, `surface`, `text`, `title`, `muted`, `border`, `primary`, `danger`, and `focus`, plus a font, radius, and fixed-role background asset. They must not declare tab indexes, page counts or names, widget `objectName` values, layout coordinates, feature-page lists, or structural selectors. Missing tokens use built-in defaults. Unknown tokens with valid values are ignored, so an old theme applies unchanged when pages are added or removed. Invalid types and dangerous assets are rejected.

The manifest requires complete Traditional Chinese, Simplified Chinese, English, and Japanese names. Colors use `#RRGGBB` or `#RRGGBBAA`. Limits are 16 MiB per archive, 12 MiB per member, 16 MiB expanded, 100:1 compression, and a 4096×4096 background. Duplicate or extra members, absolute paths, backslashes, `..`, SVG scripts, events, `foreignObject`, external URLs, CSS `url()`, `data:`, DTDs, and entities are rejected.

The built-in Lingxiao theme packs provide the default `ink-gold` “Ink-Gold · Lingxiao” plus optional `celadon` “Misty Celadon” and `crimson` “Crimson Swordlight”. They share the structured QSS in `apply_flagship_theme`, while each supplies complete normal and high-contrast palettes; every `TEXT_ON_SURFACE_PAIRS` entry remains at least 4.5:1. The C theme changes `cinnabar` to a dark crimson-purple so danger state remains distinct from its red-gold primary color; `ink-gold` remains the default.

## 日本語

テーマパックは、バージョン管理された宣言専用 ZIP です。`manifest.json` と、任意の PNG または安全な SVG 背景を一つだけ含められます。Python、JavaScript、プラグイン、スクリプトは実行しません。コアは検証、アトミックなインストール、一覧表示、内蔵テーマへの復元を提供し、設定画面の構造はアプリ本体が所有します。バージョン 2 は、炎剣公式、ユーザー制作、将来の墨寒生成ドラフトという申告元に加え、素材の由来、作者、ライセンス、参照素材を直接同梱していない旨を記録します。現在の公開版が表示するのは炎剣公式とユーザー制作だけです。

利用者がダウンロードしてアップロードするのは、自己完結した一つのファイルだけです。付属フォルダー、依存テーマ、ネットワークからの追加取得は不要です。アップロードはインストールだけを行い、選択後にプレビューできます。正式な有効化は設定画面右下の全体保存で行い、キャンセル時は以前のテーマへ戻します。現在使用していない外部テーマは確認後に完全削除できますが、内蔵テーマは削除できません。今後は固定テンプレートへ四言語名、意味的な色、フォント、角丸、任意の背景を入力するだけで、計画したデザインを同形式の単一ファイルへ素早くまとめられます。

現在はテーマの自律生成を意図的に公開していません。設定画面に生成入口はなく、バックグラウンドでの自動生成、ダウンロード、生成要求も行いません。パッケージの由来経路には、将来監査済みの提供者向けに `mohan-generated` を予約しています。正式に開放する際もテーマパックのライフサイクルを作り直す必要はなく、炎剣公式・ユーザー制作パッケージとの分離を維持できます。

テーマが設定できるのは、`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus` という安定した意味的デザイントークンと、フォント、角丸、固定役割の背景素材だけです。タブ番号、ページ数や名前、widget の `objectName`、配置座標、機能ページ一覧、構造 selector は宣言できません。不足トークンは内蔵既定値へフォールバックし、値が正しい未知トークンは無視されます。そのためページの追加・削除後も旧テーマをそのまま利用できます。不正な型や危険な素材は拒否します。

Manifest には繁体字中国語、簡体字中国語、英語、日本語の完全な名称が必要です。色は `#RRGGBB` または `#RRGGBBAA` です。上限はアーカイブ 16 MiB、メンバー 12 MiB、展開合計 16 MiB、圧縮率 100:1、背景 4096×4096 です。重複・余分なメンバー、絶対パス、バックスラッシュ、`..`、SVG のスクリプト、イベント、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD、entity は拒否します。

内蔵の凌霄テーマパックは既定の `ink-gold`「墨金・凌霄」と、選択可能な `celadon`「霧靄青磁」および `crimson`「赤焔剣光」を提供します。構造化された QSS は `apply_flagship_theme` で共有し、各テーマが通常・高コントラストの完全な色板を持ちます。`TEXT_ON_SURFACE_PAIRS` の全項目は 4.5:1 以上です。C テーマでは `cinnabar` を暗い赤紫へ変更し、危険状態が赤金の主色と混同されないようにしています。既定値は `ink-gold` のままです。
