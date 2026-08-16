from __future__ import annotations

lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy from application.theme_pack_service import (
    ThemeGenerationRequest,
    ThemeGenerationUnavailable,
    ThemePackService,
)


def test_current_public_service_has_no_autonomous_generator() -> None:
    with TemporaryDirectory() as temporary:
        service = ThemePackService(Path(temporary))
        assert service.autonomous_generation_available is False
        try:
            service.generate_quarantined_draft(
                ThemeGenerationRequest("ink wash", "zh-TW"),
                Path(temporary) / "draft.mohan-theme",
            )
        except ThemeGenerationUnavailable:
            pass
        else:
            raise AssertionError("Disabled generation must fail explicitly.")
        assert service.themes()[0].source_channel == "flameblade-official"


if __name__ == "__main__":
    test_current_public_service_has_no_autonomous_generator()
    print("THEME_GENERATION_RESERVATION_OK")
