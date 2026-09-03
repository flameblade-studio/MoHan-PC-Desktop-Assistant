from __future__ import annotations

lazy import ast
lazy import re
lazy import sys
lazy from pathlib import Path
lazy from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from presentation.flagship_ui_localization import (
    FLAGSHIP_TRANSLATIONS,
    FlagshipTranslator,
    validate_flagship_translations,
)
lazy from presentation.ui_localization import (
    _ENGLISH,
    _JAPANESE,
    _SIMPLIFIED_CHINESE,
    ui_text,
)

PRESENTATION_ROOT = ROOT / "presentation"
GENERIC_UI_OWNER_PATTERNS = ("dashboard_*.py", "companion_*.py")
GENERIC_UI_OWNER_PATHS = (
    PRESENTATION_ROOT / "first_run_wizard.py",
    PRESENTATION_ROOT / "ui_localization.py",
    PRESENTATION_ROOT / "ui_localization_ja.py",
    PRESENTATION_ROOT / "settings_ui_localization.py",
    PRESENTATION_ROOT / "auxiliary_ui_localization.py",
)
FLAGSHIP_UI_OWNER_ROOT = PRESENTATION_ROOT / "flagship"
APP_PATH = ROOT / "app.py"


WARDROBE_SOURCES = {
    "tab_wardrobe": "雲裳閣",
    "cancel_without_saving": "取消（不要保存）",
    "wardrobe_import": "匯入服裝套件",
    "wardrobe_apply": "套用選取的服裝",
    "wardrobe_restore_builtin": "還原內建服裝",
    "wardrobe_package_list": "套件清單",
    "wardrobe_compatibility_status": "相容狀態",
    "wardrobe_status": "狀態",
    "wardrobe_no_packages": "尚未安裝服裝套件",
    "wardrobe_default_outfit": "內建預設服裝",
    "wardrobe_compatible": "相容",
    "wardrobe_incompatible": "不相容",
    "wardrobe_status_ready": "雲裳系統已就緒",
    "wardrobe_validator_pending": "套件尚未通過完整安全驗證，因此未安裝。",
    "wardrobe_assets_pending": "這套服裝未具備完整全視角素材，不能套用。",
    "wardrobe_body_profile_outdated": "這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成",
    "wardrobe_builtin_applied": "已套用內建預設服裝。",
    "wardrobe_outfit_applied": "已套用所選完整服裝。",
    "wardrobe_autonomous_enabled": "允許墨寒自主選裝",
    "wardrobe_self_generation_enabled": "允許墨寒雲端自創新衣（可能產生費用）",
    "wardrobe_trend_search_enabled": "允許以五類情境搜尋流行趨勢作為原創靈感（可能產生費用）",
    "wardrobe_generation_trend_search": "正在使用已同意的五類情境搜尋趨勢，隨後生成、稽核並打包新衣（可能產生費用）……",
    "wardrobe_generated_limit": "自創服裝保留上限",
    "wardrobe_storage_limit": "自創服裝容量上限",
    "wardrobe_manual_lock_hours": "手動換裝鎖定時數",
    "wardrobe_manual_lock_off": "不鎖定",
    "wardrobe_generate_now": "立即生成新衣（將使用圖片 API）",
    "wardrobe_generation_starting": "正在建立 31 視角新衣並執行安全稽核……",
    "wardrobe_generation_running": "正在生成、稽核並封裝新衣……",
    "wardrobe_generation_installed": "新衣已通過稽核、安裝並套用。",
    "wardrobe_generation_installed_manual_lock": "新衣已通過稽核並安裝；目前手動衣裝仍在鎖定期，因此保持不變。",
    "wardrobe_generation_activation_failed": "新衣已通過稽核並安裝，但未能安全套用；目前衣裝保持不變。",
    "wardrobe_generation_not_enabled": "請先勾選允許雲端自創新衣。",
    "wardrobe_generation_no_key": "尚未設定可用的 OpenAI API Key。",
    "wardrobe_generation_capacity": "已達自創服裝容量或冷卻限制。",
    "wardrobe_generation_quarantined": "新衣未通過稽核，已隔離且未套用。",
    "wardrobe_generation_failed": "新衣生成失敗，未安裝任何素材。",
    "wardrobe_automatic_selection_disabled": "自主選裝目前已關閉。",
    "wardrobe_automatic_selection_failed": "自主選裝評估失敗，已保留目前衣裝。",
    "wardrobe_automatic_outfit_selected": "墨寒已依情境自主換裝。",
    "wardrobe_pavilion_subtitle": "讓墨寒依天候、心情與場合挑選完整造型，也保留您的決定。",
    "wardrobe_source_policy": "來源分流：炎劍官方・使用者匯入・墨寒自創",
    "dashboard_brand_line": "墨色為骨・寒光為心",
    "wardrobe_character_preview": "墨寒造型預覽",
    "wardrobe_view_front": "正面",
    "wardrobe_view_left": "左側",
    "wardrobe_view_right": "右側",
    "wardrobe_view_back": "背面",
    "wardrobe_upload_single_file": "上傳單一檔案",
    "wardrobe_installed_inactive": "已安裝，尚未套用",
    "wardrobe_outfit_preview": "服裝預覽",
    "wardrobe_hairstyle_preview": "髮型預覽",
    "wardrobe_headwear_accessories": "頭飾與配件",
    "wardrobe_preview_complete_look": "一鍵預覽整套造型",
    "wardrobe_changes_after_save": "保存後生效",
    "wardrobe_cancel_restores": "取消並回復",
    "wardrobe_remove_package": "移除外掛包",
    "wardrobe_delete_confirm": "確定移除「{package}」嗎？",
    "wardrobe_builtin_not_removable": "內建包不可刪除",
    "wardrobe_switch_before_remove": "請先切換，再移除使用中的包",
    "wardrobe_missing_package_fallback": "缺少套件，已保留目前造型",
    "theme_preview": "主題預覽",
    "theme_restore": "還原主題",
    "package_rejected_unsafe_or_missing": "套件含危險內容或缺少檔案，已整包拒絕",
    "appearance_category_outfit": "衣裝",
    "appearance_category_hairstyle": "髮型",
    "appearance_category_headwear": "頭飾",
    "appearance_category_accessory": "配件",
    "appearance_no_headwear": "無頭飾",
    "appearance_category_makeup": "妝容",
    "wardrobe_makeup_title": "妝容",
    "wardrobe_makeup_item": "妝容選擇",
    "wardrobe_makeup_none": "素顏（不上妝）",
    "wardrobe_makeup_variant_classic": "原妝",
    "wardrobe_makeup_variant_light": "淡雅",
    "wardrobe_makeup_intensity": "妝感濃淡",
    "wardrobe_makeup_applied": "已套用所選妝容。",
    "wardrobe_makeup_cleared": "已卸妝，回到素顏。",
    "wardrobe_makeup_pack_missing": "所選妝容的套件已不存在，已改回內建原妝。",
    "wardrobe_makeup_unavailable": "這組妝容目前無法套用，已保留目前妝容。",
    "wardrobe_makeup_assets_pending": "內建妝容素材待補",
    "wardrobe_makeup_hint": "素體為素顏；妝容與衣裝、髮型、頭飾一樣是可開關的圖層，新妝容請用「匯入服裝套件」加入。",
}

WARDROBE_EXPECTED = {
    "zh-TW": tuple(WARDROBE_SOURCES.values()),
    "zh-CN": (
        "云裳阁",
        "取消（不保存）",
        "导入服装套件",
        "应用所选服装",
        "恢复内置服装",
        "套件列表",
        "兼容状态",
        "状态",
        "尚未安装服装套件",
        "内置默认服装",
        "兼容",
        "不兼容",
        "云裳系统已就绪",
        "套件未通过完整全视角与安全验证，因此未安装。",
        "这套服装未具备完整全视角素材，无法应用。",
        "这套服装是为一代素体制作的，穿在二代素体上会对不准；请用一键制衣重新生成",
        "已应用内置默认服装。",
        "已应用所选完整服装。",
        "允许墨寒自主选装",
        "允许墨寒云端自创新衣（可能产生费用）",
        "允许以五类情境搜索流行趋势作为原创灵感（可能产生费用）",
        "正在使用已同意的五类情境搜索趋势，随后生成、审核并打包新衣（可能产生费用）……",
        "自创服装保留上限",
        "自创服装容量上限",
        "手动换装锁定时数",
        "不锁定",
        "立即生成新衣（将使用图片 API）",
        "正在创建 31 视角新衣并执行安全审核……",
        "正在生成、审核并打包新衣……",
        "新衣已通过审核、安装并应用。",
        "新衣已通过审核并安装；当前手动衣装仍在锁定期，因此保持不变。",
        "新衣已通过审核并安装，但无法安全应用；当前衣装保持不变。",
        "请先勾选允许云端自创新衣。",
        "尚未设置可用的 OpenAI API Key。",
        "已达到自创服装容量或冷却限制。",
        "新衣未通过审核，已隔离且未应用。",
        "新衣生成失败，未安装任何素材。",
        "自主选装目前已关闭。",
        "自主选装评估失败，已保留当前衣装。",
        "墨寒已根据情境自主换装。",
        "让墨寒依天气、心情与场合挑选完整造型，也保留您的决定。",
        "来源分流：炎剑官方・用户导入・墨寒自创",
        "墨色为骨・寒光为心",
        "墨寒造型预览",
        "正面",
        "左侧",
        "右侧",
        "背面",
        "上传单个文件",
        "已安装，未启用",
        "服装预览",
        "发型预览",
        "头饰与配件",
        "一键预览整套造型",
        "保存后生效",
        "取消并恢复",
        "移除扩展包",
        "确定移除「{package}」吗？",
        "内置包无法移除",
        "请先切换，再移除正在使用的包",
        "缺少套件，已保留当前造型",
        "主题预览",
        "还原主题",
        "套件含危险内容或缺少文件，已整包拒绝",
        "衣装",
        "发型",
        "头饰",
        "配件",
        "无头饰",
        "妆容",
        "妆容",
        "妆容选择",
        "素颜（不上妆）",
        "原妆",
        "淡雅",
        "妆感浓淡",
        "已应用所选妆容。",
        "已卸妆，回到素颜。",
        "所选妆容的套件已不存在，已改回内置原妆。",
        "这组妆容目前无法应用，已保留当前妆容。",
        "内置妆容素材待补",
        "素体为素颜；妆容与服装、发型、头饰一样是可开关的图层，新妆容请用「导入服装套件」加入。",
    ),
    "en": (
        "Wardrobe Pavilion",
        "Cancel without saving",
        "Import outfit package",
        "Apply selected outfit",
        "Restore built-in outfit",
        "Package list",
        "Compatibility status",
        "Status",
        "No outfit packages installed",
        "Built-in default outfit",
        "Compatible",
        "Incompatible",
        "Wardrobe system is ready",
        "The package failed complete all-view and security validation and was not installed.",
        "This outfit does not include complete assets for every view and cannot be applied.",
        "This outfit was made for the generation-1 body and will not line up on the generation-2 body; regenerate it with one-click outfit creation.",
        "Built-in default outfit applied.",
        "Selected complete outfit applied.",
        "Allow MoHan to choose outfits autonomously",
        "Allow MoHan to create cloud-generated outfits (charges may apply)",
        "Allow trend search using five context fields for original inspiration (may incur charges)",
        "Searching trends with the five consented context fields, then generating, auditing, and packaging a new outfit (may incur charges)…",
        "Generated outfit retention limit",
        "Generated outfit storage limit",
        "Manual outfit lock duration",
        "No lock",
        "Generate a new outfit now (uses the Image API)",
        "Creating and auditing a new 31-view outfit…",
        "Generating, auditing, and packaging a new outfit…",
        "The new outfit passed audit, was installed, and is now active.",
        "The new outfit passed audit and was installed. The current manually selected outfit remains active until its lock expires.",
        "The new outfit passed audit and was installed, but could not be activated safely; the current outfit was preserved.",
        "Enable cloud outfit creation first.",
        "No usable OpenAI API key is configured.",
        "The generated-outfit capacity or cooldown limit was reached.",
        "The new outfit failed audit and was quarantined without being applied.",
        "Outfit generation failed; no assets were installed.",
        "Autonomous outfit selection is currently disabled.",
        "Autonomous selection failed; the current outfit was preserved.",
        "MoHan changed outfits autonomously for the current context.",
        "Let MoHan choose a complete look for the weather, mood, and occasion while preserving your final say.",
        "Separated sources: Flameblade official · User imports · MoHan creations",
        "Ink in her bones · Cold light in her heart",
        "MoHan appearance preview",
        "Front",
        "Left",
        "Right",
        "Back",
        "Upload one file",
        "Installed, not active",
        "Outfit preview",
        "Hairstyle preview",
        "Headwear and accessories",
        "Preview complete look",
        "Takes effect after saving",
        "Cancel to restore",
        "Remove add-on",
        "Remove {package}?",
        "Built-in packages cannot be removed",
        "Switch packages before removing the active one",
        "Package missing; kept the current look",
        "Theme preview",
        "Restore theme",
        "Package rejected: unsafe or missing files",
        "Outfit",
        "Hairstyle",
        "Headwear",
        "Accessory",
        "No headwear",
        "Makeup",
        "Makeup",
        "Makeup selection",
        "Bare face (no makeup)",
        "Classic",
        "Light",
        "Makeup intensity",
        "Selected makeup applied.",
        "Makeup removed; back to a bare face.",
        "The selected makeup pack is gone; switched back to the built-in classic makeup.",
        "This makeup cannot be applied right now; the current makeup was kept.",
        "built-in makeup art pending",
        "The base body is bare-faced; makeup is a switchable layer like garments, hairstyles and headwear. "
        "Add new makeup with \"Import outfit package\".",
    ),
    "ja-JP": (
        "雲裳閣",
        "保存せずに取り消す",
        "衣装パッケージをインポート",
        "選択した衣装を適用",
        "内蔵衣装に戻す",
        "パッケージ一覧",
        "互換性状態",
        "状態",
        "衣装パッケージはまだインストールされていません",
        "内蔵の既定衣装",
        "互換",
        "非互換",
        "雲裳システムの準備ができました",
        "パッケージは全視点の完全性と安全性の検証に合格していないため、インストールされませんでした。",
        "この衣装には全視点の完全な素材がないため、適用できません。",
        "この衣装は第一世代素体向けに作られたもので、第二世代素体では位置が合いません。ワンクリック衣装生成で作り直してください",
        "内蔵の既定衣装を適用しました。",
        "選択した完全な衣装を適用しました。",
        "墨寒による自律的な衣装選択を許可",
        "墨寒によるクラウドでの新衣装生成を許可（料金が発生する場合があります）",
        "同意済みの5種類の状況情報で流行を検索し、独自デザインの着想に利用する（料金が発生する場合があります）",
        "同意済みの5種類の状況情報で流行を検索し、新衣装を生成・監査・パッケージ化しています（料金が発生する場合があります）…",
        "自作衣装の保存上限",
        "自作衣装の容量上限",
        "手動衣装のロック時間",
        "ロックしない",
        "新しい衣装を今すぐ生成（Image API を使用）",
        "31視点の新衣装を作成し、安全監査を実行しています…",
        "新衣装を生成・監査・パッケージ化しています…",
        "新衣装は監査に合格し、インストールして適用されました。",
        "新衣装は監査に合格してインストールされました。手動で選んだ衣装はロック期限まで維持されます。",
        "新衣装は監査に合格してインストールされましたが、安全に適用できなかったため現在の衣装を維持します。",
        "先にクラウド衣装生成を有効にしてください。",
        "使用可能な OpenAI API キーが設定されていません。",
        "生成衣装の容量またはクールダウン上限に達しました。",
        "新衣装は監査に合格せず、適用せず隔離しました。",
        "衣装生成に失敗し、素材はインストールされませんでした。",
        "自律衣装選択は現在無効です。",
        "自律選択に失敗したため、現在の衣装を維持しました。",
        "墨寒が状況に合わせて自律的に着替えました。",
        "天候・気分・場面に合わせて墨寒が一式を選び、あなたの決定も尊重します。",
        "提供元を分離：炎剣公式・ユーザー導入・墨寒の自作",
        "墨を骨とし・寒光を心とする",
        "墨寒スタイルプレビュー",
        "正面",
        "左側",
        "右側",
        "背面",
        "ファイルを1つアップロード",
        "インストール済み・未適用",
        "衣装プレビュー",
        "髪型プレビュー",
        "髪飾り・アクセサリー",
        "一式をまとめてプレビュー",
        "保存後に反映",
        "取り消して元に戻す",
        "追加パッケージを削除",
        "「{package}」を削除しますか？",
        "内蔵パッケージは削除できません",
        "使用中のパッケージを切り替えてから削除してください",
        "パッケージが見つからないため、現在の外観を維持しました",
        "テーマプレビュー",
        "テーマを元に戻す",
        "危険な内容または不足ファイルがあるため、パッケージ全体を拒否しました",
        "衣装",
        "髪型",
        "髪飾り",
        "アクセサリー",
        "髪飾りなし",
        "メイク",
        "メイク",
        "メイクの選択",
        "すっぴん（メイクなし）",
        "基本メイク",
        "淡めメイク",
        "メイクの濃さ",
        "選択したメイクを適用しました。",
        "メイクを落とし、すっぴんに戻しました。",
        "選択したメイクのパッケージが見つからないため、内蔵の基本メイクに戻しました。",
        "このメイクは現在適用できないため、現在のメイクを維持しました。",
        "内蔵メイク素材は準備中",
        "素体はすっぴんです。メイクは衣装・髪型・髪飾りと同じ切り替え可能なレイヤーで、新しいメイクは「衣装パッケージをインポート」で追加します。",
    ),
}

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
MOJIBAKE_MARKERS = ("\ufffd", "Ã", "Â", "銝", "隞", "撠", "雿", "蝟", "摰")


def format_fields(template: str) -> frozenset[str]:
    return frozenset(
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(
            template
        )
        if field_name is not None
    )


def module_tree(path: Path) -> ast.Module:
    assert path.is_file(), path
    return ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )


def generic_ui_owner_paths() -> tuple[Path, ...]:
    discovered = {
        *PRESENTATION_ROOT.glob(pattern)
        for pattern in GENERIC_UI_OWNER_PATTERNS
    }
    discovered.update(GENERIC_UI_OWNER_PATHS)
    return tuple(sorted(discovered, key=lambda path: path.name))


def literal_call_argument(
    call: ast.Call,
    function_name: str,
    argument_index: int,
) -> str | None:
    function = call.func
    called_name = (
        function.attr
        if isinstance(function, ast.Attribute)
        else function.id if isinstance(function, ast.Name) else ""
    )
    if called_name != function_name or len(call.args) <= argument_index:
        return None
    argument = call.args[argument_index]
    if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
        return None
    return argument.value


def generic_ui_keys() -> frozenset[str]:
    keys: set[str] = set()
    for path in generic_ui_owner_paths():
        for node in ast.walk(module_tree(path)):
            if not isinstance(node, ast.Call):
                continue
            local_key = literal_call_argument(node, "_t", 0)
            catalog_key = literal_call_argument(node, "ui_text", 1)
            if local_key is not None:
                keys.add(local_key)
            if catalog_key is not None:
                keys.add(catalog_key)
    return frozenset(keys)


def flagship_ui_sources() -> frozenset[str]:
    return frozenset(
        source
        for path in FLAGSHIP_UI_OWNER_ROOT.glob("*.py")
        for node in ast.walk(module_tree(path))
        if (
            isinstance(node, ast.Call)
            and (source := literal_call_argument(node, "_t", 0)) is not None
        )
    )


def first_run_fallbacks() -> dict[str, str]:
    fallbacks: dict[str, str] = {}
    for node in ast.walk(
        module_tree(PRESENTATION_ROOT / "first_run_wizard.py")
    ):
        if not isinstance(node, ast.Call):
            continue
        key = literal_call_argument(node, "_t", 0)
        fallback = literal_call_argument(node, "_t", 1)
        if key is not None and fallback is not None:
            fallbacks[key] = fallback
    return fallbacks


def assert_app_is_thin_entrypoint() -> None:
    tree = module_tree(APP_PATH)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert [function.name for function in functions] == ["main"]
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    assert not any(
        isinstance(node, ast.Call)
        and literal_call_argument(node, "_t", 0) is not None
        for node in ast.walk(tree)
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "application.application_bootstrap"
        and any(alias.name == "run_application" for alias in node.names)
        for node in tree.body
    )
    returned_calls = {
        node.value.func.id
        for node in ast.walk(functions[0])
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    }
    assert returned_calls == {"run_application"}


def main() -> None:
    translations = {
        "en": _ENGLISH,
        "zh-CN": _SIMPLIFIED_CHINESE,
        "ja-JP": _JAPANESE,
    }
    expected_keys = set(_ENGLISH)
    for language, values in translations.items():
        assert set(values) == expected_keys, language
        assert all(str(value).strip() for value in values.values()), language

    assert_app_is_thin_entrypoint()
    used_keys = generic_ui_keys()
    assert used_keys, "no UI localization keys were discovered"
    for language, values in translations.items():
        missing = used_keys - set(values)
        assert not missing, f"{language} missing UI keys: {sorted(missing)}"

    validate_flagship_translations()
    assert FLAGSHIP_TRANSLATIONS
    flagship_sources = flagship_ui_sources()
    assert flagship_sources, "no flagship localization sources were discovered"
    for language in ("zh-CN", "en", "ja-JP"):
        translator = FlagshipTranslator(language)
        for source in flagship_sources:
            translated = translator.text(source)
            assert translated.strip(), (language, source)
            assert format_fields(translated) == format_fields(source), (
                language,
                source,
            )

    fallbacks = first_run_fallbacks()
    assert fallbacks["first_run_heading"] == (
        "<b>歡迎使用墨寒桌面陪伴工作助理</b>"
    )
    assert "欢迎" in _SIMPLIFIED_CHINESE["first_run_heading"]
    assert "MoHan" in _ENGLISH["first_run_heading"]
    assert "ようこそ" in _JAPANESE["first_run_heading"]

    keys = tuple(WARDROBE_SOURCES)
    for language, expected in WARDROBE_EXPECTED.items():
        actual = tuple(
            ui_text(language, key, WARDROBE_SOURCES[key])
            for key in keys
        )
        assert actual == expected, language
        assert not any(
            marker in text
            for text in actual
            for marker in MOJIBAKE_MARKERS
        ), language
    for key in keys:
        expected_fields = format_fields(WARDROBE_SOURCES[key])
        assert all(
            format_fields(ui_text(language, key, WARDROBE_SOURCES[key]))
            == expected_fields
            for language in WARDROBE_EXPECTED
        ), key
    english_appearance_text = "\n".join(WARDROBE_EXPECTED["en"])
    assert not CJK.search(english_appearance_text)
    generic_contract = "\n".join(
        text
        for values in WARDROBE_EXPECTED.values()
        for text in values
    ).casefold()
    assert "林可芸" not in generic_contract
    assert "commercial" not in generic_contract
    assert "商業" not in generic_contract
    print("TRANSLATION_COMPLETENESS_OK")


if __name__ == "__main__":
    main()
