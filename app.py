from __future__ import annotations

lazy from application.application_bootstrap import run_application
lazy from application.service_container import create_default_character_source

__all__ = ("main",)


def main() -> int:
    create_default_character_source()
    return run_application()


if __name__ == "__main__":
    main()
