from __future__ import annotations

lazy from application.presentation_ports import (
    PlatformCapabilities,
    female_windows_voices_for_language,
    preferred_windows_voice,
)

__all__ = ("DashboardVoiceCatalogMethods",)


class DashboardVoiceCatalogMethods:
    def _available_windows_voices(
        self,
        capabilities: PlatformCapabilities,
    ) -> tuple[tuple[str, str], ...]:
        if not capabilities.system_local_speech:
            return ()
        return tuple(
            female_windows_voices_for_language(
                self.voice_catalog.windows_voices(),
                self.ui_language,
            )
        )

    def _preferred_windows_voice(
        self,
        available: tuple[tuple[str, str], ...],
        saved_voice: str,
    ) -> tuple[str, bool]:
        yating_available = any(
            "yating" in name.lower() and culture.lower() == "zh-tw"
            for name, culture in available
        )
        force_default = (
            self.ui_language.lower() in {"zh", "zh-tw"}
            and yating_available
            and not bool(
                self.db.setting(
                    "onecore_yating_v181_migrated",
                    False,
                )
            )
        )
        preferred = preferred_windows_voice(
            available,
            "" if force_default else saved_voice,
            self.ui_language,
        )
        return preferred, force_default

    @staticmethod
    def _windows_voice_label(name: str, culture: str) -> str:
        source = "OneCore" if name.startswith("OneCore::") else "Desktop SAPI"
        short_name = next(
            (
                keyword
                for keyword in ("Yating", "Hanhan")
                if keyword.lower() in name.lower()
            ),
            name,
        )
        return f"{short_name}（{culture}，{source}）"
