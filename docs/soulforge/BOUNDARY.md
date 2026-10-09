# 炎劍鑄魂模組邊界／炎剑铸魂模块边界／Soulforge Module Boundary／炎剣鋳魂モジュール境界

## 繁體中文

正式資料在 `docs/soulforge/module-boundary.json`（逐模組分類、違規基線與已修違規）。

本文件把五個候選套件的 376 個 Python 模組逐一分成引擎 263、墨寒產品殼 53、炎劍畫譜 9、待拆 51。JSON 使用完整 module name，不用 glob；新增、刪除、重複或漏列模組都會使測試失敗。

「引擎」是可移入 Soulforge 的角色中立能力。「墨寒產品殼」保留產品名稱、版本與倉庫、既有安裝資料位置、更新／備份格式、品牌視覺及最外層產品組裝。「炎劍畫譜」是素材稽核、證據與發布前驗證能力。「待拆」代表同檔仍同時擁有引擎與墨寒資料來源，例如直接呼叫 `load_mohan_character_data()` 的相容 facade；資料已外置不等於依賴已中立。

允許方向是墨寒產品殼指向引擎，且引擎與畫譜都可使用版本化角色包契約。禁止引擎匯入墨寒產品殼或畫譜。現況為 70 組引擎→產品殼基線、0 組引擎→畫譜；只准減少。一般 import、`lazy import`、相對 import 與字面值動態 import 套用同一規則。

本包修掉 9 組只為 HTTP／PCM／浮點容差而發生的反向依賴：通用值移入 `domain.core_constants`，`domain.constants` 保留原名相容匯出。另以 `application.service_contracts.CompanionServicesPort` 解除 `companion_core` 對混合式 `service_container` 的直接型別依賴；公開類別、函式與建構簽章不變。

## 简体中文

正式数据在 `docs/soulforge/module-boundary.json`（逐模块分类、违规基线与已修违规）。

本文档将五个候选包的 376 个 Python 模块逐一分为引擎 263、墨寒产品壳 53、炎剑画谱 9、待拆 51。JSON 使用完整 module name，不使用 glob；新增、删除、重复或漏列模块都会使测试失败。

“引擎”是可移入 Soulforge 的角色中立能力。“墨寒产品壳”保留产品名称、版本与仓库、现有安装数据位置、更新与备份格式、品牌视觉及最外层产品组装。“炎剑画谱”是素材审计、证据与发布前验证能力。“待拆”表示同一文件仍同时拥有引擎与墨寒数据来源，例如直接调用 `load_mohan_character_data()` 的兼容 facade；数据已外置不等于依赖已中立。

允许方向是墨寒产品壳指向引擎，引擎与画谱都可使用版本化角色包契约。禁止引擎导入墨寒产品壳或画谱。目前有 70 组引擎到产品壳基线、0 组引擎到画谱；只允许减少。普通导入、`lazy import`、相对导入和字面值动态导入使用同一规则。

本工作包修复了 9 组仅因 HTTP、PCM 与浮点容差产生的反向依赖：通用值移入 `domain.core_constants`，`domain.constants` 保留原名兼容导出。另以 `application.service_contracts.CompanionServicesPort` 解除 `companion_core` 对混合式 `service_container` 的直接类型依赖；公开类、函数与构造签名不变。

## English

The canonical data is `docs/soulforge/module-boundary.json` (per-module classification, violation baseline and removed violations).

This document classifies all 376 Python modules in the five candidate packages: 263 engine modules, 53 MoHan product-shell modules, 9 Huapu modules, and 51 pending-split modules. The JSON uses exact module names rather than globs. Adding, removing, duplicating, or omitting a module fails the test.

“Engine” means character-neutral capability that can move into Soulforge. “MoHan product shell” retains product identity, release version and repository, existing installed-data locations, update and backup formats, branded visuals, and outermost product composition. “Huapu” owns asset audit, evidence, and pre-publication validation. “Pending split” identifies a file that still owns both engine behavior and a MoHan data source, including compatibility facades that call `load_mohan_character_data()`; externalized data alone does not make the dependency neutral.

The allowed direction is MoHan product shell to engine, while both engine and Huapu may use the versioned character-pack contract. Engine imports of the MoHan product shell or Huapu are forbidden. The current baseline contains 70 engine-to-shell pairs and zero engine-to-Huapu pairs, and may only decrease. Regular imports, `lazy import`, relative imports, and literal dynamic imports follow the same rule.

This package removes nine reverse dependencies that existed only to obtain HTTP, PCM, or floating-point constants. Neutral values now live in `domain.core_constants`, while `domain.constants` preserves the old public exports. `application.service_contracts.CompanionServicesPort` also removes the direct `companion_core` type dependency on the mixed `service_container`; public classes, functions, and constructor signatures are unchanged.

## 日本語

正式データは `docs/soulforge/module-boundary.json`（モジュール別分類、違反基準、解消済み違反）にあります。

本書は五つの候補パッケージにある 376 個の Python モジュールを、エンジン 263、墨寒製品シェル 53、炎剣画譜 9、分割待ち 51 に一つずつ分類します。JSON は glob ではなく完全な module name を使用し、モジュールの追加、削除、重複、記載漏れをテスト失敗にします。

「エンジン」は Soulforge へ移せるキャラクター中立の機能です。「墨寒製品シェル」は製品識別、リリース版数とリポジトリ、既存のインストール済みデータ位置、更新とバックアップ形式、ブランド表示、最外層の製品構成を保持します。「炎剣画譜」は素材監査、証拠、公開前検証を所有します。「分割待ち」は一つのファイルがエンジン動作と墨寒データ源の両方を所有する状態であり、`load_mohan_character_data()` を直接呼ぶ互換 facade も含みます。データの外部化だけでは依存は中立になりません。

許可する方向は墨寒製品シェルからエンジンであり、エンジンと画譜はどちらも版管理されたキャラクターパック契約を利用できます。エンジンから墨寒製品シェルまたは画譜への import を禁止します。現在の基準はエンジンから製品シェルへの 70 組、エンジンから画譜への 0 組で、削減だけを許可します。通常 import、`lazy import`、相対 import、文字列リテラルによる動的 import に同じ規則を適用します。

本作業では HTTP、PCM、浮動小数点許容差を得るだけの逆依存 9 組を解消しました。中立値を `domain.core_constants` へ移し、`domain.constants` は従来の公開名を互換再公開します。また `application.service_contracts.CompanionServicesPort` により、`companion_core` から混在した `service_container` への直接型依存を解消しました。公開済みのクラス、関数、コンストラクター署名は変更していません。
