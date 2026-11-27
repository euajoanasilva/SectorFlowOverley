from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.menu_row import MenuRow
from src.ui.widget_registry import WIDGET_DEFINITIONS
from src.i18n import LANGUAGES, app_language, set_app_language, tr
from src.widget.delta.delta_editor import DeltaEditor
from src.widget.driver_panel.driver_panel_editor import DriverPanelEditor
from src.widget.flags.flags_editor import FlagsEditor
from src.widget.tyres.tyres_editor import TyresEditor
from src.widget.weather.weather_editor import WeatherEditor
from src.widget.battery.battery_editor import BatteryEditor
from src.widget.damage.damage_editor import DamageEditor
from src.widget.relative.relative_editor import RelativeEditor
from src.widget.map.map_editor import MapEditor
from src.widget.standings.standings_editor import StandingsEditor
from src.widget.fuel_time.fuel_time_editor import FuelTimeEditor
from src.widget.lap_timer.lap_timer_editor import LapTimerEditor
from src.widget.url.url_editor import UrlEditor
from src.widget.radar.radar_editor import RadarEditor
from src.laps.archive import LapRecorder
from src.ui.lap_archive_page import LapArchivePage


class MainMenuWindow(QMainWindow):
    DISCORD_URL = "https://discord.gg/pVShUkfbtN"
    RELEASES_URL = "https://github.com/RomarioSantos-Oficial/SectorFlowOverley/releases"

    def __init__(self, overlay_manager, edit_mode_manager, parent=None) -> None:
        super().__init__(parent)
        self.overlay_manager = overlay_manager
        self.edit_mode_manager = edit_mode_manager
        self.rows: dict[str, MenuRow] = {}
        self.editors: dict[str, QWidget] = {}
        self._lmu_connected = False
        self._lmu_status_text = "conexão"

        self.setWindowTitle("SectorFlow Overley")
        self.resize(920, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        root.addWidget(self._build_header())
        root.addWidget(self._build_toolbar())
        self.content_tabs = QTabWidget()
        self.content_tabs.addTab(self._build_widget_grid(), tr("Overlays"))
        self.lap_archive_page = LapArchivePage(self)
        self.content_tabs.addTab(self.lap_archive_page, tr("Voltas"))
        self.lap_recorder = LapRecorder(self.lap_archive_page.store)
        self.lap_recorder.set_owner_key(self.lap_archive_page.owner_key)
        root.addWidget(self.content_tabs, 1)
        root.addWidget(self._build_footer())
        self._apply_style()
        self.overlay_manager.profile_changed.connect(self._profile_applied)

    def _build_header(self) -> QWidget:
        box = QFrame()
        box.setObjectName("headerBox")
        layout = QHBoxLayout(box)
        identity = QVBoxLayout()
        title = QLabel("SectorFlow Overley")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Ative, desative e personalize os overlays.")
        subtitle.setObjectName("subtitle")
        identity.addWidget(title)
        identity.addWidget(subtitle)
        layout.addLayout(identity, 1)

        header_config = self._load_header_config()
        update_box = QFrame()
        update_box.setObjectName("headerInfoBox")
        update_layout = QVBoxLayout(update_box)
        update_layout.setContentsMargins(12, 8, 12, 8)
        self.version_label = QLabel(f"{tr('Versão')} {header_config['version']}")
        self.version_label.setProperty("sectorflowVersion", header_config["version"])
        self.version_label.setObjectName("versionLabel")
        notes_button = QPushButton("Notas da versão")
        notes_button.setObjectName("updateNotesButton")
        notes_button.clicked.connect(
            lambda: self._open_update_notes(header_config)
        )
        update_layout.addWidget(self.version_label)
        update_layout.addWidget(notes_button)
        layout.addWidget(update_box, 1)

        donation_box = QFrame()
        donation_box.setObjectName("headerInfoBox")
        donation_layout = QVBoxLayout(donation_box)
        donation_layout.setContentsMargins(12, 8, 12, 8)
        donation_title = QLabel(header_config["donation_label"])
        donation_title.setObjectName("donationLabel")
        donation_button = QPushButton("Doações")
        donation_button.setObjectName("donationButton")
        donation_button.clicked.connect(
            lambda: self._open_donation(header_config)
        )
        donation_layout.addWidget(donation_title)
        donation_layout.addWidget(donation_button)
        layout.addWidget(donation_box)
        return box

    @staticmethod
    def _load_header_config() -> dict[str, str]:
        defaults = {
            "version": "1.1",
            "update_note": "Novidades e correções da versão atual.",
            "update_note_key": "",
            "update_note_addendum": "",
            "update_note_addendum_key": "",
            "update_note_fix": "",
            "update_note_fix_key": "",
            "donation_label": "Apoie o desenvolvimento",
            "donation_url": "",
            "pix_key": "",
            "pix_qr_image": "images/pix/qrcode-pix.png",
        }
        path = Path(__file__).resolve().parents[1] / "config" / "menu_header.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return defaults
        return {
            key: str(data.get(key, value) or value)
            for key, value in defaults.items()
        }

    def _open_donation(self, config: dict[str, str]) -> None:
        pix_key = config.get("pix_key", "").strip()
        donation_url = config.get("donation_url", "").strip()
        dialog = QDialog(self)
        dialog.setWindowTitle("Doações")
        dialog.setMinimumWidth(380)
        layout = QVBoxLayout(dialog)

        title = QLabel("Apoie o desenvolvimento do SectorFlow Overley")
        title.setObjectName("donationDialogTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        qr_relative = config.get("pix_qr_image", "").strip()
        qr_path = Path(__file__).resolve().parents[2] / qr_relative
        if qr_relative and qr_path.is_file():
            pixmap = QPixmap(str(qr_path))
            if not pixmap.isNull():
                qr_label = QLabel()
                qr_label.setObjectName("pixQrCode")
                qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qr_label.setPixmap(
                    pixmap.scaled(
                        260,
                        260,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                layout.addWidget(qr_label)

        if pix_key:
            key_label = QLabel(f"{tr('Chave PIX:')} {pix_key}")
            key_label.setObjectName("pixKeyLabel")
            key_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            key_label.setWordWrap(True)
            layout.addWidget(key_label)
            copy_pix = QPushButton("Copiar chave PIX")
            copy_pix.clicked.connect(
                lambda: self._copy_pix_key(pix_key, copy_pix)
            )
            layout.addWidget(copy_pix)

        if donation_url:
            paypal = QPushButton("Doar com PayPal")
            paypal.setObjectName("paypalButton")
            paypal.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(donation_url))
            )
            layout.addWidget(paypal)

        if not pix_key and not donation_url:
            layout.addWidget(QLabel("Destino de doação ainda não configurado."))

        close = QPushButton("Fechar")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def _open_update_notes(self, config: dict[str, str]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Notas da versão")
        dialog.setMinimumSize(480, 300)
        layout = QVBoxLayout(dialog)

        version = QLabel(f"SectorFlow Overley — {tr('Versão')} {config['version']}")
        version.setObjectName("updateDialogTitle")
        layout.addWidget(version)

        source_note = config.get("update_note", "").strip() or "Nenhuma nota cadastrada."
        translation_key = config.get("update_note_key", "").strip()
        translated_note = tr(translation_key) if translation_key else tr(source_note)
        if translation_key and translated_note == translation_key:
            translated_note = source_note
        addendum_source = config.get("update_note_addendum", "").strip()
        addendum_key = config.get("update_note_addendum_key", "").strip()
        translated_addendum = tr(addendum_key) if addendum_key else tr(addendum_source)
        if addendum_key and translated_addendum == addendum_key:
            translated_addendum = addendum_source
        if translated_addendum:
            translated_note = f"{translated_note}\n\n{translated_addendum}"
        fix_source = config.get("update_note_fix", "").strip()
        fix_key = config.get("update_note_fix_key", "").strip()
        translated_fix = tr(fix_key) if fix_key else tr(fix_source)
        if fix_key and translated_fix == fix_key:
            translated_fix = fix_source
        if translated_fix:
            translated_note = f"{translated_note}\n\n{translated_fix}"
        note = QLabel(translated_note)
        note.setObjectName("updateDialogNote")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(note, 1)

        close = QPushButton("Fechar")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    @staticmethod
    def _copy_pix_key(pix_key: str, button: QPushButton) -> None:
        QApplication.clipboard().setText(pix_key)
        button.setText(tr("Chave PIX copiada!"))

    def _build_toolbar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("toolbarBox")
        outer = QVBoxLayout(box)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(9)

        # Faixa principal: perfil e ações rápidas.
        primary = QHBoxLayout()
        primary.setSpacing(8)
        profile_label = QLabel("Perfil:")
        profile_label.setObjectName("toolbarFieldLabel")
        primary.addWidget(profile_label)

        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("profileCombo")
        self.profile_combo.setMinimumWidth(142)
        self._reload_profiles()
        self.profile_combo.currentIndexChanged.connect(self._switch_profile)
        primary.addWidget(self.profile_combo)

        add_profile = QPushButton("Novo perfil")
        add_profile.setObjectName("toolbarActionButton")
        add_profile.setMinimumWidth(92)
        add_profile.setCursor(Qt.CursorShape.PointingHandCursor)
        add_profile.clicked.connect(self._create_profile)
        primary.addWidget(add_profile)

        self.rename_profile_button = QPushButton("Renomear")
        self.rename_profile_button.setObjectName("toolbarActionButton")
        self.rename_profile_button.setMinimumWidth(82)
        self.rename_profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_profile_button.clicked.connect(self._rename_profile)
        primary.addWidget(self.rename_profile_button)

        self.delete_profile_button = QPushButton("Excluir")
        self.delete_profile_button.setObjectName("deleteProfileButton")
        self.delete_profile_button.setMinimumWidth(70)
        self.delete_profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_profile_button.clicked.connect(self._delete_profile)
        primary.addWidget(self.delete_profile_button)
        self._update_profile_buttons()

        primary.addStretch(1)

        self.edit_mode_button = QPushButton("Modo edição: DESLIGADO")
        self.edit_mode_button.setObjectName("editModeButton")
        self.edit_mode_button.setMinimumWidth(176)
        self.edit_mode_button.setCheckable(True)
        self.edit_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_mode_button.toggled.connect(self._set_edit_mode)
        primary.addWidget(self.edit_mode_button)

        save = QPushButton("Salvar layout")
        save.setObjectName("saveLayoutButton")
        save.setMinimumWidth(112)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.overlay_manager.save_config)
        primary.addWidget(save)
        outer.addLayout(primary)

        divider = QFrame()
        divider.setObjectName("toolbarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        outer.addWidget(divider)

        # Preferências em uma segunda faixa para evitar que os controles
        # fiquem espremidos em telas menores.
        preferences = QHBoxLayout()
        preferences.setSpacing(9)

        performance_label = QLabel("Desempenho:")
        performance_label.setObjectName("toolbarFieldLabel")
        preferences.addWidget(performance_label)
        self.performance_combo = QComboBox()
        self.performance_combo.setObjectName("performanceCombo")
        self.performance_combo.addItem("Padrão", "standard")
        self.performance_combo.addItem("Baixo consumo", "low")
        profile = str(
            self.overlay_manager.config_data.get("performance_profile", "standard")
        )
        self.performance_combo.setCurrentIndex(
            max(0, self.performance_combo.findData(profile))
        )
        self.performance_combo.setMinimumWidth(142)
        self.performance_combo.setToolTip(
            "Reduz a frequência de leitura e atualização dos overlays."
        )
        self.performance_combo.currentIndexChanged.connect(
            self._set_performance_profile
        )
        preferences.addWidget(self.performance_combo)

        preferences.addSpacing(14)
        language_label = QLabel("Idioma:")
        language_label.setObjectName("toolbarFieldLabel")
        preferences.addWidget(language_label)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("languageCombo")
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        current = self.language_combo.findData(app_language())
        self.language_combo.setCurrentIndex(max(0, current))
        self.language_combo.setMinimumWidth(126)
        self.language_combo.setToolTip("Idioma da interface")
        self.language_combo.currentIndexChanged.connect(self._change_language)
        preferences.addWidget(self.language_combo)
        preferences.addStretch(1)

        outer.addLayout(preferences)
        return box

    def _set_performance_profile(self, index: int) -> None:
        selected = str(self.performance_combo.itemData(index) or "standard")
        self.overlay_manager.config_data["performance_profile"] = selected
        self.overlay_manager.save_config()

    def _change_language(self, index: int) -> None:
        language = str(self.language_combo.itemData(index) or "pt_BR")
        set_app_language(language)
        self._refresh_dynamic_translations()

    def _refresh_dynamic_translations(self) -> None:
        """Reaplica textos que mudam depois que a janela foi traduzida."""
        version = str(self.version_label.property("sectorflowVersion") or "1.1")
        self.version_label.setText(f"{tr('Versão')} {version}")
        if hasattr(self, "discord_button"):
            self.discord_button.setToolTip(tr("Abrir servidor do Discord"))
        if hasattr(self, "releases_button"):
            self.releases_button.setText(tr("Atualizações"))
            self.releases_button.setToolTip(tr("Ver atualizações do SectorFlow"))
        if hasattr(self, "lap_archive_page"):
            self.lap_archive_page.retranslate()
        self._reload_profiles()
        self.edit_mode_button.setText(
            tr("Modo edição: LIGADO")
            if self.edit_mode_button.isChecked()
            else tr("Modo edição: DESLIGADO")
        )
        for row in self.rows.values():
            source_title = str(row.property("sectorflowTitle") or "")
            if source_title:
                row.title_label.setText(tr(source_title))
            row._apply_enabled_status(row.toggle.isChecked())
        self.set_lmu_status(self._lmu_connected, self._lmu_status_text)

    def _reload_profiles(self, selected_id: str | None = None) -> None:
        if not hasattr(self, "profile_combo"):
            return
        selected_id = selected_id or self.overlay_manager.active_profile_id
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected_index = 0
        for index, (profile_id, name) in enumerate(
            self.overlay_manager.profile_items()
        ):
            # Nomes criados pelo usuário não são traduzidos. Somente os dois
            # perfis internos possuem nomes localizáveis.
            display_name = tr(name) if profile_id in {"standard", "engineer"} else name
            self.profile_combo.addItem(display_name, profile_id)
            if profile_id == selected_id:
                selected_index = index
        self.profile_combo.setCurrentIndex(selected_index)
        self.profile_combo.blockSignals(False)

    def _switch_profile(self, index: int) -> None:
        profile_id = self.profile_combo.itemData(index)
        if profile_id:
            self.overlay_manager.switch_profile(str(profile_id))
        self._update_profile_buttons()

    def _create_profile(self) -> None:
        name, accepted = self._translated_text_dialog(
            "Novo perfil", "Nome do perfil personalizado:"
        )
        if not accepted or not name.strip():
            return
        try:
            profile_id = self.overlay_manager.create_profile(name)
            self._reload_profiles(profile_id)
            self.overlay_manager.switch_profile(profile_id)
        except Exception as exc:
            QMessageBox.critical(self, tr("Erro ao criar perfil"), str(exc))

    def _rename_profile(self) -> None:
        profile_id = str(self.profile_combo.currentData() or "")
        if profile_id in {"standard", "engineer"}:
            return
        current_name = self.profile_combo.currentText()
        name, accepted = self._translated_text_dialog(
            "Renomear perfil",
            "Novo nome do perfil:",
            current_name,
        )
        if not accepted or not name.strip():
            return
        try:
            self.overlay_manager.rename_profile(profile_id, name)
        except Exception as exc:
            QMessageBox.critical(self, tr("Erro ao renomear perfil"), str(exc))

    def _translated_text_dialog(
        self, title: str, label: str, value: str = ""
    ) -> tuple[str, bool]:
        dialog = QInputDialog(self)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setWindowTitle(tr(title))
        dialog.setLabelText(tr(label))
        dialog.setTextValue(value)
        dialog.setOkButtonText(tr("OK"))
        dialog.setCancelButtonText(tr("Cancelar"))
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog.textValue(), accepted

    def _delete_profile(self) -> None:
        profile_id = str(self.profile_combo.currentData() or "")
        if profile_id in {"standard", "engineer"}:
            return
        name = self.profile_combo.currentText()
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Question)
        message.setWindowTitle(tr("Excluir perfil"))
        message.setText(tr("Excluir permanentemente o perfil '{name}'?").format(name=name))
        message.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        message.setDefaultButton(QMessageBox.StandardButton.No)
        yes_button = message.button(QMessageBox.StandardButton.Yes)
        no_button = message.button(QMessageBox.StandardButton.No)
        if yes_button is not None:
            yes_button.setText(tr("Sim"))
        if no_button is not None:
            no_button.setText(tr("Não"))
        answer = QMessageBox.StandardButton(message.exec())
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.overlay_manager.delete_profile(profile_id)
        except Exception as exc:
            QMessageBox.critical(self, tr("Erro ao excluir perfil"), str(exc))

    def _update_profile_buttons(self) -> None:
        if not hasattr(self, "delete_profile_button"):
            return
        custom = str(self.profile_combo.currentData() or "") not in {
            "standard", "engineer", ""
        }
        self.rename_profile_button.setEnabled(custom)
        self.delete_profile_button.setEnabled(custom)

    def _profile_applied(self, profile_id: str) -> None:
        self._reload_profiles(profile_id)
        self._update_profile_buttons()
        configs = self.overlay_manager.config_data.get("widgets", {})
        for widget_id, row in self.rows.items():
            row.set_enabled_state(
                bool(configs.get(widget_id, {}).get("enabled", False))
            )

    def _build_widget_grid(self) -> QWidget:
        """Organiza os overlays por área sem alterar seus IDs ou sinais."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        sections_layout = QVBoxLayout(content)
        sections_layout.setContentsMargins(10, 12, 10, 12)
        sections_layout.setSpacing(16)

        configs = self.overlay_manager.config_data.setdefault("widgets", {})
        grouped: dict[str, list] = {}
        for definition in WIDGET_DEFINITIONS:
            grouped.setdefault(definition.category, []).append(definition)

        for category, definitions in grouped.items():
            section = QFrame()
            section.setObjectName("categorySection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(12, 10, 12, 12)
            section_layout.setSpacing(9)

            heading = QLabel(tr(category))
            heading.setObjectName("categoryTitle")
            section_layout.addWidget(heading)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(9)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)

            for index, definition in enumerate(definitions):
                enabled = bool(
                    configs.get(definition.widget_id, {}).get("enabled", False)
                )
                row = MenuRow(
                    definition.widget_id,
                    definition.title,
                    enabled,
                    definition.editable,
                    definition.implemented,
                )
                row.setProperty("sectorflowTitle", definition.title)
                row.toggled.connect(self._toggle_widget)
                row.edit_requested.connect(self._open_editor)
                grid.addWidget(row, index // 2, index % 2)
                self.rows[definition.widget_id] = row

            section_layout.addLayout(grid)
            sections_layout.addWidget(section)

        sections_layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_footer(self) -> QWidget:
        box = QFrame()
        box.setObjectName("footerBox")
        layout = QHBoxLayout(box)
        # Status do LMU seguido dos links e do atalho.
        self.discord_button = QPushButton("Discord")
        self.discord_button.setObjectName("communityLinkButton")
        self.discord_button.setToolTip(tr("Abrir servidor do Discord"))
        self.discord_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.DISCORD_URL))
        )
        self.releases_button = QPushButton(tr("Atualizações"))
        self.releases_button.setObjectName("communityLinkButton")
        self.releases_button.setToolTip(tr("Ver atualizações do SectorFlow"))
        self.releases_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.RELEASES_URL))
        )
        self.connection_label = QLabel("LMU: aguardando conexão")
        self.connection_label.setObjectName("connectionLabel")
        self.connection_label.setText(tr("LMU: Desconectado"))
        self.connection_label.setProperty("connected", False)
        layout.addWidget(self.connection_label)
        layout.addWidget(self.discord_button)
        layout.addWidget(self.releases_button)
        layout.addStretch()
        layout.addWidget(QLabel("F12 alterna o modo de edição"))
        return box

    def set_lmu_status(self, connected: bool, text: str = "") -> None:
        self._lmu_connected = bool(connected)
        self._lmu_status_text = text
        message = tr("LMU: Ativo") if connected else tr("LMU: Desconectado")
        if self.connection_label.text() != message:
            self.connection_label.setText(message)

        # Reaplicar todo o estilo 20 vezes por segundo é caro. O estilo só
        # precisa ser recalculado quando o estado da conexão realmente muda.
        previous = self.connection_label.property("connected")
        if previous != connected:
            self.connection_label.setProperty("connected", connected)
            self.connection_label.style().unpolish(self.connection_label)
            self.connection_label.style().polish(self.connection_label)

    def observe_lap_session(self, session) -> None:
        """Record valid laps even while the overlay windows are hidden."""
        saved = self.lap_recorder.observe(session)
        if saved:
            self.lap_archive_page.refresh_local_records()

    def finish_lap_recording(self) -> None:
        self.lap_recorder.finish_session()

    def _toggle_widget(self, widget_id: str, enabled: bool) -> None:
        widgets_config = self.overlay_manager.config_data.setdefault("widgets", {})
        previous_enabled = bool(
            widgets_config.get(widget_id, {}).get("enabled", False)
        )
        try:
            self.overlay_manager.set_widget_enabled(widget_id, enabled)
            self.rows[widget_id].set_enabled_state(enabled)
        except Exception as exc:
            # Em caso de falha, restaura o estado anterior em vez de forçar
            # o botão para desligado (o que poderia divergir da configuração).
            widgets_config.setdefault(widget_id, {})["enabled"] = previous_enabled
            self.rows[widget_id].set_enabled_state(previous_enabled)
            QMessageBox.critical(self, tr("Erro ao controlar widget"), str(exc))

    def _open_editor(self, widget_id: str) -> None:
        if widget_id == "driver_panel":
            editor = DriverPanelEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "delta":
            editor = DeltaEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "flags":
            editor = FlagsEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "tires":
            editor = TyresEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "weather":
            editor = WeatherEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "battery":
            editor = BatteryEditor(
                deepcopy(
                    self.overlay_manager.config_data["widgets"][widget_id]
                ),
                None,
            )
        elif widget_id == "damage":
            editor = DamageEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]),
                None,
            )
        elif widget_id == "fuel_time":
            editor = FuelTimeEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "lap_timer":
            editor = LapTimerEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "url":
            editor = UrlEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "relative":
            editor = RelativeEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]),
                None,
            )
        elif widget_id == "radar":
            editor = RadarEditor(
                deepcopy(self.overlay_manager.config_data["widgets"][widget_id]), None
            )
        elif widget_id == "map":
            editor = MapEditor(
                deepcopy(
                    self.overlay_manager.config_data["widgets"][widget_id]
                ),
                None,
            )
        elif widget_id == "standings":
            editor = StandingsEditor(
                deepcopy(
                    self.overlay_manager.config_data["widgets"][widget_id]
                ),
                None,
            )
        else:
            QMessageBox.information(
                self,
                tr("Editor ainda não criado"),
                tr("O editor de '{widget_id}' ainda não foi implementado.").format(
                    widget_id=widget_id
                ),
            )
            return

        editor.config_changed.connect(
            lambda config, current_id=widget_id: self.overlay_manager.update_widget_config(
                current_id, config
            )
        )
        if isinstance(editor, DriverPanelEditor):
            editor.geometry_changed.connect(
                self._update_driver_panel_geometry
            )
        editor.restore_requested.connect(
            lambda current_id=widget_id: self.overlay_manager.restore_widget_default(current_id)
        )
        editor.finished.connect(
            lambda _result, current_id=widget_id: self._editor_closed(
                current_id
            )
        )
        self.editors[widget_id] = editor
        self.hide()
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def _update_driver_panel_geometry(
        self,
        section: str,
        key: str,
        value,
    ) -> None:
        """Aplica somente o campo geométrico editado sobre o estado atual."""
        config = deepcopy(
            self.overlay_manager.config_data["widgets"]["driver_panel"]
        )
        if section:
            config.setdefault(section, {})[key] = value
        else:
            config[key] = value
        self.overlay_manager.update_widget_config(
            "driver_panel",
            config,
            preserve_geometry=False,
        )

    def _editor_closed(self, widget_id: str) -> None:
        self.editors.pop(widget_id, None)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if bool(getattr(self, "tray_mode_enabled", False)):
            event.ignore()
            self.hide()
            tray_icon = getattr(self, "tray_icon", None)
            if tray_icon is not None:
                tray_icon.showMessage(
                    "SectorFlow Overley",
                    tr("O programa continua na bandeja do Windows."),
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )
            return
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _set_edit_mode(self, enabled: bool) -> None:
        if self.edit_mode_manager is not None:
            self.edit_mode_manager.set_enabled(enabled)
        else:
            self.overlay_manager.set_edit_mode(enabled)
        self.edit_mode_button.setText(
            tr("Modo edição: LIGADO") if enabled else tr("Modo edição: DESLIGADO")
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0B111B;
                color: #E8EEF7;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }

            QFrame#headerBox {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #19283C, stop: 1 #101A29
                );
                border: 1px solid #2D405A;
                border-radius: 16px;
            }
            QFrame#toolbarBox, QFrame#footerBox {
                background: #121C2A;
                border: 1px solid #26374D;
                border-radius: 13px;
            }
            QFrame#headerInfoBox {
                background: #142238;
                border: 1px solid #30445F;
                border-radius: 11px;
            }
            QFrame#toolbarDivider {
                background: #29394D;
                border: none;
                max-height: 1px;
            }

            QLabel#mainTitle {
                color: #F7FAFF;
                font-size: 29px;
                font-weight: 750;
            }
            QLabel#subtitle {
                color: #A7B7CC;
                font-size: 13px;
            }
            QLabel#versionLabel {
                color: #70D8F5;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#donationLabel {
                color: #F1C56B;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#toolbarFieldLabel {
                color: #9FB0C5;
                font-size: 12px;
                font-weight: 650;
            }
            QLabel#updateDialogTitle {
                color: #70D8F5;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#updateDialogNote {
                color: #D7E0EC;
                font-size: 13px;
                padding: 10px;
            }
            QLabel#donationDialogTitle {
                color: #F1C56B;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#pixQrCode {
                background: #17263A;
                border: 2px solid #4CB8D8;
                border-radius: 12px;
                padding: 14px;
            }
            QLabel#pixKeyLabel {
                color: #D7E0EC;
                font-family: Consolas, monospace;
                font-size: 12px;
            }

            QTabWidget::pane {
                background: #0F1825;
                border: 1px solid #283A51;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: #141F2E;
                color: #9AACC2;
                border: 1px solid #293B52;
                border-bottom: none;
                padding: 10px 19px;
                margin-right: 5px;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                font-weight: 650;
            }
            QTabBar::tab:hover {
                background: #1B2A3E;
                color: #EAF2FC;
            }
            QTabBar::tab:selected {
                background: #1B2D45;
                color: #F7FAFF;
                border-color: #397FBD;
                border-bottom: 2px solid #58B9E8;
            }

            QFrame#categorySection {
                background: #101B29;
                border: 1px solid #263A51;
                border-radius: 13px;
            }
            QLabel#categoryTitle {
                color: #71C8F0;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 2px 4px 5px 4px;
            }

            QFrame#menuRow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #172435, stop: 1 #131F2E
                );
                border: 1px solid #2B3D54;
                border-radius: 12px;
            }
            QFrame#menuRow:hover {
                background: #1A2A3E;
                border: 1px solid #4A7195;
            }
            QLabel#rowTitle {
                color: #EDF4FD;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#rowStatus {
                color: #F08B91;
                background: #30232D;
                border: 1px solid #563743;
                border-radius: 9px;
                padding: 4px 9px;
                font-size: 10px;
                font-weight: 750;
            }
            QLabel#rowStatus[active="true"] {
                color: #67E2AE;
                background: #15382F;
                border-color: #28634F;
            }

            QPushButton {
                background: #223249;
                color: #E7EFF9;
                border: 1px solid #3A506D;
                border-radius: 8px;
                padding: 8px 12px;
                min-height: 18px;
                font-weight: 650;
            }
            QPushButton:hover {
                background: #2C4260;
                border-color: #56789F;
            }
            QPushButton:pressed {
                background: #1A2A3F;
                padding-top: 9px;
                padding-bottom: 7px;
            }
            QPushButton:disabled {
                background: #182333;
                color: #64748A;
                border-color: #29384B;
            }
            QPushButton#toolbarActionButton {
                background: #1B2A3E;
                border-color: #344B68;
            }
            QPushButton#toolbarActionButton:hover {
                background: #263C57;
                border-color: #4C7098;
            }
            QPushButton#deleteProfileButton {
                color: #F0A4A7;
                background: #30232D;
                border-color: #593744;
            }
            QPushButton#deleteProfileButton:hover {
                background: #482B36;
                border-color: #81505E;
            }
            QPushButton#editModeButton {
                color: #B8C8DA;
                background: #1B2B40;
                border-color: #3A526E;
            }
            QPushButton#editModeButton:checked {
                color: #8CF0C5;
                background: #164333;
                border-color: #2A8C68;
            }
            QPushButton#saveLayoutButton {
                color: #F2FBF7;
                background: #17664F;
                border-color: #2D9674;
            }
            QPushButton#saveLayoutButton:hover {
                background: #1C8061;
                border-color: #42B58D;
            }
            QPushButton#rowEditButton {
                color: #DFF2FF;
                background: #174B73;
                border-color: #2878AA;
                padding-left: 14px;
                padding-right: 14px;
            }
            QPushButton#rowEditButton:hover {
                background: #1D6596;
                border-color: #4BA4D4;
            }
            QPushButton#updateNotesButton {
                color: #F0FAFF;
                background: #155C91;
                border-color: #2C8AC4;
            }
            QPushButton#donationButton {
                color: #FBF5FF;
                background: #6741A5;
                border-color: #8D68C7;
            }
            QPushButton#donationButton:hover {
                background: #7951B8;
            }
            QPushButton#paypalButton {
                background: #086CA7;
                border-color: #2496CF;
            }
            QPushButton#communityLinkButton {
                color: #A9D7FF;
                background: #1A2A3E;
                border-color: #344B68;
                padding: 5px 10px;
                min-height: 18px;
                font-size: 11px;
            }

            QComboBox {
                color: #E8F0FA;
                background: #182639;
                border: 1px solid #344A65;
                border-radius: 8px;
                padding: 7px 10px;
                min-width: 118px;
                min-height: 20px;
                selection-background-color: #246BA4;
            }
            QComboBox:hover {
                border-color: #52769B;
                background: #1D3048;
            }
            QComboBox:focus {
                border-color: #4B9ED1;
            }
            QComboBox::drop-down {
                width: 26px;
                border: none;
            }
            QComboBox QAbstractItemView {
                color: #E8F0FA;
                background: #172538;
                border: 1px solid #3B526F;
                selection-background-color: #235F91;
                selection-color: #FFFFFF;
                padding: 4px;
                outline: none;
            }

            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 42px;
                height: 22px;
            }
            QCheckBox::indicator:unchecked {
                image: none;
                background: #3B485B;
                border: 1px solid #53647B;
                border-radius: 11px;
            }
            QCheckBox::indicator:checked {
                image: none;
                background: #16865D;
                border: 1px solid #36C28D;
                border-radius: 11px;
            }
            QCheckBox::indicator:disabled {
                background: #222E3D;
                border-color: #303F52;
            }

            QLabel#connectionLabel {
                color: #F0B95D;
                font-weight: 700;
            }
            QLabel#connectionLabel[connected="true"] {
                color: #57DCA4;
            }
            QLabel#connectionLabel[connected="false"] {
                color: #F07A82;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #101A28;
                width: 10px;
                margin: 3px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #3A526E;
                min-height: 28px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #54799D;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QToolTip {
                color: #F3F7FC;
                background: #172538;
                border: 1px solid #3B526F;
                padding: 5px 8px;
            }
            """
        )
