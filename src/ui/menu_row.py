from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
)
from src.i18n import tr


class MenuRow(QFrame):
    toggled = Signal(str, bool)
    edit_requested = Signal(str)

    def __init__(
        self,
        widget_id: str,
        title: str,
        enabled: bool,
        editable: bool,
        implemented: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.widget_id = widget_id
        self.setObjectName("menuRow")
        self.setMinimumHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 9, 6)
        layout.setSpacing(9)

        icon_map = {
            "standings": "🏆", "delta": "Δ", "driver_panel": "◉",
            "fuel_time": "⛽", "tires": "⚙", "url": "↗",
            "flags": "⚑", "relative": "⌖", "map": "▧",
            "battery": "▣", "lap_timer": "◷", "damage": "⚠",
            "weather": "☁", "radar": "◎",
        }
        self.icon_label = QLabel(icon_map.get(widget_id, "◆"))
        self.icon_label.setObjectName("rowIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("rowTitle")

        self.status_label = QLabel()
        self.status_label.setObjectName("rowStatus")

        self.toggle = QCheckBox()
        self.toggle.setChecked(enabled)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setToolTip("Ativar ou desativar este overlay")
        self.toggle.setAccessibleName(f"Ativar ou desativar {title}")
        self.toggle.toggled.connect(
            lambda value: self.toggled.emit(self.widget_id, value)
        )

        # Sempre guarde o texto-base. O tradutor de runtime aplica o idioma
        # quando a linha aparece e consegue retornar ao português depois.
        self.edit_button = QPushButton("Editar")
        self.edit_button.setObjectName("rowEditButton")
        self.edit_button.setMinimumWidth(78)
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_button.setToolTip("Personalizar este overlay")
        self.edit_button.setAccessibleName(f"Editar {title}")
        self.edit_button.setEnabled(editable and implemented)
        self.edit_button.clicked.connect(
            lambda: self.edit_requested.emit(self.widget_id)
        )

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle)
        layout.addWidget(self.edit_button)

        self._apply_implemented_state(implemented)
        self._apply_enabled_status(enabled)

    def set_enabled_state(self, enabled: bool) -> None:
        self.toggle.blockSignals(True)
        self.toggle.setChecked(enabled)
        self.toggle.blockSignals(False)
        self._apply_enabled_status(enabled)

    def _apply_enabled_status(self, enabled: bool) -> None:
        self.status_label.setText(tr("Ativo") if enabled else tr("Desativado"))
        self.status_label.setProperty("active", bool(enabled))
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _apply_implemented_state(self, implemented: bool) -> None:
        if not implemented:
            self.toggle.setEnabled(False)
