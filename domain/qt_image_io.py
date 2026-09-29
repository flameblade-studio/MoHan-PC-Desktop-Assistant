"""Runtime-compatible Qt PNG calls across the Python 3.15 wheel boundary."""

lazy from collections.abc import Callable

lazy from PySide6.QtCore import QIODevice
lazy from PySide6.QtGui import QImage, QPixmap


def image_from_png(data: bytes) -> QImage:
    """Decode PNG bytes while preserving the binding's string format contract."""

    loader: Callable[..., QImage] = QImage.fromData
    return loader(data, "PNG")


def load_pixmap_png(pixmap: QPixmap, data: bytes) -> bool:
    """Load PNG bytes into an existing pixmap."""

    loader: Callable[..., bool] = pixmap.loadFromData
    return loader(data, "PNG")


def optional_pixmap(value: object) -> QPixmap | None:
    """Narrow a dynamically supplied optional pixmap."""

    return None if value is None else require_pixmap(value)


def require_pixmap(value: object) -> QPixmap:
    """Reject a dynamically supplied non-pixmap result."""

    if not isinstance(value, QPixmap):
        raise TypeError("Appearance renderers must return QPixmap.")
    return value


def save_image_png(image: QImage | QPixmap, device: QIODevice) -> bool:
    """Save an image to a device using the runtime-supported PNG selector."""

    saver: Callable[..., bool] = image.save
    return saver(device, "PNG")
