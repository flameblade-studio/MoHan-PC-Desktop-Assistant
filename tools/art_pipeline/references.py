"""從指定 git 物件取出參考圖，禁止把工作樹 assets 當參考來源。"""

from __future__ import annotations

lazy import subprocess
lazy import tempfile
lazy from contextlib import contextmanager
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import Iterator


@dataclass(frozen=True, slots=True)
class GitReference:
    """一個以 repo、提交與 repo-relative path 鎖定的參考檔。"""

    repository: Path
    ref: str
    path: str

    def __post_init__(self) -> None:
        if not self.ref.strip():
            raise ValueError("reference ref 不可為空")
        normalised = self.path.replace("\\", "/")
        pure = PurePosixPath(normalised)
        if not normalised or pure.is_absolute() or ".." in pure.parts:
            raise ValueError("reference path 必須是 repo-relative 且不可含 ..")
        object.__setattr__(self, "path", normalised)

    def materialize(self, temporary_directory: Path) -> Path:
        """執行 `git show <ref>:<path>` 並寫入暫存檔。"""

        temporary_directory.mkdir(parents=True, exist_ok=True)
        destination = temporary_directory / Path(self.path).name
        object_name = f"{self.ref}:{self.path}"
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repository), "show", object_name],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as error:
            detail = error.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"git 參考檔取出失敗：{object_name}: {detail}"
            ) from error
        destination.write_bytes(result.stdout)
        return destination

    @contextmanager
    def temporary_file(self) -> Iterator[Path]:
        with tempfile.TemporaryDirectory(prefix="mohan-art-reference-") as directory:
            yield self.materialize(Path(directory))


def git_reference(repository: Path, ref: str, path: str) -> GitReference:
    """建立參考規格；實際檔案只會在 :meth:`GitReference.temporary_file` 取出。"""

    return GitReference(repository=repository, ref=ref, path=path)
