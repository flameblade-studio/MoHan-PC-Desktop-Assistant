# 墨寒主題包／墨寒主题包／MoHan Theme Packs／墨寒テーマパック

## 繁體中文

主題包是版本化、純宣告式 ZIP，內容由 `manifest.json` 與一個選用的 PNG 或安全 SVG 背景組成。純資料格式將 Python、JavaScript、外掛與腳本維持在執行範圍之外。核心提供檢查、原子安裝、列出與還原內建主題；控制台 UI 結構由應用程式本體掌握。第 2 版會記錄套件宣告為炎劍官方、使用者自製或未來的墨寒自創草稿，並保存來源類型、作者、授權，以及參考素材保持在封裝範圍之外的聲明。目前公開版的顯示範圍為炎劍官方與使用者自製套件。

使用者下載並上傳一個完整自含、具備所有所需資料的檔案。上傳階段完成安裝；選取後可先預覽，按控制台右下「保存設定」正式啟用，按「取消」則還原先前主題。使用者確認後可完整移除目前處於非使用狀態的外部主題；內建主題持續受到保護。日後製作新風格時，以固定範本填入四語名稱、語意色彩、字型、圓角與選用背景，即可快速產生同一種單檔主題包。

目前的主題工作流程採使用者主動上傳與稽核套件模式；自主生成安排在供應器通過稽核後啟用。套件來源管線已預留 `mohan-generated` 給未來通過稽核的供應器，因此日後可沿用現有主題包生命週期，並維持炎劍官方與使用者自製套件的隔離。

主題的設定範圍限定為穩定的語意設計 token：`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus`，以及字型、圓角和固定角色的背景資產。分頁索引、頁數、頁面名稱、widget `objectName`、版面座標、功能子頁清單與結構 selector 由應用程式本體掌握。省略的 token 使用內建預設值；未知且格式合法的 token 會略過，讓舊主題可直接套用增減功能後的控制台。允收條件要求型別合法且資產符合安全規格。

Manifest 必須含完整繁中、簡中、英文、日文名稱。色彩使用 `#RRGGBB` 或 `#RRGGBBAA`。封裝上限為 16 MiB、單一成員 12 MiB、解壓總量 16 MiB、壓縮比 100:1、背景 4096×4096。允收成員各自唯一且受 manifest 宣告，使用正規相對路徑與正斜線；SVG 採靜態宣告圖形與套件內資料，XML 採一般元素及屬性。

凌霄內建主題包提供預設 `ink-gold`「墨金・凌霄」、可選的 `celadon`「霧靄青瓷」與 `crimson`「赤焰劍光」。它們共用 `apply_flagship_theme` 的結構化 QSS，並各自提供一般與高對比完整色板；`TEXT_ON_SURFACE_PAIRS` 每一組都維持至少 4.5:1。C 主題把 `cinnabar` 調成暗赤紫，讓危險狀態與赤金主色清楚區隔；預設仍是 `ink-gold`。

## 简体中文

主题包是版本化、纯声明式 ZIP，内容由 `manifest.json` 与一个可选的 PNG 或安全 SVG 背景组成。纯数据格式将 Python、JavaScript、插件与脚本维持在执行范围之外。核心提供检查、原子安装、列出与恢复内置主题；控制台 UI 结构由应用程序本体掌握。第 2 版会记录套件声明为炎剑官方、用户自制或未来的墨寒自创草稿，并保存来源类型、作者、许可，以及参考素材保持在封装范围之外的声明。目前公开版的显示范围为炎剑官方与用户自制套件。

用户下载并上传一个完整自包含、具备所有所需数据的文件。上传阶段完成安装；选取后可以先预览，按控制台右下“保存设置”正式启用，按“取消”则恢复先前主题。用户确认后可完整移除当前处于非使用状态的外部主题；内置主题持续受到保护。日后制作新风格时，用固定模板填写四语名称、语义颜色、字体、圆角与可选背景，即可快速生成相同格式的单文件主题包。

当前的主题工作流程采用用户主动上传与审核套件模式；自主生成安排在提供方通过审核后启用。套件来源管线已预留 `mohan-generated` 给未来通过审核的提供方，因此日后可沿用现有主题包生命周期，并维持炎剑官方与用户自制套件的隔离。

主题的设置范围限定为稳定的语义设计 token：`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus`，以及字体、圆角和固定角色的背景资产。分页索引、页数、页面名称、widget `objectName`、布局坐标、功能子页清单与结构 selector 由应用程序本体掌握。省略的 token 使用内置默认值；未知且格式合法的 token 会略过，使旧主题可直接应用于增减功能后的控制台。接收条件要求类型合法且资产符合安全规格。

Manifest 必须包含完整繁中、简中、英文、日文名称。颜色使用 `#RRGGBB` 或 `#RRGGBBAA`。封装上限为 16 MiB、单个成员 12 MiB、解压总量 16 MiB、压缩比 100:1、背景 4096×4096。接收成员各自唯一且受 manifest 声明，使用正规相对路径与正斜线；SVG 采用静态声明图形与套件内数据，XML 采用普通元素及属性。

凌霄内置主题包提供默认 `ink-gold`“墨金・凌霄”、可选的 `celadon`“雾霭青瓷”与 `crimson`“赤焰剑光”。它们共用 `apply_flagship_theme` 的结构化 QSS，并各自提供普通与高对比完整色板；`TEXT_ON_SURFACE_PAIRS` 每一组都保持至少 4.5:1。C 主题将 `cinnabar` 调为暗赤紫，让危险状态与赤金主色清楚区分；默认仍为 `ink-gold`。

## English

A theme pack is a versioned, declarative ZIP composed of `manifest.json` and one optional PNG or safe SVG background. Its data-only format keeps Python, JavaScript, plugins, and scripts outside the execution surface. The core validates, atomically installs, lists, and restores the built-in theme; the application owns the control-panel structure. Version 2 records whether the pack declares itself as Flameblade official, user-authored, or a future MoHan-generated draft, together with source kind, author, license, and confirmation that reference assets remain outside the package. The current public product displays Flameblade official and user-authored packages.

The user downloads and uploads one fully self-contained file with every required resource. Uploading completes installation. A selection may be previewed, becomes persistent through the control panel's global Save action, and is reverted by Cancel. The user may confirm removal of an inactive external theme, while the built-in theme remains protected. A fixed authoring template lets us turn a planned visual direction into the same single-file pack by supplying four-language names, semantic colors, a font, a radius, and an optional background.

The current theme workflow uses user-initiated uploads and audited packages; autonomous generation is scheduled for activation after its provider passes audit. The package provenance channel already reserves `mohan-generated` for that future audited provider, so activation can reuse the existing theme-package lifecycle while preserving official/user package isolation.

A theme's setting scope is the stable semantic design tokens `window`, `background`, `card`, `surface`, `text`, `title`, `muted`, `border`, `primary`, `danger`, and `focus`, plus a font, radius, and fixed-role background asset. The application owns tab indexes, page counts and names, widget `objectName` values, layout coordinates, feature-page lists, and structural selectors. Omitted tokens use built-in defaults. Unknown tokens with valid values are skipped, so an old theme applies unchanged as pages change. Acceptance requires valid types and assets that satisfy the safety specification.

The manifest requires complete Traditional Chinese, Simplified Chinese, English, and Japanese names. Colors use `#RRGGBB` or `#RRGGBBAA`. Limits are 16 MiB per archive, 12 MiB per member, 16 MiB expanded, 100:1 compression, and a 4096×4096 background. Accepted members are unique and manifest-declared, use normalized relative paths and forward slashes, and keep SVG content to static declarative shapes and package-local data with ordinary XML elements and attributes.

The built-in Lingxiao theme packs provide the default `ink-gold` “Ink-Gold · Lingxiao” plus optional `celadon` “Misty Celadon” and `crimson` “Crimson Swordlight”. They share the structured QSS in `apply_flagship_theme`, while each supplies complete normal and high-contrast palettes; every `TEXT_ON_SURFACE_PAIRS` entry remains at least 4.5:1. The C theme changes `cinnabar` to a dark crimson-purple so danger state remains distinct from its red-gold primary color; `ink-gold` remains the default.

## 日本語

テーマパックは、バージョン管理された宣言専用 ZIP です。内容は `manifest.json` と、任意の PNG または安全な SVG 背景一つで構成します。データ専用形式により、Python、JavaScript、プラグイン、スクリプトを実行範囲外に保ちます。コアは検証、アトミックなインストール、一覧表示、内蔵テーマへの復元を提供し、設定画面の構造はアプリ本体が所有します。バージョン 2 は、炎剣公式、ユーザー制作、将来の墨寒生成ドラフトという申告元に加え、素材の由来、作者、ライセンス、参照素材をパッケージ範囲外に保つ旨を記録します。現在の公開版は炎剣公式とユーザー制作を表示します。

利用者は、必要な資料をすべて備えた自己完結ファイル一つをダウンロードしてアップロードします。アップロード段階でインストールを完了し、選択後にプレビューできます。正式な有効化は設定画面右下の全体保存で行い、キャンセル時は以前のテーマへ戻します。利用者の確認後、現在使用中の状態から切り替えた外部テーマを完全削除できます。内蔵テーマは継続して保護します。今後は固定テンプレートへ四言語名、意味的な色、フォント、角丸、任意の背景を入力するだけで、計画したデザインを同形式の単一ファイルへ素早くまとめられます。

現在のテーマ運用は、利用者が開始するアップロードと監査済みパッケージを採用します。自律生成は、提供者の監査通過後に有効化する予定です。パッケージの由来経路には、将来監査済みの提供者向けに `mohan-generated` を予約しています。正式な有効化時も既存のテーマパックライフサイクルを継続し、炎剣公式・ユーザー制作パッケージとの分離を維持できます。

テーマの設定範囲は、`window`、`background`、`card`、`surface`、`text`、`title`、`muted`、`border`、`primary`、`danger`、`focus` という安定した意味的デザイントークンと、フォント、角丸、固定役割の背景素材です。タブ番号、ページ数や名前、widget の `objectName`、配置座標、機能ページ一覧、構造 selector はアプリ本体が所有します。省略トークンは内蔵既定値へフォールバックし、値が正しい未知トークンは読み飛ばします。そのためページ構成の変更後も旧テーマをそのまま利用できます。受入条件は、型と素材が安全仕様を満たすことです。

Manifest には繁体字中国語、簡体字中国語、英語、日本語の完全な名称が必要です。色は `#RRGGBB` または `#RRGGBBAA` です。上限はアーカイブ 16 MiB、メンバー 12 MiB、展開合計 16 MiB、圧縮率 100:1、背景 4096×4096 です。受入メンバーは一意かつ manifest で宣言し、正規相対パスとスラッシュを使用します。SVG は静的な宣言図形とパッケージ内データ、XML は通常の要素と属性で構成します。

内蔵の凌霄テーマパックは既定の `ink-gold`「墨金・凌霄」と、選択可能な `celadon`「霧靄青磁」および `crimson`「赤焔剣光」を提供します。構造化された QSS は `apply_flagship_theme` で共有し、各テーマが通常・高コントラストの完全な色板を持ちます。`TEXT_ON_SURFACE_PAIRS` の全項目は 4.5:1 以上です。C テーマでは `cinnabar` を暗い赤紫へ変更し、危険状態と赤金の主色を明確に区別しています。既定値は `ink-gold` のままです。
