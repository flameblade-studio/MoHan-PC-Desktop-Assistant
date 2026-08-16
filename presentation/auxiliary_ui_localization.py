from __future__ import annotations

lazy from collections.abc import Mapping
lazy from enum import StrEnum

lazy from domain.language_support import canonical_ui_language
lazy from domain.safe_error import SafeError
lazy from domain.safe_error_localization import safe_error_message


class AuxiliaryText(StrEnum):
    """Complete, typed text contract for auxiliary desktop panels."""

    UPDATE_TITLE = "update_title"
    CURRENT_VERSION = "current_version"
    CHANNEL_STABLE = "channel_stable"
    CHANNEL_PREVIEW = "channel_preview"
    AUTO_CHECK = "auto_check"
    CHECK_NOW = "check_now"
    DOWNLOAD_INSTALL = "download_install"
    CHANNEL_LABEL = "channel_label"
    NOT_CHECKED = "not_checked"
    NOTES_PLACEHOLDER = "notes_placeholder"
    CHECKING = "checking"
    UP_TO_DATE = "up_to_date"
    NEW_VERSION = "new_version"
    NO_RELEASE_NOTES = "no_release_notes"
    NEW_VERSION_TITLE = "new_version_title"
    NEW_VERSION_AVAILABLE = "new_version_available"
    DOWNLOAD_TITLE = "download_title"
    DOWNLOAD_PROMPT = "download_prompt"
    DOWNLOADING = "downloading"
    VERIFIED_TITLE = "verified_title"
    VERIFIED_PROMPT = "verified_prompt"
    SAFE_DOWNLOADED = "safe_downloaded"
    INSTALLER_LAUNCH_FAILED = "installer_launch_failed"
    UPDATE_DIALOG_TITLE = "update_dialog_title"
    UPDATE_ERROR_NO_RELEASE = "update_error_no_release"
    UPDATE_ERROR_CONNECTION = "update_error_connection"
    UPDATE_ERROR_SECURITY = "update_error_security"
    UPDATE_ERROR_DATA = "update_error_data"
    UPDATE_ERROR_VERSION = "update_error_version"
    UPDATE_ERROR_DOWNLOAD = "update_error_download"
    UPDATE_ERROR_GENERIC = "update_error_generic"
    PROFILE_HEADING = "profile_heading"
    PROFILE_NOTE = "profile_note"
    INCLUDE_ENCRYPTED_SENSITIVE_DATA = "include_encrypted_sensitive_data"
    STRONG_PASSWORD = "strong_password"
    CONFIRM_STRONG_PASSWORD = "confirm_strong_password"
    SENSITIVE_DATA_WARNING = "sensitive_data_warning"
    PASSWORD_MISMATCH = "password_mismatch"
    EXPORT_COMPLETE_WITH_SENSITIVE = "export_complete_with_sensitive"
    EXPORT_COMPLETE_WITHOUT_SENSITIVE = "export_complete_without_sensitive"
    IMPORT_ENCRYPTED_PASSWORD_PROMPT = "import_encrypted_password_prompt"
    ENCRYPTED_CONTENT_AUTH_FAILED = "encrypted_content_auth_failed"
    IMPORT_VISION_REMAINS_OFF = "import_vision_remains_off"
    SENSITIVE_DATA_RESTORED = "sensitive_data_restored"
    EXPORT_BUTTON = "export_button"
    IMPORT_BUTTON = "import_button"
    DEFAULT_ASSISTANT_NAME = "default_assistant_name"
    EXPORT_FILENAME = "export_filename"
    EXPORT_DIALOG_TITLE = "export_dialog_title"
    PROFILE_FILTER = "profile_filter"
    EXPORT_FAILED_TITLE = "export_failed_title"
    EXPORT_FAILED = "export_failed"
    EXPORT_COMPLETE_TITLE = "export_complete_title"
    EXPORT_COMPLETE = "export_complete"
    IMPORT_DIALOG_TITLE = "import_dialog_title"
    IMPORT_READ_FAILED_TITLE = "import_read_failed_title"
    IMPORT_READ_FAILED = "import_read_failed"
    LEGACY_SOURCE = "legacy_source"
    UNKNOWN = "unknown"
    UNNAMED = "unnamed"
    OLDER_WARNING = "older_warning"
    IMPORT_CONFIRM_TITLE = "import_confirm_title"
    IMPORT_CONFIRM = "import_confirm"
    IMPORT_FAILED_TITLE = "import_failed_title"
    IMPORT_FAILED = "import_failed"
    IMPORT_COMPLETE_TITLE = "import_complete_title"
    IMPORT_COMPLETE = "import_complete"
    PROFILE_ERROR_NOT_FOUND = "profile_error_not_found"
    PROFILE_ERROR_FORMAT = "profile_error_format"
    PROFILE_ERROR_SECURITY = "profile_error_security"
    PROFILE_ERROR_DUPLICATE = "profile_error_duplicate"
    PROFILE_ERROR_DATABASE = "profile_error_database"
    PROFILE_ERROR_GENERIC = "profile_error_generic"


class AuxiliaryOperation(StrEnum):
    """Backend operation families that need user-facing error localization."""

    PROFILE = "profile"
    UPDATE = "update"


_ZH_TW: Mapping[AuxiliaryText, str] = frozendict({
    AuxiliaryText.UPDATE_TITLE: "<b>軟體更新</b>",
    AuxiliaryText.CURRENT_VERSION: "目前版本：{version}",
    AuxiliaryText.CHANNEL_STABLE: "穩定版（建議）",
    AuxiliaryText.CHANNEL_PREVIEW: "預覽版／RC",
    AuxiliaryText.AUTO_CHECK: "啟動後自動檢查更新",
    AuxiliaryText.CHECK_NOW: "立即檢查更新",
    AuxiliaryText.DOWNLOAD_INSTALL: "下載並安裝",
    AuxiliaryText.CHANNEL_LABEL: "更新頻道",
    AuxiliaryText.NOT_CHECKED: "尚未檢查",
    AuxiliaryText.NOTES_PLACEHOLDER: "有新版本時會在此顯示版本說明。",
    AuxiliaryText.CHECKING: "正在安全地檢查 GitHub Release……",
    AuxiliaryText.UP_TO_DATE: "目前已是此更新頻道的最新版本。",
    AuxiliaryText.NEW_VERSION: "發現新版本 {version}；安裝前會驗證 SHA256。",
    AuxiliaryText.NO_RELEASE_NOTES: "此版本未提供說明。",
    AuxiliaryText.NEW_VERSION_TITLE: "發現墨寒新版本",
    AuxiliaryText.NEW_VERSION_AVAILABLE: "新版本 {version} 已可下載。",
    AuxiliaryText.DOWNLOAD_TITLE: "下載官方更新",
    AuxiliaryText.DOWNLOAD_PROMPT: (
        "將從官方 GitHub Release 下載安裝程式，完成 SHA256 驗證後再啟動。\n\n"
        "版本：{version}\n檔案：{filename}\n\n是否繼續？"
    ),
    AuxiliaryText.DOWNLOADING: "正在下載並核對安裝程式……",
    AuxiliaryText.VERIFIED_TITLE: "驗證完成",
    AuxiliaryText.VERIFIED_PROMPT: (
        "SHA256 驗證通過。現在將關閉墨寒並開啟安裝程式。\n"
        "您的對話、記憶、待辦與設定仍保留在本機資料目錄。\n\n"
        "是否立即升級？"
    ),
    AuxiliaryText.SAFE_DOWNLOADED: "已安全下載：{path}",
    AuxiliaryText.INSTALLER_LAUNCH_FAILED: "無法啟動安裝程式。",
    AuxiliaryText.UPDATE_DIALOG_TITLE: "墨寒更新",
    AuxiliaryText.UPDATE_ERROR_NO_RELEASE: "目前沒有此頻道可用的相容更新。",
    AuxiliaryText.UPDATE_ERROR_CONNECTION: (
        "無法連線至 GitHub 更新服務，請檢查網路後再試。"
    ),
    AuxiliaryText.UPDATE_ERROR_SECURITY: (
        "更新因來源、清單、大小或 SHA256 驗證未通過而被安全阻擋。"
    ),
    AuxiliaryText.UPDATE_ERROR_DATA: "GitHub Release 的更新資料無法安全讀取。",
    AuxiliaryText.UPDATE_ERROR_VERSION: "更新版本或頻道資料無效。",
    AuxiliaryText.UPDATE_ERROR_DOWNLOAD: "安裝程式未能完整且安全地下載。",
    AuxiliaryText.UPDATE_ERROR_GENERIC: "更新作業未能安全完成，請稍後再試。",
    AuxiliaryText.PROFILE_HEADING: "<b>攜帶、換機與進度接續</b>",
    AuxiliaryText.PROFILE_NOTE: (
        "匯出後只需攜帶一個檔案，即可在另一台電腦接續對話、記憶、待辦、"
        "靈感與工作進度。預設不包含敏感資料；若選用加密攜帶，也不會攜帶"
        "這台電腦的權限、資料夾路徑或裝置設定。"
    ),
    AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA: (
        "同時加密攜帶 API 金鑰、連線權杖與臉部身分資料（選用）"
    ),
    AuxiliaryText.STRONG_PASSWORD: "輸入強密碼",
    AuxiliaryText.CONFIRM_STRONG_PASSWORD: "再次輸入強密碼",
    AuxiliaryText.SENSITIVE_DATA_WARNING: (
        "敏感資料只會以密碼加密後寫入攜帶檔。請妥善保管密碼；此選項不會攜帶這台電腦的權限或本機路徑。"
    ),
    AuxiliaryText.PASSWORD_MISMATCH: "兩次輸入的密碼不一致。",
    AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE: (
        "墨寒攜帶檔已建立，並包含加密的敏感資料。\n\n位置：{path}\n收錄資料與設定共 {count} 筆。"
    ),
    AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE: (
        "墨寒攜帶檔已建立，未包含 API 金鑰、連線權杖或臉部身分資料。\n\n位置：{path}\n收錄資料與設定共 {count} 筆。"
    ),
    AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT: (
        "偵測到加密的敏感內容。請輸入建立這份攜帶檔時使用的密碼。"
    ),
    AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED: (
        "密碼錯誤或攜帶檔可能已遭修改；敏感資料未匯入。"
    ),
    AuxiliaryText.IMPORT_VISION_REMAINS_OFF: (
        "匯入完成後，攝影機與人臉辨識仍保持關閉，必須由您自行啟用。"
    ),
    AuxiliaryText.SENSITIVE_DATA_RESTORED: "敏感資料已成功安全恢復。",
    AuxiliaryText.EXPORT_BUTTON: "匯出墨寒攜帶檔",
    AuxiliaryText.IMPORT_BUTTON: "匯入並接續進度",
    AuxiliaryText.DEFAULT_ASSISTANT_NAME: "墨寒",
    AuxiliaryText.EXPORT_FILENAME: "{assistant}-攜帶進度-{timestamp}{extension}",
    AuxiliaryText.EXPORT_DIALOG_TITLE: "匯出墨寒攜帶檔",
    AuxiliaryText.PROFILE_FILTER: "墨寒攜帶檔 (*{extension})",
    AuxiliaryText.EXPORT_FAILED_TITLE: "匯出墨寒攜帶檔",
    AuxiliaryText.EXPORT_FAILED: "匯出失敗：{reason}",
    AuxiliaryText.EXPORT_COMPLETE_TITLE: "匯出完成",
    AuxiliaryText.EXPORT_COMPLETE: (
        "墨寒攜帶檔已建立。\n\n位置：{path}\n收錄資料與設定共 {count} 筆。\n\n"
        "此檔案不含 API 金鑰、OAuth 權杖或本機電腦權限。"
    ),
    AuxiliaryText.IMPORT_DIALOG_TITLE: "匯入墨寒攜帶檔",
    AuxiliaryText.IMPORT_READ_FAILED_TITLE: "匯入墨寒攜帶檔",
    AuxiliaryText.IMPORT_READ_FAILED: "無法讀取攜帶檔：{reason}",
    AuxiliaryText.LEGACY_SOURCE: "舊版攜帶檔",
    AuxiliaryText.UNKNOWN: "未知",
    AuxiliaryText.UNNAMED: "未命名",
    AuxiliaryText.OLDER_WARNING: (
        "\n\n⚠ 此檔建立時間早於上次匯入的進度。"
        "若繼續，較新的共同進度可能被取代。"
    ),
    AuxiliaryText.IMPORT_CONFIRM_TITLE: "確認接續進度",
    AuxiliaryText.IMPORT_CONFIRM: (
        "即將以攜帶檔內的共同進度取代這台電腦目前的對話、記憶、待辦與工作資料。"
        "\n\n建立時間：{created_at}\n來源裝置識別：{source}\n助理名稱：{assistant}"
        "\n資料與設定：約 {count} 筆\n\n匯入前會自動備份目前資料；這台電腦的 "
        "API 金鑰、OAuth、權限、路徑與裝置設定將維持不變。{older_warning}"
        "\n\n確定匯入嗎？"
    ),
    AuxiliaryText.IMPORT_FAILED_TITLE: "匯入墨寒攜帶檔",
    AuxiliaryText.IMPORT_FAILED: "匯入失敗，原資料未變更：{reason}",
    AuxiliaryText.IMPORT_COMPLETE_TITLE: "進度接續完成",
    AuxiliaryText.IMPORT_COMPLETE: (
        "墨寒的共同進度已匯入完成。\n\n原資料備份：{path}\n\n"
        "程式現在會安全關閉；請重新開啟墨寒，即可從匯入後的進度繼續使用。"
    ),
    AuxiliaryText.PROFILE_ERROR_NOT_FOUND: "找不到指定的墨寒攜帶檔。",
    AuxiliaryText.PROFILE_ERROR_FORMAT: "攜帶檔格式、版本或資料內容無法安全讀取。",
    AuxiliaryText.PROFILE_ERROR_SECURITY: "攜帶檔未通過安全或完整性驗證。",
    AuxiliaryText.PROFILE_ERROR_DUPLICATE: (
        "這份攜帶檔已匯入過；為避免覆蓋較新的進度，本次未重複匯入。"
    ),
    AuxiliaryText.PROFILE_ERROR_DATABASE: "資料庫匯入失敗；原資料未變更。",
    AuxiliaryText.PROFILE_ERROR_GENERIC: "攜帶檔作業未能安全完成。",
})

_ZH_CN: Mapping[AuxiliaryText, str] = frozendict({
    AuxiliaryText.UPDATE_TITLE: "<b>软件更新</b>",
    AuxiliaryText.CURRENT_VERSION: "当前版本：{version}",
    AuxiliaryText.CHANNEL_STABLE: "稳定版（推荐）",
    AuxiliaryText.CHANNEL_PREVIEW: "预览版／RC",
    AuxiliaryText.AUTO_CHECK: "启动后自动检查更新",
    AuxiliaryText.CHECK_NOW: "立即检查更新",
    AuxiliaryText.DOWNLOAD_INSTALL: "下载并安装",
    AuxiliaryText.CHANNEL_LABEL: "更新频道",
    AuxiliaryText.NOT_CHECKED: "尚未检查",
    AuxiliaryText.NOTES_PLACEHOLDER: "有新版本时会在此显示版本说明。",
    AuxiliaryText.CHECKING: "正在安全地检查 GitHub Release……",
    AuxiliaryText.UP_TO_DATE: "当前已是此更新频道的最新版本。",
    AuxiliaryText.NEW_VERSION: "发现新版本 {version}；安装前会验证 SHA256。",
    AuxiliaryText.NO_RELEASE_NOTES: "此版本未提供说明。",
    AuxiliaryText.NEW_VERSION_TITLE: "发现墨寒新版本",
    AuxiliaryText.NEW_VERSION_AVAILABLE: "新版本 {version} 已可下载。",
    AuxiliaryText.DOWNLOAD_TITLE: "下载官方更新",
    AuxiliaryText.DOWNLOAD_PROMPT: (
        "将从官方 GitHub Release 下载安装程序，完成 SHA256 验证后再启动。\n\n"
        "版本：{version}\n文件：{filename}\n\n是否继续？"
    ),
    AuxiliaryText.DOWNLOADING: "正在下载并核对安装程序……",
    AuxiliaryText.VERIFIED_TITLE: "验证完成",
    AuxiliaryText.VERIFIED_PROMPT: (
        "SHA256 验证通过。现在将关闭墨寒并启动安装程序。\n"
        "您的对话、记忆、待办与设置仍保留在本地数据目录。\n\n"
        "是否立即升级？"
    ),
    AuxiliaryText.SAFE_DOWNLOADED: "已安全下载：{path}",
    AuxiliaryText.INSTALLER_LAUNCH_FAILED: "无法启动安装程序。",
    AuxiliaryText.UPDATE_DIALOG_TITLE: "墨寒更新",
    AuxiliaryText.UPDATE_ERROR_NO_RELEASE: "当前没有此频道可用的兼容更新。",
    AuxiliaryText.UPDATE_ERROR_CONNECTION: (
        "无法连接 GitHub 更新服务，请检查网络后重试。"
    ),
    AuxiliaryText.UPDATE_ERROR_SECURITY: (
        "更新因来源、清单、大小或 SHA256 验证未通过而被安全阻止。"
    ),
    AuxiliaryText.UPDATE_ERROR_DATA: "无法安全读取 GitHub Release 更新数据。",
    AuxiliaryText.UPDATE_ERROR_VERSION: "更新版本或频道数据无效。",
    AuxiliaryText.UPDATE_ERROR_DOWNLOAD: "安装程序未能完整且安全地下载。",
    AuxiliaryText.UPDATE_ERROR_GENERIC: "更新操作未能安全完成，请稍后重试。",
    AuxiliaryText.PROFILE_HEADING: "<b>携带、换机与进度接续</b>",
    AuxiliaryText.PROFILE_NOTE: (
        "导出后只需携带一个文件，即可在另一台电脑接续对话、记忆、待办、"
        "灵感与工作进度。默认不包含敏感数据；即使选择加密携带，也不会携带"
        "这台电脑的权限、文件夹路径或设备设置。"
    ),
    AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA: (
        "同时加密携带 API 密钥、连接令牌与面部身份数据（可选）"
    ),
    AuxiliaryText.STRONG_PASSWORD: "输入强密码",
    AuxiliaryText.CONFIRM_STRONG_PASSWORD: "再次输入强密码",
    AuxiliaryText.SENSITIVE_DATA_WARNING: (
        "敏感数据只会使用密码加密后写入携带文件。请妥善保管密码；此选项不会携带这台电脑的权限或本地路径。"
    ),
    AuxiliaryText.PASSWORD_MISMATCH: "两次输入的密码不一致。",
    AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE: (
        "墨寒携带文件已建立，并包含加密的敏感数据。\n\n位置：{path}\n共收录 {count} 项数据与设置。"
    ),
    AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE: (
        "墨寒携带文件已建立，未包含 API 密钥、连接令牌或面部身份数据。\n\n位置：{path}\n共收录 {count} 项数据与设置。"
    ),
    AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT: (
        "检测到加密的敏感内容。请输入建立这份携带文件时使用的密码。"
    ),
    AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED: (
        "密码错误或携带文件可能已被修改；敏感数据未导入。"
    ),
    AuxiliaryText.IMPORT_VISION_REMAINS_OFF: (
        "导入完成后，摄像头与人脸识别仍保持关闭，必须由您自行启用。"
    ),
    AuxiliaryText.SENSITIVE_DATA_RESTORED: "敏感数据已成功安全恢复。",
    AuxiliaryText.EXPORT_BUTTON: "导出墨寒携带文件",
    AuxiliaryText.IMPORT_BUTTON: "导入并接续进度",
    AuxiliaryText.DEFAULT_ASSISTANT_NAME: "墨寒",
    AuxiliaryText.EXPORT_FILENAME: "{assistant}-携带进度-{timestamp}{extension}",
    AuxiliaryText.EXPORT_DIALOG_TITLE: "导出墨寒携带文件",
    AuxiliaryText.PROFILE_FILTER: "墨寒携带文件 (*{extension})",
    AuxiliaryText.EXPORT_FAILED_TITLE: "导出墨寒携带文件",
    AuxiliaryText.EXPORT_FAILED: "导出失败：{reason}",
    AuxiliaryText.EXPORT_COMPLETE_TITLE: "导出完成",
    AuxiliaryText.EXPORT_COMPLETE: (
        "墨寒携带文件已建立。\n\n位置：{path}\n共收录 {count} 项数据与设置。\n\n"
        "此文件不含 API 密钥、OAuth 令牌或本地电脑权限。"
    ),
    AuxiliaryText.IMPORT_DIALOG_TITLE: "导入墨寒携带文件",
    AuxiliaryText.IMPORT_READ_FAILED_TITLE: "导入墨寒携带文件",
    AuxiliaryText.IMPORT_READ_FAILED: "无法读取携带文件：{reason}",
    AuxiliaryText.LEGACY_SOURCE: "旧版携带文件",
    AuxiliaryText.UNKNOWN: "未知",
    AuxiliaryText.UNNAMED: "未命名",
    AuxiliaryText.OLDER_WARNING: (
        "\n\n⚠ 此文件的建立时间早于上次导入的进度。"
        "若继续，较新的共同进度可能被替换。"
    ),
    AuxiliaryText.IMPORT_CONFIRM_TITLE: "确认接续进度",
    AuxiliaryText.IMPORT_CONFIRM: (
        "即将使用携带文件中的共同进度替换这台电脑当前的对话、记忆、待办与工作数据。"
        "\n\n建立时间：{created_at}\n来源设备标识：{source}\n助手名称：{assistant}"
        "\n数据与设置：约 {count} 项\n\n导入前会自动备份当前数据；这台电脑的 "
        "API 密钥、OAuth、权限、路径与设备设置将保持不变。{older_warning}"
        "\n\n确定导入吗？"
    ),
    AuxiliaryText.IMPORT_FAILED_TITLE: "导入墨寒携带文件",
    AuxiliaryText.IMPORT_FAILED: "导入失败，原数据未更改：{reason}",
    AuxiliaryText.IMPORT_COMPLETE_TITLE: "进度接续完成",
    AuxiliaryText.IMPORT_COMPLETE: (
        "墨寒的共同进度已导入完成。\n\n原数据备份：{path}\n\n"
        "程序现在会安全关闭；请重新打开墨寒，即可从导入后的进度继续使用。"
    ),
    AuxiliaryText.PROFILE_ERROR_NOT_FOUND: "找不到指定的墨寒携带文件。",
    AuxiliaryText.PROFILE_ERROR_FORMAT: "无法安全读取携带文件的格式、版本或数据内容。",
    AuxiliaryText.PROFILE_ERROR_SECURITY: "携带文件未通过安全或完整性验证。",
    AuxiliaryText.PROFILE_ERROR_DUPLICATE: (
        "这份携带文件已经导入；为避免覆盖较新的进度，本次未重复导入。"
    ),
    AuxiliaryText.PROFILE_ERROR_DATABASE: "数据库导入失败；原数据未更改。",
    AuxiliaryText.PROFILE_ERROR_GENERIC: "携带文件操作未能安全完成。",
})

_EN: Mapping[AuxiliaryText, str] = frozendict({
    AuxiliaryText.UPDATE_TITLE: "<b>Software updates</b>",
    AuxiliaryText.CURRENT_VERSION: "Current version: {version}",
    AuxiliaryText.CHANNEL_STABLE: "Stable (recommended)",
    AuxiliaryText.CHANNEL_PREVIEW: "Preview / RC",
    AuxiliaryText.AUTO_CHECK: "Check for updates after startup",
    AuxiliaryText.CHECK_NOW: "Check now",
    AuxiliaryText.DOWNLOAD_INSTALL: "Download and install",
    AuxiliaryText.CHANNEL_LABEL: "Update channel",
    AuxiliaryText.NOT_CHECKED: "Not checked yet",
    AuxiliaryText.NOTES_PLACEHOLDER: "Release notes appear here when an update is available.",
    AuxiliaryText.CHECKING: "Safely checking GitHub Releases…",
    AuxiliaryText.UP_TO_DATE: "You already have the latest version in this channel.",
    AuxiliaryText.NEW_VERSION: (
        "Version {version} is available. Its SHA256 will be verified before installation."
    ),
    AuxiliaryText.NO_RELEASE_NOTES: "No release notes were provided for this version.",
    AuxiliaryText.NEW_VERSION_TITLE: "A new MoHan version is available",
    AuxiliaryText.NEW_VERSION_AVAILABLE: "Version {version} is ready to download.",
    AuxiliaryText.DOWNLOAD_TITLE: "Download the official update",
    AuxiliaryText.DOWNLOAD_PROMPT: (
        "The installer will be downloaded from the official GitHub Release and started only "
        "after SHA256 verification.\n\nVersion: {version}\nFile: {filename}\n\nContinue?"
    ),
    AuxiliaryText.DOWNLOADING: "Downloading and verifying the installer…",
    AuxiliaryText.VERIFIED_TITLE: "Verification complete",
    AuxiliaryText.VERIFIED_PROMPT: (
        "SHA256 verification passed. MoHan will now close and start the installer.\n"
        "Your chats, memories, tasks, and settings remain in the local data folder.\n\n"
        "Upgrade now?"
    ),
    AuxiliaryText.SAFE_DOWNLOADED: "Safely downloaded: {path}",
    AuxiliaryText.INSTALLER_LAUNCH_FAILED: "The installer could not be started.",
    AuxiliaryText.UPDATE_DIALOG_TITLE: "MoHan update",
    AuxiliaryText.UPDATE_ERROR_NO_RELEASE: (
        "No compatible published update is currently available in this channel."
    ),
    AuxiliaryText.UPDATE_ERROR_CONNECTION: (
        "GitHub's update service could not be reached. Check your connection and try again."
    ),
    AuxiliaryText.UPDATE_ERROR_SECURITY: (
        "The update was safely blocked because its source, manifest, size, or SHA256 "
        "verification did not pass."
    ),
    AuxiliaryText.UPDATE_ERROR_DATA: "The GitHub Release data could not be read safely.",
    AuxiliaryText.UPDATE_ERROR_VERSION: "The update version or channel data is invalid.",
    AuxiliaryText.UPDATE_ERROR_DOWNLOAD: (
        "The installer could not be downloaded completely and safely."
    ),
    AuxiliaryText.UPDATE_ERROR_GENERIC: (
        "The update operation could not be completed safely. Please try again later."
    ),
    AuxiliaryText.PROFILE_HEADING: "<b>Move devices and continue your progress</b>",
    AuxiliaryText.PROFILE_NOTE: (
        "Export one portable file to continue your chats, memories, tasks, ideas, and work "
        "progress on another computer. Sensitive data is excluded by default. Even when "
        "encrypted sensitive data is selected, this computer's permissions, folder paths, "
        "and device settings are not transferred."
    ),
    AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA: (
        "Also include encrypted API keys, connection tokens, and face identity data (optional)"
    ),
    AuxiliaryText.STRONG_PASSWORD: "Enter a strong password",
    AuxiliaryText.CONFIRM_STRONG_PASSWORD: "Enter the strong password again",
    AuxiliaryText.SENSITIVE_DATA_WARNING: (
        "Sensitive data is written to the portable profile only after password encryption. "
        "Keep the password safe. This option does not transfer this computer's permissions "
        "or local paths."
    ),
    AuxiliaryText.PASSWORD_MISMATCH: "The two passwords do not match.",
    AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE: (
        "The portable MoHan profile was created with encrypted sensitive data.\n\n"
        "Location: {path}\nIt contains {count} data and setting records."
    ),
    AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE: (
        "The portable MoHan profile was created without API keys, connection tokens, or "
        "face identity data.\n\nLocation: {path}\n"
        "It contains {count} data and setting records."
    ),
    AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT: (
        "Encrypted sensitive content was detected. Enter the password used to create this "
        "portable profile."
    ),
    AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED: (
        "The password is incorrect or the portable profile may have been modified. "
        "Sensitive data was not imported."
    ),
    AuxiliaryText.IMPORT_VISION_REMAINS_OFF: (
        "After import, the camera and face recognition remain off until you enable them."
    ),
    AuxiliaryText.SENSITIVE_DATA_RESTORED: "Sensitive data was restored securely.",
    AuxiliaryText.EXPORT_BUTTON: "Export portable MoHan profile",
    AuxiliaryText.IMPORT_BUTTON: "Import and continue",
    AuxiliaryText.DEFAULT_ASSISTANT_NAME: "MoHan",
    AuxiliaryText.EXPORT_FILENAME: "{assistant}-portable-progress-{timestamp}{extension}",
    AuxiliaryText.EXPORT_DIALOG_TITLE: "Export portable MoHan profile",
    AuxiliaryText.PROFILE_FILTER: "MoHan portable profile (*{extension})",
    AuxiliaryText.EXPORT_FAILED_TITLE: "Portable profile export",
    AuxiliaryText.EXPORT_FAILED: "Export failed: {reason}",
    AuxiliaryText.EXPORT_COMPLETE_TITLE: "Export complete",
    AuxiliaryText.EXPORT_COMPLETE: (
        "The portable MoHan profile was created.\n\nLocation: {path}\n"
        "Included data and settings: {count}.\n\nThis file contains no API keys, "
        "OAuth tokens, or local computer permissions."
    ),
    AuxiliaryText.IMPORT_DIALOG_TITLE: "Import portable MoHan profile",
    AuxiliaryText.IMPORT_READ_FAILED_TITLE: "Portable profile import",
    AuxiliaryText.IMPORT_READ_FAILED: "The portable profile could not be read: {reason}",
    AuxiliaryText.LEGACY_SOURCE: "Legacy portable profile",
    AuxiliaryText.UNKNOWN: "Unknown",
    AuxiliaryText.UNNAMED: "Unnamed",
    AuxiliaryText.OLDER_WARNING: (
        "\n\n⚠ This file was created before the last imported progress. Continuing may "
        "replace newer shared progress."
    ),
    AuxiliaryText.IMPORT_CONFIRM_TITLE: "Confirm progress import",
    AuxiliaryText.IMPORT_CONFIRM: (
        "The shared progress in this portable profile will replace this computer's current "
        "chats, memories, tasks, and work data.\n\nCreated: {created_at}\n"
        "Source device ID: {source}\nAssistant name: {assistant}\n"
        "Data and settings: about {count}\n\nCurrent data will be backed up first. "
        "This computer's API keys, OAuth credentials, permissions, paths, and device settings "
        "will remain unchanged.{older_warning}\n\nImport this profile?"
    ),
    AuxiliaryText.IMPORT_FAILED_TITLE: "Portable profile import",
    AuxiliaryText.IMPORT_FAILED: "Import failed; existing data was not changed: {reason}",
    AuxiliaryText.IMPORT_COMPLETE_TITLE: "Progress import complete",
    AuxiliaryText.IMPORT_COMPLETE: (
        "MoHan's shared progress was imported.\n\nExisting data backup: {path}\n\n"
        "The application will now close safely. Reopen MoHan to continue from the imported "
        "progress."
    ),
    AuxiliaryText.PROFILE_ERROR_NOT_FOUND: "The selected portable MoHan profile was not found.",
    AuxiliaryText.PROFILE_ERROR_FORMAT: (
        "The portable profile's format, version, or data could not be read safely."
    ),
    AuxiliaryText.PROFILE_ERROR_SECURITY: (
        "The portable profile did not pass its security or integrity checks."
    ),
    AuxiliaryText.PROFILE_ERROR_DUPLICATE: (
        "This portable profile was already imported. It was not imported again, protecting "
        "newer progress from being overwritten."
    ),
    AuxiliaryText.PROFILE_ERROR_DATABASE: (
        "The database import failed; existing data was not changed."
    ),
    AuxiliaryText.PROFILE_ERROR_GENERIC: (
        "The portable profile operation could not be completed safely."
    ),
})

_JA: Mapping[AuxiliaryText, str] = frozendict({
    AuxiliaryText.UPDATE_TITLE: "<b>ソフトウェア更新</b>",
    AuxiliaryText.CURRENT_VERSION: "現在のバージョン：{version}",
    AuxiliaryText.CHANNEL_STABLE: "安定版（推奨）",
    AuxiliaryText.CHANNEL_PREVIEW: "プレビュー版／RC",
    AuxiliaryText.AUTO_CHECK: "起動後に更新を自動確認",
    AuxiliaryText.CHECK_NOW: "今すぐ確認",
    AuxiliaryText.DOWNLOAD_INSTALL: "ダウンロードしてインストール",
    AuxiliaryText.CHANNEL_LABEL: "更新チャンネル",
    AuxiliaryText.NOT_CHECKED: "まだ確認していません",
    AuxiliaryText.NOTES_PLACEHOLDER: "更新がある場合、ここにリリースノートを表示します。",
    AuxiliaryText.CHECKING: "GitHub Release を安全に確認しています……",
    AuxiliaryText.UP_TO_DATE: "この更新チャンネルでは最新バージョンです。",
    AuxiliaryText.NEW_VERSION: (
        "新しいバージョン {version} があります。インストール前に SHA256 を検証します。"
    ),
    AuxiliaryText.NO_RELEASE_NOTES: "このバージョンには説明がありません。",
    AuxiliaryText.NEW_VERSION_TITLE: "墨寒の新しいバージョンがあります",
    AuxiliaryText.NEW_VERSION_AVAILABLE: "バージョン {version} をダウンロードできます。",
    AuxiliaryText.DOWNLOAD_TITLE: "公式アップデートをダウンロード",
    AuxiliaryText.DOWNLOAD_PROMPT: (
        "公式 GitHub Release からインストーラーをダウンロードし、SHA256 検証後に"
        "起動します。\n\nバージョン：{version}\nファイル：{filename}\n\n続行しますか？"
    ),
    AuxiliaryText.DOWNLOADING: "インストーラーをダウンロードして検証しています……",
    AuxiliaryText.VERIFIED_TITLE: "検証完了",
    AuxiliaryText.VERIFIED_PROMPT: (
        "SHA256 検証に合格しました。墨寒を終了してインストーラーを起動します。\n"
        "会話、記憶、予定、設定はローカルデータフォルダーに保持されます。\n\n"
        "今すぐアップグレードしますか？"
    ),
    AuxiliaryText.SAFE_DOWNLOADED: "安全にダウンロードしました：{path}",
    AuxiliaryText.INSTALLER_LAUNCH_FAILED: "インストーラーを起動できませんでした。",
    AuxiliaryText.UPDATE_DIALOG_TITLE: "墨寒の更新",
    AuxiliaryText.UPDATE_ERROR_NO_RELEASE: "このチャンネルで利用できる互換更新はありません。",
    AuxiliaryText.UPDATE_ERROR_CONNECTION: (
        "GitHub の更新サービスに接続できません。ネットワークを確認して再試行してください。"
    ),
    AuxiliaryText.UPDATE_ERROR_SECURITY: (
        "配布元、マニフェスト、サイズ、または SHA256 の検証に合格しなかったため、"
        "更新を安全に停止しました。"
    ),
    AuxiliaryText.UPDATE_ERROR_DATA: "GitHub Release の更新データを安全に読み取れません。",
    AuxiliaryText.UPDATE_ERROR_VERSION: "更新バージョンまたはチャンネルのデータが無効です。",
    AuxiliaryText.UPDATE_ERROR_DOWNLOAD: (
        "インストーラーを完全かつ安全にダウンロードできませんでした。"
    ),
    AuxiliaryText.UPDATE_ERROR_GENERIC: (
        "更新処理を安全に完了できませんでした。後でもう一度お試しください。"
    ),
    AuxiliaryText.PROFILE_HEADING: "<b>持ち運び、端末移行、進捗の継続</b>",
    AuxiliaryText.PROFILE_NOTE: (
        "一つのポータブルファイルを書き出すだけで、別のパソコンでも会話、記憶、予定、"
        "アイデア、作業進捗を継続できます。機密データは既定で含まれません。暗号化した"
        "機密データを選んでも、この端末の権限、フォルダーパス、端末設定は移行されません。"
    ),
    AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA: (
        "API キー、接続トークン、顔識別データも暗号化して含める（任意）"
    ),
    AuxiliaryText.STRONG_PASSWORD: "強力なパスワードを入力",
    AuxiliaryText.CONFIRM_STRONG_PASSWORD: "強力なパスワードを再入力",
    AuxiliaryText.SENSITIVE_DATA_WARNING: (
        "機密データはパスワードで暗号化した後にのみポータブルプロファイルへ保存されます。"
        "パスワードを安全に保管してください。この設定では、この端末の権限やローカルパスは移行されません。"
    ),
    AuxiliaryText.PASSWORD_MISMATCH: "2回入力したパスワードが一致しません。",
    AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE: (
        "暗号化された機密データを含む墨寒ポータブルプロファイルを作成しました。\n\n"
        "保存場所：{path}\nデータと設定を合計 {count} 件収録しました。"
    ),
    AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE: (
        "API キー、接続トークン、顔識別データを含まない墨寒ポータブルプロファイルを作成しました。\n\n"
        "保存場所：{path}\nデータと設定を合計 {count} 件収録しました。"
    ),
    AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT: (
        "暗号化された機密内容を検出しました。このポータブルプロファイルの作成時に使用したパスワードを入力してください。"
    ),
    AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED: (
        "パスワードが正しくないか、ポータブルプロファイルが変更された可能性があります。機密データは読み込まれませんでした。"
    ),
    AuxiliaryText.IMPORT_VISION_REMAINS_OFF: (
        "読み込み完了後も、カメラと顔認識はオフのままです。使用するにはご自身で有効にしてください。"
    ),
    AuxiliaryText.SENSITIVE_DATA_RESTORED: "機密データを安全に復元しました。",
    AuxiliaryText.EXPORT_BUTTON: "墨寒ポータブルプロファイルを書き出す",
    AuxiliaryText.IMPORT_BUTTON: "読み込んで進捗を継続",
    AuxiliaryText.DEFAULT_ASSISTANT_NAME: "墨寒",
    AuxiliaryText.EXPORT_FILENAME: "{assistant}-ポータブル進捗-{timestamp}{extension}",
    AuxiliaryText.EXPORT_DIALOG_TITLE: "墨寒ポータブルプロファイルを書き出す",
    AuxiliaryText.PROFILE_FILTER: "墨寒ポータブルプロファイル (*{extension})",
    AuxiliaryText.EXPORT_FAILED_TITLE: "ポータブルプロファイルの書き出し",
    AuxiliaryText.EXPORT_FAILED: "書き出しに失敗しました：{reason}",
    AuxiliaryText.EXPORT_COMPLETE_TITLE: "書き出し完了",
    AuxiliaryText.EXPORT_COMPLETE: (
        "墨寒ポータブルプロファイルを作成しました。\n\n保存先：{path}\n"
        "収録したデータと設定：{count} 件。\n\nこのファイルには API キー、OAuth トークン、"
        "ローカルパソコンの権限は含まれません。"
    ),
    AuxiliaryText.IMPORT_DIALOG_TITLE: "墨寒ポータブルプロファイルを読み込む",
    AuxiliaryText.IMPORT_READ_FAILED_TITLE: "ポータブルプロファイルの読み込み",
    AuxiliaryText.IMPORT_READ_FAILED: "ポータブルプロファイルを読み取れません：{reason}",
    AuxiliaryText.LEGACY_SOURCE: "旧形式のポータブルプロファイル",
    AuxiliaryText.UNKNOWN: "不明",
    AuxiliaryText.UNNAMED: "名称なし",
    AuxiliaryText.OLDER_WARNING: (
        "\n\n⚠ このファイルは前回読み込んだ進捗より前に作成されています。続行すると、"
        "新しい共有進捗が置き換わる可能性があります。"
    ),
    AuxiliaryText.IMPORT_CONFIRM_TITLE: "進捗の読み込みを確認",
    AuxiliaryText.IMPORT_CONFIRM: (
        "ポータブルプロファイル内の共有進捗で、このパソコンにある現在の会話、記憶、"
        "予定、作業データを置き換えます。\n\n作成日時：{created_at}\n"
        "移行元端末 ID：{source}\nアシスタント名：{assistant}\n"
        "データと設定：約 {count} 件\n\n読み込み前に現在のデータを自動バックアップします。"
        "このパソコンの API キー、OAuth 認証情報、権限、パス、端末設定は変更されません。"
        "{older_warning}\n\nこのプロファイルを読み込みますか？"
    ),
    AuxiliaryText.IMPORT_FAILED_TITLE: "ポータブルプロファイルの読み込み",
    AuxiliaryText.IMPORT_FAILED: "読み込みに失敗しました。元のデータは変更されていません：{reason}",
    AuxiliaryText.IMPORT_COMPLETE_TITLE: "進捗の読み込み完了",
    AuxiliaryText.IMPORT_COMPLETE: (
        "墨寒の共有進捗を読み込みました。\n\n元データのバックアップ：{path}\n\n"
        "アプリを安全に終了します。墨寒を再度開くと、読み込んだ進捗から利用を続けられます。"
    ),
    AuxiliaryText.PROFILE_ERROR_NOT_FOUND: "選択した墨寒ポータブルプロファイルが見つかりません。",
    AuxiliaryText.PROFILE_ERROR_FORMAT: (
        "ポータブルプロファイルの形式、バージョン、またはデータを安全に読み取れません。"
    ),
    AuxiliaryText.PROFILE_ERROR_SECURITY: (
        "ポータブルプロファイルは安全性または整合性の検証に合格しませんでした。"
    ),
    AuxiliaryText.PROFILE_ERROR_DUPLICATE: (
        "このポータブルプロファイルは読み込み済みです。新しい進捗を上書きしないよう、"
        "再読み込みは行いませんでした。"
    ),
    AuxiliaryText.PROFILE_ERROR_DATABASE: (
        "データベースの読み込みに失敗しました。元のデータは変更されていません。"
    ),
    AuxiliaryText.PROFILE_ERROR_GENERIC: (
        "ポータブルプロファイルの処理を安全に完了できませんでした。"
    ),
})


TRANSLATIONS: Mapping[str, Mapping[AuxiliaryText, str]] = frozendict({
    "zh-TW": _ZH_TW,
    "zh-CN": _ZH_CN,
    "en": _EN,
    "ja-JP": _JA,
})

_EXPECTED_KEYS = frozenset(AuxiliaryText)
for _language, _translations in TRANSLATIONS.items():
    if frozenset(_translations) != _EXPECTED_KEYS:
        missing = sorted(key.value for key in _EXPECTED_KEYS - frozenset(_translations))
        extra = sorted(key.value for key in frozenset(_translations) - _EXPECTED_KEYS)
        raise RuntimeError(
            f"Incomplete auxiliary UI translations for {_language}: "
            f"missing={missing}, extra={extra}"
        )


def auxiliary_text(
    language: str,
    key: AuxiliaryText,
    **values: object,
) -> str:
    """Return one localized auxiliary-UI string from the complete key set."""

    template = TRANSLATIONS[canonical_ui_language(language)][key]
    return template.format(**values) if values else template


def _update_error_key(message: str) -> AuxiliaryText:
    rules = (
        (
            ("目前沒有符合更新頻道", "沒有可用的 Windows 安裝程式"),
            AuxiliaryText.UPDATE_ERROR_NO_RELEASE,
        ),
        (
            ("無法連線", "更新服務回應錯誤"),
            AuxiliaryText.UPDATE_ERROR_CONNECTION,
        ),
        (
            (
                "受信任",
                "登入憑證",
                "SHA256",
                "不屬於官方",
                "檔名不安全",
                "安全大小限制",
            ),
            AuxiliaryText.UPDATE_ERROR_SECURITY,
        ),
        (("下載",), AuxiliaryText.UPDATE_ERROR_DOWNLOAD),
        (
            ("語意版本", "更新頻道必須"),
            AuxiliaryText.UPDATE_ERROR_VERSION,
        ),
        (
            ("格式", "清單", "Release 回應"),
            AuxiliaryText.UPDATE_ERROR_DATA,
        ),
    )
    return next(
        (
            key
            for markers, key in rules
            if any(marker in message for marker in markers)
        ),
        AuxiliaryText.UPDATE_ERROR_GENERIC,
    )


def _profile_error_key(message: str) -> AuxiliaryText:
    if "找不到指定" in message:
        return AuxiliaryText.PROFILE_ERROR_NOT_FOUND
    if "已匯入過" in message:
        return AuxiliaryText.PROFILE_ERROR_DUPLICATE
    if any(
        marker in message
        for marker in ("密鑰", "機器權限", "不安全", "雜湊", "完整性")
    ):
        return AuxiliaryText.PROFILE_ERROR_SECURITY
    if "資料庫" in message or "匯入資料" in message:
        return AuxiliaryText.PROFILE_ERROR_DATABASE
    if any(
        marker in message
        for marker in (
            "版本",
            "資料筆數",
            "內容不完整",
            "超過安全",
            "描述格式",
            "格式識別",
            "不是有效",
            "必要資料表",
            "必要欄位",
            "可安全匯入的欄位",
        )
    ):
        return AuxiliaryText.PROFILE_ERROR_FORMAT
    return AuxiliaryText.PROFILE_ERROR_GENERIC


def localized_operation_error(
    language: str,
    message: str | SafeError,
    *,
    operation: AuxiliaryOperation,
) -> str:
    """Localize backend failures without leaking source-language UI text."""

    normalized_language = canonical_ui_language(language)
    if isinstance(message, SafeError):
        return safe_error_message(normalized_language, message)
    if normalized_language == "zh-TW":
        return str(message).strip() or auxiliary_text(
            language,
            AuxiliaryText.PROFILE_ERROR_GENERIC
            if operation is AuxiliaryOperation.PROFILE
            else AuxiliaryText.UPDATE_ERROR_GENERIC,
        )
    key = (
        _profile_error_key(str(message))
        if operation is AuxiliaryOperation.PROFILE
        else _update_error_key(str(message))
    )
    return auxiliary_text(normalized_language, key)


__all__ = (
    "TRANSLATIONS",
    "AuxiliaryOperation",
    "AuxiliaryText",
    "auxiliary_text",
    "localized_operation_error",
)
