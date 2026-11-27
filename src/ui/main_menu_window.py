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
        self.resize(1180, 850)
        self.setMinimumSize(940, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
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
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        logo = QLabel("S")
        logo.setObjectName("brandMark")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(66, 66)
        layout.addWidget(logo)

        identity = QVBoxLayout()
        identity.setSpacing(3)
        title = QLabel("SectorFlow Overley")
        title.setObjectName("mainTitle")
        subtitle = QLabel("🏁  ATIVE, DESATIVE E PERSONALIZE OS OVERLAYS  ·  RACE TELEMETRY")
        subtitle.setObjectName("subtitle")
        identity.addWidget(title)
        identity.addWidget(subtitle)
        layout.addLayout(identity, 1)

        header_config = self._load_header_config()
        update_box = QFrame()
        update_box.setObjectName("headerInfoBox")
        update_layout = QVBoxLayout(update_box)
        update_layout.setContentsMargins(13, 9, 13, 9)
        update_layout.setSpacing(6)
        self.version_label = QLabel(f"●  {tr('Versão')} {header_config['version']}")
        self.version_label.setProperty("sectorflowVersion", header_config["version"])
        self.version_label.setObjectName("versionLabel")
        notes_button = QPushButton("▤  Notas da versão")
        notes_button.setObjectName("updateNotesButton")
        notes_button.clicked.connect(lambda: self._open_update_notes(header_config))
        update_layout.addWidget(self.version_label)
        update_layout.addWidget(notes_button)
        layout.addWidget(update_box)

        donation_box = QFrame()
        donation_box.setObjectName("headerInfoBox")
        donation_layout = QVBoxLayout(donation_box)
        donation_layout.setContentsMargins(13, 9, 13, 9)
        donation_layout.setSpacing(6)
        donation_title = QLabel("♥  " + header_config["donation_label"])
        donation_title.setObjectName("donationLabel")
        donation_button = QPushButton("♥  Doações")
        donation_button.setObjectName("donationButton")
        donation_button.clicked.connect(lambda: self._open_donation(header_config))
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
        """Painel 2x2 por categoria; IDs, sinais e callbacks permanecem intactos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("overlayScroll")
        content = QWidget()
        sections_layout = QGridLayout(content)
        sections_layout.setContentsMargins(10, 10, 10, 10)
        sections_layout.setHorizontalSpacing(14)
        sections_layout.setVerticalSpacing(14)
        sections_layout.setColumnStretch(0, 1)
        sections_layout.setColumnStretch(1, 1)

        configs = self.overlay_manager.config_data.setdefault("widgets", {})
        grouped: dict[str, list] = {}
        for definition in WIDGET_DEFINITIONS:
            grouped.setdefault(definition.category, []).append(definition)

        category_details = {
            "Corrida": ("🏁", "Informações da corrida"),
            "Carro": ("🚘", "Dados e condição do veículo"),
            "Estratégia": ("◈", "Planejamento e estratégia"),
            "Sistema": ("⌁", "Conexões e informações"),
        }
        category_order = ["Corrida", "Carro", "Estratégia", "Sistema"]
        ordered = [name for name in category_order if name in grouped]
        ordered.extend(name for name in grouped if name not in ordered)

        for category_index, category in enumerate(ordered):
            section = QFrame()
            section.setObjectName("categorySection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(12, 10, 12, 12)
            section_layout.setSpacing(8)
            icon, description = category_details.get(category, ("◆", ""))
            heading_row = QHBoxLayout()
            heading_row.setSpacing(10)
            icon_label = QLabel(icon)
            icon_label.setObjectName("categoryIcon")
            heading_row.addWidget(icon_label)
            heading_text = QVBoxLayout()
            heading_text.setSpacing(0)
            heading = QLabel(tr(category))
            heading.setObjectName("categoryTitle")
            caption = QLabel(tr(description) if description else "")
            caption.setObjectName("categorySubtitle")
            heading_text.addWidget(heading)
            heading_text.addWidget(caption)
            heading_row.addLayout(heading_text, 1)
            section_layout.addLayout(heading_row)
            accent = QFrame()
            accent.setObjectName("categoryAccent")
            accent.setFixedHeight(3)
            section_layout.addWidget(accent)

            for definition in grouped[category]:
                enabled = bool(configs.get(definition.widget_id, {}).get("enabled", False))
                row = MenuRow(definition.widget_id, definition.title, enabled, definition.editable, definition.implemented)
                row.setProperty("sectorflowTitle", definition.title)
                row.toggled.connect(self._toggle_widget)
                row.edit_requested.connect(self._open_editor)
                section_layout.addWidget(row)
                self.rows[definition.widget_id] = row
            sections_layout.addWidget(section, category_index // 2, category_index % 2)
        sections_layout.setRowStretch(2, 1)
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
            QMainWindow, QWidget { background: #050D1A; color: #EAF4FF; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
            QFrame#headerBox { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #06172D,stop:0.52 #09264A,stop:1 #03101F); border: 1px solid #1268B5; border-radius: 15px; }
            QLabel#brandMark { color: #F4FBFF; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #27C8FF,stop:0.48 #0874E8,stop:1 #073B91); border: 2px solid #79DFFF; border-radius: 15px; font-size: 43px; font-weight: 900; }
            QFrame#toolbarBox, QFrame#footerBox { background: #0A192B; border: 1px solid #14518A; border-radius: 13px; }
            QFrame#headerInfoBox { background: #071A30; border: 1px solid #1769AA; border-radius: 11px; }
            QFrame#toolbarDivider { background: #153B60; border: none; max-height: 1px; }
            QLabel#mainTitle { color: #F5FAFF; font-size: 30px; font-weight: 850; }
            QLabel#subtitle { color: #83C9F4; font-size: 11px; font-weight: 700; }
            QLabel#versionLabel { color: #67D8FF; font-size: 12px; font-weight: 800; }
            QLabel#donationLabel { color: #FFD0E0; font-size: 11px; font-weight: 750; }
            QLabel#toolbarFieldLabel { color: #9CCDF2; font-size: 12px; font-weight: 700; }
            QLabel#updateDialogTitle { color: #70D8F5; font-size: 20px; font-weight: 700; }
            QLabel#updateDialogNote { color: #D7E0EC; font-size: 13px; padding: 10px; }
            QLabel#donationDialogTitle { color: #F1C56B; font-size: 18px; font-weight: 700; }
            QLabel#pixQrCode { background: #102945; border: 2px solid #20A9F0; border-radius: 12px; padding: 14px; }
            QLabel#pixKeyLabel { color: #D7E0EC; font-family: Consolas, monospace; font-size: 12px; }
            QTabWidget::pane { background: #061426; border: 1px solid #14518A; border-radius: 11px; top: -1px; }
            QTabBar::tab { background: #0B2037; color: #9BC8EA; border: 1px solid #174D7A; border-bottom: none; padding: 10px 20px; margin-right: 5px; border-top-left-radius: 9px; border-top-right-radius: 9px; font-weight: 750; }
            QTabBar::tab:hover { background: #10345A; color: #FFFFFF; }
            QTabBar::tab:selected { background: #0756A2; color: #FFFFFF; border-color: #22AFFF; }
            QFrame#categorySection { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0A1C31,stop:1 #071426); border: 1px solid #1266A8; border-radius: 14px; }
            QFrame#categorySection:hover { border-color: #20AFFF; }
            QLabel#categoryIcon { color: #54CFFF; font-size: 25px; font-weight: 800; min-width: 34px; }
            QLabel#categoryTitle { color: #F3F9FF; font-size: 17px; font-weight: 850; }
            QLabel#categorySubtitle { color: #83B7DD; font-size: 10px; font-style: italic; }
            QFrame#categoryAccent { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0875D1,stop:0.72 #11B9FF,stop:1 rgba(17,185,255,0)); border: none; border-radius: 1px; }
            QFrame#menuRow { background: #0D2035; border: 1px solid #173E62; border-radius: 9px; }
            QFrame#menuRow:hover { background: #102A46; border-color: #218BD0; }
            QLabel#rowIcon { color: #83D8FF; font-size: 17px; min-width: 24px; max-width: 24px; }
            QLabel#rowTitle { color: #EDF7FF; font-size: 13px; font-weight: 750; }
            QLabel#rowStatus { color: #FF8D9A; background: #301B2A; border: 1px solid #6C2A42; border-radius: 9px; padding: 4px 8px; font-size: 10px; font-weight: 800; }
            QLabel#rowStatus[active="true"] { color: #55F0A2; background: #0B382D; border-color: #087B54; }
            QPushButton { background: #10375C; color: #ECF8FF; border: 1px solid #1767A5; border-radius: 8px; padding: 8px 12px; min-height: 18px; font-weight: 700; }
            QPushButton:hover { background: #14558A; border-color: #27B5FF; }
            QPushButton:pressed { background: #08294A; }
            QPushButton:disabled { background: #142235; color: #607A93; border-color: #263B52; }
            QPushButton#toolbarActionButton { background: #0D3155; border-color: #1767A5; }
            QPushButton#toolbarActionButton:hover { background: #12518A; }
            QPushButton#deleteProfileButton { color: #FFB1B8; background: #321D2A; border-color: #713447; }
            QPushButton#deleteProfileButton:hover { background: #512638; }
            QPushButton#editModeButton { color: #B8DDF8; background: #102A45; border-color: #1D6AA7; }
            QPushButton#editModeButton:checked { color: #8CFFD0; background: #0A4938; border-color: #19B77B; }
            QPushButton#saveLayoutButton { color: #FFFFFF; background: #087B59; border-color: #1DD69A; }
            QPushButton#saveLayoutButton:hover { background: #09966A; }
            QPushButton#rowEditButton { color: #FFFFFF; background: #07549A; border-color: #168FDF; padding-left: 13px; padding-right: 13px; }
            QPushButton#rowEditButton:hover { background: #0875C9; border-color: #55C7FF; }
            QPushButton#updateNotesButton { color: #FFFFFF; background: #075A9F; border-color: #1C9EE8; }
            QPushButton#donationButton { color: #FFFFFF; background: #6336C5; border-color: #9D70FF; }
            QPushButton#donationButton:hover { background: #794BE0; }
            QPushButton#paypalButton { background: #086CA7; border-color: #2496CF; }
            QPushButton#communityLinkButton { color: #A9DFFF; background: #0C2C4A; border-color: #1B5B8B; padding: 5px 10px; min-height: 18px; font-size: 11px; }
            QComboBox { color: #E8F5FF; background: #10263E; border: 1px solid #1C5688; border-radius: 8px; padding: 7px 10px; min-width: 118px; min-height: 20px; selection-background-color: #0879C7; }
            QComboBox:hover { border-color: #2BAFFF; background: #123252; }
            QComboBox:focus { border-color: #39C1FF; }
            QComboBox::drop-down { width: 26px; border: none; }
            QComboBox QAbstractItemView { color: #E8F0FA; background: #10263E; border: 1px solid #2585C4; selection-background-color: #075F9E; selection-color: #FFFFFF; padding: 4px; outline: none; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 42px; height: 22px; }
            QCheckBox::indicator:unchecked { image: none; background: #34465C; border: 1px solid #58718D; border-radius: 11px; }
            QCheckBox::indicator:checked { image: none; background: #0BAA70; border: 1px solid #43F0B1; border-radius: 11px; }
            QCheckBox::indicator:disabled { background: #222E3D; border-color: #303F52; }
            QLabel#connectionLabel { color: #F0B95D; font-weight: 800; }
            QLabel#connectionLabel[connected="true"] { color: #39E99B; }
            QLabel#connectionLabel[connected="false"] { color: #FF7E8B; }
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { background: #071426; width: 10px; margin: 3px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #17649A; min-height: 28px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #20AFFF; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QToolTip { color: #F3F7FC; background: #10263E; border: 1px solid #2585C4; padding: 5px 8px; }
            """
        )
