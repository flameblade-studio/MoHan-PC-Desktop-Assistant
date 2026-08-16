from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol

lazy from domain.language_support import canonical_ui_language
lazy from domain.theme_pack import (
    DEFAULT_TOKENS,
    ThemePack,
    apply_theme,
    inspect_theme_pack,
    install_theme_pack,
    list_installed_themes,
    materialize_theme_background,
    remove_theme_pack,
    restore_builtin_theme,
)
lazy from domain.theme_session import BUILTIN_THEME_ID, ThemeResolution

__all__ = (
    "InstalledTheme",
    "ThemeGenerationPort",
    "ThemeGenerationRequest",
    "ThemeGenerationUnavailable",
    "ThemePackService",
)


_BUILTIN_NAMES = frozendict(
    {
        "zh-TW": "墨寒藍銀主題",
        "zh-CN": "墨寒蓝银主题",
        "en": "MoHan Blue-Silver",
        "ja-JP": "墨寒ブルーシルバー",
    }
)


@dataclass(frozen=True, slots=True)
class InstalledTheme:
    theme_id: str
    display_names: frozendict[str, str]
    built_in: bool = False
    source_channel: str = "user-authored"

    def display_name(self, language: str) -> str:
        canonical = canonical_ui_language(language)
        return str(
            self.display_names.get(canonical)
            or self.display_names.get("en")
            or self.theme_id
        )


@dataclass(frozen=True, slots=True)
class ThemeGenerationRequest:
    """Future-facing, provider-neutral request for one quarantined draft."""

    creative_direction: str
    language: str


class ThemeGenerationPort(Protocol):
    """Optional provider boundary; current public builds inject no provider."""

    def generate_draft(
        self,
        request: ThemeGenerationRequest,
        destination: Path,
    ) -> Path:
        raise NotImplementedError


class ThemeGenerationUnavailable(RuntimeError):
    pass


class ThemePackService:
    """One application boundary for validated dashboard theme packages."""

    def __init__(
        self,
        store: Path,
        *,
        generation_provider: ThemeGenerationPort | None = None,
    ) -> None:
        self.store = Path(store)
        self._generation_provider = generation_provider

    @property
    def autonomous_generation_available(self) -> bool:
        return self._generation_provider is not None

    def generate_quarantined_draft(
        self,
        request: ThemeGenerationRequest,
        destination: Path,
    ) -> ThemePack:
        """Generate but never install or activate a future provider draft."""

        if self._generation_provider is None:
            raise ThemeGenerationUnavailable(
                "Autonomous theme generation is not enabled."
            )
        generated = self._generation_provider.generate_draft(
            request,
            Path(destination),
        )
        theme = inspect_theme_pack(generated)
        if theme.source_channel != "mohan-generated":
            raise ThemeGenerationUnavailable(
                "Generated theme provenance is invalid."
            )
        return theme

    def themes(self) -> tuple[InstalledTheme, ...]:
        built_in = InstalledTheme(
            BUILTIN_THEME_ID,
            _BUILTIN_NAMES,
            True,
            "flameblade-official",
        )
        installed = tuple(
            InstalledTheme(
                theme.theme_id,
                theme.display_names,
                False,
                theme.source_channel,
            )
            for theme in list_installed_themes(self.store)
        )
        return (built_in, *installed)

    def install(self, source: Path) -> ThemePack:
        return install_theme_pack(Path(source), self.store)

    def remove(self, theme_id: str) -> None:
        remove_theme_pack(theme_id, self.store)

    def resolve(self, theme_id: str) -> ThemeResolution:
        requested = str(theme_id).strip() or BUILTIN_THEME_ID
        if requested == BUILTIN_THEME_ID:
            return ThemeResolution(
                requested,
                BUILTIN_THEME_ID,
                self._builtin_theme(),
                "ready",
            )
        for theme in list_installed_themes(self.store):
            if theme.theme_id == requested:
                return ThemeResolution(requested, requested, theme, "ready")
        return ThemeResolution(
            requested,
            BUILTIN_THEME_ID,
            self._builtin_theme(),
            "missing",
        )

    def activate(self, theme_id: str) -> ThemePack:
        if theme_id == BUILTIN_THEME_ID:
            restore_builtin_theme(self.store)
            return self._builtin_theme()
        return apply_theme(theme_id, self.store)

    def background_path(self, theme_id: str) -> Path | None:
        if theme_id == BUILTIN_THEME_ID:
            return None
        return materialize_theme_background(theme_id, self.store)

    @staticmethod
    def _builtin_theme() -> ThemePack:
        return ThemePack(
            BUILTIN_THEME_ID,
            _BUILTIN_NAMES,
            DEFAULT_TOKENS,
            "Microsoft JhengHei UI",
            10,
            None,
            "flameblade-official",
            "original",
            "Flameblade Studio",
            "MIT",
        )
