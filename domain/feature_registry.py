from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass

lazy from PySide6.QtWidgets import QTabWidget, QWidget

FeatureFactory = Callable[[], QWidget]


@dataclass(frozen=True)
class DashboardFeature:
    feature_id: str
    title: str
    factory: FeatureFactory


class DashboardFeatureRegistry:
    """Explicit composition point for independently maintained feature tabs."""

    def __init__(self) -> None:
        self._features: list[DashboardFeature] = []
        self._ids: set[str] = set()

    def register(
        self,
        feature_id: str,
        title: str,
        factory: FeatureFactory,
    ) -> None:
        normalized = feature_id.strip().lower()
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("feature_id 必須是英數字與底線。")
        if normalized in self._ids:
            raise ValueError(f"功能模組重複註冊：{normalized}")
        if not title.strip() or not callable(factory):
            raise ValueError("功能模組必須提供標題與可呼叫的 UI 工廠。")
        self._ids.add(normalized)
        self._features.append(
            DashboardFeature(normalized, title.strip(), factory)
        )

    @property
    def features(self) -> tuple[DashboardFeature, ...]:
        return tuple(self._features)

    def mount(self, tabs: QTabWidget) -> None:
        for feature in self._features:
            widget = feature.factory()
            if not isinstance(widget, QWidget):
                raise TypeError(
                    f"{feature.feature_id} 沒有建立有效的 QWidget。"
                )
            widget.setProperty("mohanFeatureId", feature.feature_id)
            tabs.addTab(widget, feature.title)
