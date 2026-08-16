"""Compatibility facade for the domain command parser."""

from __future__ import annotations

from domain.command_parser import is_start_work_command, is_stop_work_command

__all__ = ("is_start_work_command", "is_stop_work_command")
