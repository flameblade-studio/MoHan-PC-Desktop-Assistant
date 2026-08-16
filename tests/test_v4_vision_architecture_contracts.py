from __future__ import annotations

lazy import ast
lazy import inspect
lazy import json
lazy import sys
lazy import tomllib
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from cloud_scene_interpreter import CloudSceneInterpreter
lazy from cloud_vision_runtime import (
    CloudVisionFrame,
    CloudVisionRuntime,
    CloudVisionStatus,
    SavedVisionAuthorization,
)
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
)
lazy from integrations.openai_vision_provider import (
    VisionDetail,
    VisionFrameRequest,
    VisionProviderResult,
    VisionResultStatus,
    create_openai_vision_provider,
)
lazy from openai_vision_preferences import (
    PREFERENCES_VERSION,
    OpenAIVisionPreferences,
)
lazy from presentation.flagship_ui_localization import (
    FLAGSHIP_TRANSLATIONS,
    FlagshipTranslator,
)
lazy from visual_perception import LocalVisualAnalyzer, PresenceState

LOCAL_CORE_MODULES = (
    "vision_domain",
    "visual_perception",
    "local_visual_intelligence",
)
VISION_CONTRACT_MODULES = (
    *LOCAL_CORE_MODULES,
    "cloud_scene_interpreter",
    "cloud_vision_runtime",
    "openai_vision_authorization",
    "openai_vision_preferences",
    "openai_vision_preferences_store",
    "openai_vision_provider",
)
STATIC_SOURCE_PATHS = {
    "vision_domain": "domain/vision_domain.py",
    "visual_perception": "application/visual_perception.py",
    "local_visual_intelligence": "application/local_visual_intelligence.py",
    "cloud_scene_interpreter": "domain/cloud_scene_interpreter.py",
    "cloud_vision_runtime": "application/cloud_vision_runtime.py",
    "openai_vision_authorization": "domain/openai_vision_authorization.py",
    "openai_vision_preferences": "domain/openai_vision_preferences.py",
    "openai_vision_preferences_store": (
        "infrastructure/openai_vision_preferences_store.py"
    ),
    "openai_vision_provider": "integrations/openai_vision_provider.py",
}
FORBIDDEN_LOCAL_ROOTS = frozenset({
    "PySide6",
    "ai_client",
    "db",
    "http",
    "logging",
    "openai",
    "requests",
    "socket",
    "sqlite3",
    "urllib",
    "websocket",
})
FORBIDDEN_CLOUD_CONTROL_ROOTS = frozenset({
    "action_planner",
    "ai_client",
    "computer_tools",
    "speech",
    "speech_providers",
})
SENSITIVE_NAMES = frozenset({
    "api_key",
    "authorization",
    "authorization_header",
    "base64",
    "encoded",
    "image_bytes",
    "key",
})
PERSISTENCE_OR_LOG_CALLS = frozenset({
    "add",
    "debug",
    "error",
    "exception",
    "execute",
    "executemany",
    "info",
    "insert",
    "log",
    "print",
    "save",
    "update",
    "warning",
    "write",
    "write_bytes",
    "write_text",
})


def source(module: str) -> str:
    return (ROOT / STATIC_SOURCE_PATHS[module]).read_text(encoding="utf-8")


def tree(module: str) -> ast.Module:
    return ast.parse(source(module), filename=STATIC_SOURCE_PATHS[module])


def imported_roots(module: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree(module)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.partition(".")[0])
    return roots


def call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def names_in(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def string_constants(syntax: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(syntax)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_local_visual_core_has_no_cloud_ui_db_or_network_dependency() -> None:
    local_modules = {path.stem for path in ROOT.glob("*.py")}
    graph = {
        module: imported_roots(module) & local_modules
        for module in LOCAL_CORE_MODULES
    }
    pending = list(LOCAL_CORE_MODULES)
    visited: set[str] = set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        imports = imported_roots(module)
        forbidden = imports & FORBIDDEN_LOCAL_ROOTS
        assert not forbidden, f"{module} imports forbidden local-core dependency: {forbidden}"
        pending.extend(graph.get(module, ()))


def test_cloud_interpreter_cannot_identify_speak_or_execute_actions() -> None:
    assert not (
        imported_roots("cloud_scene_interpreter") & FORBIDDEN_CLOUD_CONTROL_ROOTS
    )
    syntax = tree("cloud_scene_interpreter")
    forbidden_calls = {
        call_name(node)
        for node in ast.walk(syntax)
        if isinstance(node, ast.Call)
        and call_name(node) in {"act", "execute", "perform", "speak"}
    }
    assert not forbidden_calls

    empty = CloudSceneInterpreter().interpret(None)
    assert empty.increment.identity.state.value == "unknown"
    assert all(
        not hasattr(candidate, attribute)
        for candidate in empty.interaction_candidates
        for attribute in ("action", "speak")
    )


def test_stdlib_https_transport_is_private_and_non_persistent() -> None:
    for module in VISION_CONTRACT_MODULES:
        syntax = tree(module)
        assert not imported_roots(module) & {"db", "logging", "sqlite3"}
        for node in ast.walk(syntax):
            if not isinstance(node, ast.Call) or call_name(node) not in PERSISTENCE_OR_LOG_CALLS:
                continue
            arguments = (*node.args, *(keyword.value for keyword in node.keywords))
            leaked = set().union(*(names_in(argument) for argument in arguments))
            assert not leaked & SENSITIVE_NAMES, (
                f"{module}:{node.lineno} sends sensitive vision data to "
                f"{call_name(node)}"
            )

    frame_field = CloudVisionFrame.__dataclass_fields__["image_bytes"]
    assert frame_field.repr is False
    provider_tree = tree("openai_vision_provider")
    imports = imported_roots("openai_vision_provider")
    responses_endpoint = "https://api.openai.com/v1/responses"
    endpoints = {
        value
        for value in string_constants(provider_tree)
        if value == responses_endpoint
    }
    failures: list[str] = []
    if "urllib" not in imports:
        failures.append("stdlib urllib transport missing")
    if "importlib" in imports or "openai" in imports:
        failures.append("dynamic OpenAI SDK loading remains")
    if endpoints != {responses_endpoint}:
        failures.append(f"Responses HTTPS endpoint mismatch: {sorted(endpoints)}")
    if "Authorization" not in string_constants(provider_tree):
        failures.append("Authorization header construction missing")
    assert not failures, "; ".join(failures)


def test_http_errors_are_sanitized_without_secret_echo() -> None:
    provider_tree = tree("openai_vision_provider")
    for node in ast.walk(provider_tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        leaked = names_in(node.exc) & SENSITIVE_NAMES
        assert not leaked, (
            f"integrations.openai_vision_provider.py:{node.lineno} raises sensitive HTTP data: "
            f"{sorted(leaked)}"
        )

    secret_key = "test-secret-key-never-log"
    secret_error = "test-secret-error-never-log"
    captured: list[object] = []

    def fail_network(request: object, **_options: object) -> object:
        captured.append(request)
        raise URLError(secret_error)

    service = create_openai_vision_provider(
        secret_key,
        model_selector=lambda: "gpt-5.6-luna",
    )
    request = VisionFrameRequest(
        91,
        b"ephemeral-frame",
        2,
        2,
        "image/jpeg",
        "Describe visible context.",
    )
    with patch("integrations.openai_vision_provider.urlopen", side_effect=fail_network):
        result = service.analyze(request)
    assert result.status is VisionResultStatus.NETWORK_UNAVAILABLE
    assert secret_key not in repr(result)
    assert secret_error not in repr(result)
    assert len(captured) == 1
    http_request = captured[0]
    assert http_request.full_url == "https://api.openai.com/v1/responses"
    assert http_request.get_header("Authorization") == f"Bearer {secret_key}"
    payload = json.loads(http_request.data.decode("utf-8"))
    assert payload["store"] is False

    authentication_error = HTTPError(
        "https://api.openai.com/v1/responses",
        401,
        secret_error,
        None,
        None,
    )
    service = create_openai_vision_provider(
        secret_key,
        model_selector=lambda: "gpt-5.6-luna",
    )
    with patch("integrations.openai_vision_provider.urlopen", side_effect=authentication_error):
        result = service.analyze(request)
    assert result.status is VisionResultStatus.AUTHENTICATION_FAILED
    assert secret_key not in repr(result)
    assert secret_error not in repr(result)


def test_http_transport_adds_no_openai_or_jiter_dependency() -> None:
    requirements = {
        *(
            line.partition("==")[0].strip().casefold()
            for line in (ROOT / filename).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        for filename in ("requirements.txt", "requirements-runtime.txt")
    }
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = {
        dependency.partition("==")[0].strip().casefold()
        for dependency in project["project"]["dependencies"]
    }
    forbidden = {"openai", "jiter"}
    assert not requirements & forbidden
    assert not project_dependencies & forbidden


class MemorySettings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def read(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return self.read(keys)

    def write(self, values: dict[str, object]) -> None:
        self.values.update(values)

    def restore(self, snapshot: dict[str, object]) -> None:
        self.values = dict(snapshot)


def test_continuous_authorization_is_saved_opt_in_and_revocable() -> None:
    signature = inspect.signature(OpenAIVisionPreferences.permits_cloud_frame)
    assert "explicit_consent" not in signature.parameters, (
        "continuous authorization must not retain a per-frame consent parameter"
    )

    settings = MemorySettings()
    store = OpenAIVisionPreferencesStore(settings)
    enabled = OpenAIVisionPreferences(enabled=True, cloud_vision_enabled=True)
    store.save(enabled)
    assert store.load() == enabled
    store.save(OpenAIVisionPreferences())
    assert store.load().enabled is False
    assert store.load().cloud_vision_enabled is False


@dataclass
class AuthorizationSource:
    authorization: SavedVisionAuthorization

    def load(self) -> SavedVisionAuthorization:
        return self.authorization


class Provider:
    def __init__(self, status: VisionResultStatus) -> None:
        self.status = status
        self.requests = 0

    def analyze(self, request: object) -> VisionProviderResult:
        self.requests += 1
        return VisionProviderResult(
            request.operation_id,
            self.status,
            request.model or "",
            VisionDetail.AUTO,
        )

    def cancel(self, _operation_id: int) -> None:
        return


def test_cloud_failures_never_block_the_local_path() -> None:
    local = LocalVisualAnalyzer(motion_threshold=1.0)
    local.analyze((10, 10, 10, 10), observed_at=0.0)
    authorization = SavedVisionAuthorization(
        OpenAIVisionPreferences(enabled=True, cloud_vision_enabled=True),
        PREFERENCES_VERSION,
        1,
        True,
    )
    expected = {
        VisionResultStatus.KEY_MISSING: CloudVisionStatus.KEY_MISSING,
        VisionResultStatus.NETWORK_UNAVAILABLE: CloudVisionStatus.NETWORK_UNAVAILABLE,
        VisionResultStatus.AUTHENTICATION_FAILED: CloudVisionStatus.KEY_MISSING,
        VisionResultStatus.RATE_LIMITED: CloudVisionStatus.PROVIDER_RATE_LIMITED,
        VisionResultStatus.TIMED_OUT: CloudVisionStatus.TIMED_OUT,
        VisionResultStatus.SERVICE_UNAVAILABLE: CloudVisionStatus.SERVICE_UNAVAILABLE,
    }
    for operation_id, (provider_status, runtime_status) in enumerate(
        expected.items(), start=1
    ):
        runtime = CloudVisionRuntime(Provider(provider_status), AuthorizationSource(authorization))
        result = runtime.analyze(
            CloudVisionFrame(
                operation_id,
                b"ephemeral",
                2,
                2,
                "image/jpeg",
                "Describe visible context.",
            )
        )
        assert result.status is runtime_status
        observation = local.analyze((20, 20, 20, 20), observed_at=float(operation_id))
        assert observation.presence is PresenceState.PRESENT


def test_four_language_continuous_authorization_keys_are_complete() -> None:
    required_sources = (
        "公開版預設關閉。明確啟用並全域保存後即持續授權，直到你主動關閉；系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。本機 OpenCV 不受此設定影響。",
        "允許雲端視覺持續運作",
        "明確啟用並全域保存後，雲端視覺會依所選事件與用量限制持續運作，直到你主動關閉；系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。原始影像不保存，也不會自動上網。",
        "立即關閉雲端視覺",
        "● 雲端視覺持續授權中",
    )
    for source_text in required_sources:
        translations = FLAGSHIP_TRANSLATIONS[source_text]
        assert len(translations) == 3
        assert all(value.strip() for value in translations)

    retired_consent_markers = (
        "每次送出單幀前仍須明確同意",
        "仍須逐次同意",
        "Every frame still requires explicit consent",
        "consent required each time",
        "各フレームの送信には明示的な同意",
        "毎回の同意が必要",
        "不要求逐幀或每次確認",
        "不要求逐帧或每次确认",
        "no per-frame or per-request confirmation",
        "フレームごとまたは要求ごとの確認",
    )
    all_text = "\n".join(
        text
        for source_text, translations in FLAGSHIP_TRANSLATIONS.items()
        for text in (source_text, *translations)
    )
    retired_found = tuple(
        marker for marker in retired_consent_markers if marker in all_text
    )
    assert not retired_found, f"retired per-frame consent text remains: {retired_found}"

    for language in ("zh-TW", "zh-CN", "en-US", "ja-JP"):
        localizer = FlagshipTranslator(language)
        assert localizer.text("允許雲端視覺持續運作").strip()

    legacy_summary = (
        "公開版預設關閉。每次送出單幀前仍須明確同意；"
        "本機 OpenCV 不受此設定影響。"
    )
    for language in ("zh-TW", "zh-CN", "en-US", "ja-JP"):
        rendered = FlagshipTranslator(language).text(legacy_summary)
        assert not any(marker in rendered for marker in retired_consent_markers)


def test_python315_lazy_import_and_zen_contracts_do_not_regress() -> None:
    for module in VISION_CONTRACT_MODULES:
        syntax = tree(module)
        for node in syntax.body:
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                assert getattr(node, "is_lazy", 0), f"{module}:{node.lineno} is eager"
                assert not any(alias.name == "*" for alias in node.names)
        for node in ast.walk(syntax):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                assert not (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "object"
                ), f"{module}:{node.lineno} uses a legacy object sentinel"


def run() -> None:
    checks = (
        test_local_visual_core_has_no_cloud_ui_db_or_network_dependency,
        test_cloud_interpreter_cannot_identify_speak_or_execute_actions,
        test_stdlib_https_transport_is_private_and_non_persistent,
        test_http_errors_are_sanitized_without_secret_echo,
        test_http_transport_adds_no_openai_or_jiter_dependency,
        test_continuous_authorization_is_saved_opt_in_and_revocable,
        test_cloud_failures_never_block_the_local_path,
        test_four_language_continuous_authorization_keys_are_complete,
        test_python315_lazy_import_and_zen_contracts_do_not_regress,
    )
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except AssertionError as error:
            detail = str(error).strip() or "assertion failed"
            failures.append(f"{check.__name__}: {detail}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("V4_VISION_ARCHITECTURE_CONTRACTS_OK")


if __name__ == "__main__":
    run()
