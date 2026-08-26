from __future__ import annotations

lazy from application.application_bootstrap import run_application

__all__ = ("main",)


def main() -> int:
    return run_application()


if __name__ == "__main__":
    main()
