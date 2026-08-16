from __future__ import annotations

lazy import re
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_HEADINGS = ("繁體中文", "简体中文", "English", "日本語")
MOJIBAKE_MARKERS = ("\ufffd", "Ã", "Â", "銝", "隞", "撠", "雿", "蝟", "摰")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def language_sections(text: str) -> dict[str, str]:
    matches = tuple(
        re.finditer(r"(?m)^## (繁體中文|简体中文|English|日本語)\s*$", text)
    )
    assert tuple(match.group(1) for match in matches) == LANGUAGE_HEADINGS
    return {
        match.group(1): text[
            match.end() : matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        ]
        for index, match in enumerate(matches)
    }


def assert_four_language_vision_contract(relative: str) -> None:
    text = read(relative)
    assert not any(marker in text for marker in MOJIBAKE_MARKERS)
    sections = language_sections(text)
    required = {
        "繁體中文": (
            "預設關閉",
            "明確啟用",
            "持續授權",
            "主動關閉",
            "不會逐幀詢問",
            "授權狀態",
            "立即撤銷",
            "低頻或事件觸發",
            "不儲存",
            "Base64",
            "不自行開啟網路",
            "成本上限",
            "取消",
            "不影響",
        ),
        "简体中文": (
            "默认关闭",
            "全局保存",
            "持续授权",
            "主动关闭",
            "不会逐帧询问",
            "授权状态",
            "立即撤销",
            "低频或事件触发",
            "不保存",
            "Base64",
            "不会自行开启网络",
            "成本上限",
            "取消",
            "不影响",
        ),
        "English": (
            "off by default",
            "globally saving",
            "continuous authorization",
            "turns it off",
            "does not ask for consent frame by frame",
            "authorization status",
            "immediate revocation",
            "low frequency or on an event trigger",
            "not retain",
            "Base64",
            "does not enable network",
            "cost limits",
            "cancel",
            "without harming",
        ),
        "日本語": (
            "既定で無効",
            "全体設定を保存",
            "継続的な許可",
            "自ら無効",
            "フレームごとに許可を求めることはありません",
            "許可状態",
            "直ちに取り消",
            "低頻度またはイベント発生時",
            "保存",
            "Base64",
            "自らネットワークを有効",
            "費用の上限",
            "取り消",
            "影響しません",
        ),
    }
    failures: list[str] = []
    for language, phrases in required.items():
        missing = tuple(phrase for phrase in phrases if phrase not in sections[language])
        if missing:
            failures.append(f"{language} missing {missing}")
        failures.extend(
            f"{language} missing {product}"
            for product in ("OpenCV", "GPT-5.6")
            if product not in sections[language]
        )
    assert not failures, f"{relative}: {'; '.join(failures)}"


def dependency_version(requirements: str, name: str) -> str | None:
    match = re.search(rf"(?mi)^{re.escape(name)}==([^\s;]+)$", requirements)
    return match.group(1) if match else None


def sbom_components() -> dict[str, dict[str, object]]:
    document = tomllib.loads(read("sbom/components.toml"))
    return {
        str(component["name"]).casefold(): component
        for component in document.get("component", [])
    }


def sbom_external_services() -> dict[str, dict[str, object]]:
    document = tomllib.loads(read("sbom/components.toml"))
    return {
        str(service["name"]).casefold(): service
        for service in document.get("external_service", [])
    }


def test_v4_vision_documentation_contract() -> None:
    for relative in (
        "README.md",
        "ARCHITECTURE.md",
        "docs/releases/v4.0.0-draft.md",
    ):
        assert_four_language_vision_contract(relative)


def test_vision_runtime_inventory_is_evidence_based() -> None:
    pyproject = tomllib.loads(read("pyproject.toml"))
    project_dependencies = "\n".join(pyproject["project"]["dependencies"])
    runtime_requirements = read("requirements-runtime.txt")
    components = sbom_components()
    external_services = sbom_external_services()

    opencv_version = dependency_version(runtime_requirements, "opencv-python")
    assert opencv_version == dependency_version(project_dependencies, "opencv-python")
    assert components["opencv-python"]["version"] == opencv_version
    assert components["opencv-python"]["license"] == "Apache-2.0"

    openai_version = dependency_version(runtime_requirements, "openai")
    assert openai_version == dependency_version(project_dependencies, "openai")
    assert openai_version is None
    assert "openai" not in components

    service = external_services["openai responses api"]
    assert service["endpoint"] == "https://api.openai.com/v1/responses"
    assert service["transport"] == "Python standard library urllib.request over HTTPS"
    assert service["sdk_package"] == "openai"
    assert service["sdk_runtime_dependency"] is False
    assert service["inventory_policy"] == "external-service-not-packaged"

    provider = read("integrations/openai_vision_provider.py")
    for contract in (
        "urllib.request import Request, urlopen",
        '"https://api.openai.com/v1/responses"',
        "store=False",
    ):
        assert contract in provider


def run() -> None:
    test_v4_vision_documentation_contract()
    test_vision_runtime_inventory_is_evidence_based()
    print("V4_VISION_DOCUMENTATION_OK")


if __name__ == "__main__":
    run()
