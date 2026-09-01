from __future__ import annotations

lazy import ctypes
lazy import os
lazy from ctypes import wintypes
lazy from pathlib import Path

lazy from domain.contracts import SecretStoreFactoryPort, SecretStorePort
lazy from infrastructure.platform_contracts import PlatformServicePort


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, object]:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


class SecretStore:
    """Store secrets encrypted for the current Windows user with DPAPI."""

    def __init__(
        self,
        path: Path,
        description: str = "MoHan OpenAI API key",
    ):
        self.path = path
        self.description = description

    def save(self, value: str) -> None:
        if not value:
            self.clear()
            return
        if os.name != "nt":
            raise OSError("安全金鑰保存僅支援 Windows")
        source, source_buffer = _blob(value.encode("utf-8"))
        output = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(source),
            self.description,
            None,
            None,
            None,
            0,
            ctypes.byref(output),
        )
        _ = source_buffer
        if not ok:
            raise ctypes.WinError()
        try:
            encrypted = ctypes.string_at(output.pbData, output.cbData)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # 原子寫入。先前直接覆寫正式檔案，斷電或磁碟寫入失敗會留下
            # 截斷的 DPAPI blob；下一次 load() 解密失敗回傳空字串，而空字串
            # 與「尚未設定」無法區分——臉部 identity 會被當成零個 profile、
            # 手勢模板被當成空字典，接著新增一筆就把殘骸覆寫成新的真相。
            # 憑證、生物特徵與模板就這樣靜靜消失。
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with open(temporary, "wb") as handle:
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    def load(self) -> str:
        if not self.path.exists():
            return ""
        if os.name != "nt":
            return ""
        source, source_buffer = _blob(self.path.read_bytes())
        output = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(output),
        )
        _ = source_buffer
        if not ok:
            return ""
        try:
            return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class UnavailableSecretStore:
    """Non-persistent store used until a native secure adapter is verified."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason

    def save(self, value: str) -> None:
        if value:
            raise OSError(self.reason)
        self.clear()

    def load(self) -> str:
        return ""

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class PlatformSecretStoreFactory:
    """Create only the secure store verified for the active platform.

    Unsupported platforms receive a fail-closed store.  Keeping this choice in
    one injectable factory prevents individual features from silently falling
    back to plaintext or constructing a Windows-only DPAPI store themselves.
    """

    def __init__(self, platform_services: PlatformServicePort):
        self.platform_services = platform_services

    def __call__(
        self,
        path: Path,
        description: str = "MoHan protected secret",
    ) -> SecretStorePort:
        capabilities = self.platform_services.capabilities
        if capabilities.secure_secret_storage:
            return SecretStore(path, description)
        reason = (
            f"{capabilities.display_name} 的原生安全金鑰保存"
            "尚未完成實機驗證；墨寒不會退回明文保存。"
        )
        return UnavailableSecretStore(path.with_suffix(".unavailable"), reason)


def platform_secret_store_factory(
    platform_services: PlatformServicePort,
) -> SecretStoreFactoryPort:
    """Return the platform's single injectable secret-store boundary."""

    return PlatformSecretStoreFactory(platform_services)
