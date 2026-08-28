from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.app_profile import persona_for_profile
lazy from infrastructure.db import StudioDB
lazy from integrations.ai_client import PERSONA

LEGACY_PERSONA = (
    "你是墨寒。你稱使用者為主上。"
    "你是炎劍文化工作室的虛擬執行長、文膽與策士。"
    "請以炎劍文化工作室首席文膽與策士的身份工作。"
)


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        db = StudioDB(Path(temp_dir) / "mohan.db")
        fresh = persona_for_profile(db)
        assert "炎劍文化工作室" not in fresh
        assert "使用者身邊的虛擬執行長" in fresh

        db.set_setting("assistant_name", "霜月")
        db.set_setting("user_title", "老師")
        db.set_setting("organization_name", "星河研究室")
        personalized = persona_for_profile(db)
        assert "霜月" in personalized
        assert "老師" in personalized
        assert "星河研究室" in personalized
        assert "炎劍文化工作室" not in personalized

        db.set_setting("organization_name", "")
        db.set_setting("persona_prompt", LEGACY_PERSONA)
        neutralized = persona_for_profile(db)
        assert "炎劍文化工作室" not in neutralized
        assert "使用者身邊的虛擬執行長" in neutralized
        assert "首席文膽與策士" in neutralized

        db.set_setting("organization_name", "炎劍文化工作室")
        retained = persona_for_profile(db)
        assert "炎劍文化工作室" in retained
        db.close()

    assert "炎劍文化工作室" not in PERSONA
    print("PUBLIC_PROFILE_PERSONA_OK")


if __name__ == "__main__":
    run()
