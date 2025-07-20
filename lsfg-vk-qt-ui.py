from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QComboBox,
    QMessageBox, QInputDialog, QSlider, QAbstractButton, QSizePolicy,
    QSpacerItem
)
from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Property, QTimer
from PySide6.QtGui import QPainter, QBrush, QFontMetrics, QPalette
import sys
import os
import toml

CONFIG_PATH = os.getenv("LSFG_CONFIG") or os.path.expanduser("~/.config/lsfg-vk/conf.toml")
DEFAULT_PROFILE_PATH = os.path.expanduser("~/.config/lsfg-vk-qt-ui/default.toml")
DEFAULT_PROFILE_NAME = "Default"

DISPLAY_NAMES_PATH = os.path.expanduser("~/.config/lsfg-vk-qt-ui/displaynames.toml")

def load_display_names():
    if os.path.exists(DISPLAY_NAMES_PATH):
        return toml.load(DISPLAY_NAMES_PATH)
    return {}

def save_display_names(display_names):
    os.makedirs(os.path.dirname(DISPLAY_NAMES_PATH), exist_ok=True)
    with open(DISPLAY_NAMES_PATH, "w") as f:
        toml.dump(display_names, f)

def ensure_config_exists():
    config_dir = os.path.dirname(CONFIG_PATH)
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(config_dir, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            f.write("version = 1\n")

    default_profile_data = {
        "exe": DEFAULT_PROFILE_NAME,
        "multiplier": 2,
        "flow_scale": 1.0,
        "performance_mode": False,
        "hdr_mode": False,
        "experimental_present_mode": "vsync",

    }

    if not os.path.exists(DEFAULT_PROFILE_PATH):
        os.makedirs(os.path.dirname(DEFAULT_PROFILE_PATH), exist_ok=True)
        with open(DEFAULT_PROFILE_PATH, "w") as f:
            toml.dump(default_profile_data, f)

from PySide6.QtWidgets import QDialog, QLineEdit, QLabel, QVBoxLayout, QDialogButtonBox

class ProfileInputDialog(QDialog):
    def __init__(self, display_name="", app_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Profile")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Profile Name (Optional):"))
        self.display_name_edit = QLineEdit(display_name)
        self.display_name_edit.setPlaceholderText("Defaults to app name")
        layout.addWidget(self.display_name_edit)

        layout.addWidget(QLabel("App:"))
        self.app_name_edit = QLineEdit(app_name)
        self.app_name_edit.setPlaceholderText("App to apply LSFG-VK to")
        layout.addWidget(self.app_name_edit)
        layout.addSpacing(10)

        self.list_apps_btn = QPushButton("Add a currently open app")
        layout.addWidget(self.list_apps_btn)

        layout.addSpacing(10)

        self.list_apps_btn.clicked.connect(self.list_open_apps)

        from PySide6.QtWidgets import QHBoxLayout

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(buttons)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        self.app_name_edit.setFocus()

    def get_inputs(self):
        return self.display_name_edit.text().strip(), self.app_name_edit.text().strip()

    def list_open_apps(self):
        import subprocess
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QMessageBox

        bash_script = """
        for pid in /proc/[0-9]*; do
            owner=$(stat -c %U "$pid" 2>/dev/null)
            if [[ "$owner" == "$USER" ]]; then
                if grep -qi 'vulkan' "$pid/maps" 2>/dev/null; then
                    procname=$(cat "$pid/comm" 2>/dev/null)
                    if [[ -n "$procname" ]]; then
                        printf "%s\\n" "$procname"
                    fi
                fi
            fi
        done | sort -u
        """

        try:
            result = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True, timeout=5)
            app_list = result.stdout.strip().splitlines()

            if not app_list:
                QMessageBox.information(self, "Info", "No Vulkan apps found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Select a Running App")
            layout = QVBoxLayout(dialog)

            list_widget = QListWidget()
            list_widget.addItems(app_list)
            layout.addWidget(list_widget)

            close_btn = QPushButton("Cancel")
            layout.addWidget(close_btn)
            close_btn.clicked.connect(dialog.reject)

            def on_item_clicked(item):
                app_name = item.text()
                self.app_name_edit.setText(app_name)
                QMessageBox.information(
                    self,
                    "Restart May Be Required",
                    f'A restart of "{app_name}" may be required before frame generation is applied.'
                )
                dialog.accept()

            list_widget.itemClicked.connect(on_item_clicked)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list apps:\n{e}")

class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None, width=50, height=25):
        super().__init__(parent)
        self.setCheckable(True)
        self._offset = 0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(120)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._w, self._h = width, height
        self.setFixedSize(self._w + 40, self._h)
        self.toggled.connect(self._animate)
        self._text_font = self.font()
        self._text_font.setBold(False)
        self._text_color = self.palette().color(self.foregroundRole())

    def _animate(self, checked):
        self._animation.stop()
        self._animation.setEndValue(self._w - self._h if checked else 0)
        self._animation.start()

    def get_offset(self): return self._offset
    def set_offset(self, val):
        self._offset = val
        self.update()
    offset = Property(int, get_offset, set_offset)

    def paintEvent(self, event):
        radius = self._h / 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pal = self.palette()

        bg_color = pal.color(QPalette.Highlight) if self.isChecked() else pal.color(QPalette.Mid)
        text = "On" if self.isChecked() else "Off"

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self._w, self._h, radius, radius)

        handle_radius = radius - 2
        painter.setBrush(QBrush(pal.color(QPalette.Base)))
        painter.drawEllipse(self._offset + 2, 2, handle_radius * 2, handle_radius * 2)

        painter.setFont(self._text_font)
        painter.setPen(self._text_color)
        fm = QFontMetrics(self._text_font)
        text_x = self._w + 10
        text_y = (self._h + fm.ascent() - fm.descent()) / 2
        painter.drawText(text_x, text_y, text)

class HoverSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self.show_hover_tooltip)
        self._tooltip_label = None

    def enterEvent(self, event):
        self._hover_timer.start(500)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_timer.stop()
        if self._tooltip_label:
            self._tooltip_label.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._hover_timer.stop()
        if self._tooltip_label:
            self._tooltip_label.show()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._tooltip_label:
            self._tooltip_label.hide()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._tooltip_label and self._tooltip_label.isVisible():
            val = self.value()
            self._tooltip_label.setText(f"{val / 100:.2f}")
            global_pos = self.mapToGlobal(event.position().toPoint())
            x = global_pos.x() - self._tooltip_label.width()
            y = global_pos.y() - 30
            self._tooltip_label.move(x, y)
            self._tooltip_label.adjustSize()
        super().mouseMoveEvent(event)

    def show_hover_tooltip(self):
        if self._tooltip_label:
            val = self.value()
            self._tooltip_label.setText(f"{val / 100:.2f}")
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            global_pos = self.mapToGlobal(cursor_pos)
            x = global_pos.x() - self._tooltip_label.width()
            y = global_pos.y() - 30
            self._tooltip_label.move(x, y)
            self._tooltip_label.adjustSize()
            self._tooltip_label.show()

class GameProfile:
    def __init__(self, exe="", multiplier="Off", flow_scale=1.0,
                 performance_mode=False, hdr_mode=False, exp_mode="vsync",
                 env=None, fps_limit=None):
        self.exe = exe
        self.multiplier = multiplier
        self.flow_scale = flow_scale
        self.performance_mode = performance_mode
        self.hdr_mode = hdr_mode
        self.experimental_present_mode = exp_mode
        self.env = env
        self.experimental_fps_limit = fps_limit

    @staticmethod
    def from_dict(d: dict) -> "GameProfile":
        multiplier = d.get("multiplier", 1)
        multiplier_label = f"X{multiplier}" if isinstance(multiplier, int) and multiplier > 1 else "Off"
        return GameProfile(
            exe=d.get("exe", ""),
            multiplier=multiplier_label,
            flow_scale=float(d.get("flow_scale", 1.0)),
            performance_mode=bool(d.get("performance_mode", False)),
            hdr_mode=bool(d.get("hdr_mode", False)),
            exp_mode=d.get("experimental_present_mode", "vsync"),
            env=d.get("env"),
            fps_limit=d.get("experimental_fps_limit")
        )

    def to_dict(self) -> dict:
        d = {"exe": self.exe}
        try:
            d["multiplier"] = int(self.multiplier[1:]) if self.multiplier != "Off" else 1
        except:
            d["multiplier"] = 1
        if self.flow_scale != 1.0:
            d["flow_scale"] = self.flow_scale
        if self.performance_mode:
            d["performance_mode"] = True
        if self.hdr_mode:
            d["hdr_mode"] = True
        if self.experimental_present_mode:
            d["experimental_present_mode"] = self.experimental_present_mode
        if self.env:
            d["env"] = self.env
        if self.experimental_fps_limit:
            d["experimental_fps_limit"] = self.experimental_fps_limit
        return d

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lossless Scaling Frame Generation")
        self.resize(900, 520)
        self.setFixedSize(self.size())
        self.profiles = []
        self.display_names = load_display_names()
        self.current_index = -1
        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.build_layout())
        self.load_profiles()

        self.display_names = {}
        display_path = os.path.expanduser("~/.config/lsfg-vk-qt-ui/displaynames.toml")
        if os.path.exists(display_path):
            try:
                self.display_names = toml.load(display_path)
            except Exception:
                self.display_names = {}

        default_index = next((i for i, p in enumerate(self.profiles) if p.exe == DEFAULT_PROFILE_NAME), -1)
        if default_index != -1:
            self.profile_list.setCurrentRow(default_index)
            self.current_index = default_index
            self.settings_panel.setEnabled(True)
            self.update_ui()
        else:
            self.current_index = -1
            self.settings_panel.setEnabled(False)
            self.clear_settings_panel()

    def load_profiles(self):
        self.profiles.clear()
        self.profile_list.clear()

        if os.path.exists(DEFAULT_PROFILE_PATH):
            try:
                default_data = toml.load(DEFAULT_PROFILE_PATH)
                default_profile = GameProfile.from_dict(default_data)
                default_profile.exe = DEFAULT_PROFILE_NAME
                self.profiles.append(default_profile)
                self.profile_list.addItem(DEFAULT_PROFILE_NAME)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load default profile:\n{e}")
        else:
            QMessageBox.warning(self, "Warning", "Default profile not found.")

        if os.path.exists(CONFIG_PATH):
            try:
                data = toml.load(CONFIG_PATH)
                game_entries = data.get("game", [])
                if isinstance(game_entries, dict):
                    game_entries = [game_entries]

                for entry in game_entries:
                    profile = GameProfile.from_dict(entry)
                    if profile.exe != DEFAULT_PROFILE_NAME:
                        self.profiles.append(profile)
                        display_name = self.display_names.get(profile.exe, profile.exe)
                        self.profile_list.addItem(display_name)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load config file:\n{e}")

    def save_profiles(self):
        try:

            data = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    data = toml.load(CONFIG_PATH)
                except Exception:
                    pass

            data["game"] = [p.to_dict() for p in self.profiles if p.exe != DEFAULT_PROFILE_NAME]

            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                toml.dump(data, f)

            default_profile = next((p for p in self.profiles if p.exe == DEFAULT_PROFILE_NAME), None)
            if default_profile:
                os.makedirs(os.path.dirname(DEFAULT_PROFILE_PATH), exist_ok=True)
                with open(DEFAULT_PROFILE_PATH, "w") as f:
                    toml.dump(default_profile.to_dict(), f)
                    valid_exes = {p.exe for p in self.profiles if p.exe != DEFAULT_PROFILE_NAME}
                    display_path = os.path.expanduser("~/.config/lsfg-vk-qt-ui/displaynames.toml")
                    try:
                        if os.path.exists(display_path):
                            current_names = toml.load(display_path)
                        else:
                            current_names = {}
                    except Exception:
                        current_names = {}

                    cleaned = {k: v for k, v in current_names.items() if k in valid_exes}

                    with open(display_path, "w") as f:
                        toml.dump(cleaned, f)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config:\n{e}")

    def build_layout(self):
        root = QVBoxLayout()
        header = QHBoxLayout()
        header.addStretch()
        label = QLabel('<a href="https://github.com/PancakeTAS/lsfg-vk">LSFG-VK</a>')
        label.setStyleSheet("padding: 1px 6px; font: bold 9pt;")
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        header.addWidget(label)
        root.addLayout(header)

        main = QHBoxLayout()
        main.addWidget(self.build_sidebar())
        self.settings_panel = self.build_settings()
        self.current_index = -1
        self.profile_name_label.setText("")
        self.settings_panel.setEnabled(False)
        main.addWidget(self.settings_panel)

        root.addLayout(main)
        return root

    def build_sidebar(self):
        layout = QVBoxLayout()
        title = QLabel("Game Profiles")
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(title)

        self.profile_list = QListWidget()
        self.profile_list.clicked.connect(self.profile_selected)
        layout.addWidget(self.profile_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        pal = self.palette()
        highlight = pal.color(QPalette.Highlight).name()
        highlight_text = pal.color(QPalette.HighlightedText).name()

        style = f"""
            QPushButton {{
                background-color: {highlight};
                color: {highlight_text};
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton::hover {{
                background-color: {highlight};
            }}
            QToolTip {{
                color: black;
                background-color:
                border: 1px solid gray;
                padding: 4px;
            }}
        """

        add_btn = QPushButton("+")
        add_btn.setFixedSize(110, 33)
        add_btn.setToolTip("Add profile")
        add_btn.setStyleSheet(style)
        add_btn.clicked.connect(self.create_profile)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(55, 33)
        edit_btn.setToolTip("Edit profile")
        edit_btn.setStyleSheet(style)
        edit_btn.clicked.connect(self.rename_profile)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(55, 33)
        delete_btn.setToolTip("Delete profile")
        delete_btn.setStyleSheet(style)
        delete_btn.clicked.connect(self.delete_profile)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setLayout(layout)
        return sidebar

    def build_settings(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        name_container = QWidget()
        name_container.setFixedHeight(48)
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)

        self.profile_name_label = QLabel()
        self.profile_name_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        name_layout.addWidget(self.profile_name_label)

        self.real_name_label = QLabel()
        self.real_name_label.setStyleSheet("font-size: 9pt; color: gray; margin-top: 0px;")
        name_layout.addWidget(self.real_name_label)

        layout.addWidget(name_container)

        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; font-size: 14pt; margin-top: 10px;")
            return lbl

        def labeled_widget(label, widget, bold=False):
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold; font-size: 11pt;" if bold else "font-size: 11pt;")
            h.addWidget(lbl)
            h.addWidget(widget)
            h.setAlignment(Qt.AlignTop)
            container = QWidget()
            container.setLayout(h)
            container.setContentsMargins(20, 0, 0, 0)
            return container

        layout.addWidget(section_label("Frame Generation"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Off", "X2", "X3", "X4", "X8"])
        self.mode_combo.setFixedSize(245, 52)
        self.mode_combo.currentTextChanged.connect(self.mode_changed)
        layout.addWidget(labeled_widget("Mode", self.mode_combo, True))

        self.flow_slider = HoverSlider(Qt.Horizontal)
        self.flow_slider.setRange(25, 100)
        self.flow_slider.setValue(100)
        self.flow_slider.setFixedHeight(28)

        pal = self.palette()
        light_color = pal.color(QPalette.Light).name()
        highlight_color = pal.color(QPalette.Highlight).name()
        base_color = pal.color(QPalette.Base).name()
        text_color = pal.color(QPalette.Text).name()

        self.flow_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                border-radius: 4px;
                background: {light_color};
            }}
            QSlider::handle:horizontal {{
                background: {highlight_color};
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            margin-left: 40px;
        """)

        self.flow_value_tooltip = QLabel(self)
        self.flow_value_tooltip.setStyleSheet(f"""
            background-color: {base_color};
            color: {text_color};
            border-radius: 5px;
            padding: 3px 7px;
            font-weight: bold;
        """)
        self.flow_value_tooltip.setWindowFlags(Qt.ToolTip)
        self.flow_value_tooltip.hide()

        self.flow_slider._tooltip_label = self.flow_value_tooltip

        flow_container = QWidget()
        flow_layout = QHBoxLayout(flow_container)
        flow_layout.setContentsMargins(23, 0, 0, 0)

        flow_label = QLabel("Flow scale")
        flow_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        flow_layout.addWidget(flow_label)
        flow_layout.addSpacerItem(QSpacerItem(237, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        flow_layout.addWidget(self.flow_slider)
        layout.addWidget(flow_container)

        self.flow_slider.valueChanged.connect(self.flow_slider_changed)

        self.perf_check = ToggleSwitch()
        self.perf_check.toggled.connect(self.performance_mode_changed)
        layout.addWidget(labeled_widget("Performance", self.perf_check, True))

        layout.addWidget(section_label("Rendering"))
        self.hdr_check = ToggleSwitch()
        self.hdr_check.toggled.connect(self.hdr_mode_changed)
        layout.addWidget(labeled_widget("HDR", self.hdr_check, True))

        self.present_combo = QComboBox()
        self.present_combo.addItems(["vsync", "immediate", "mailbox"])
        self.present_combo.setFixedSize(245, 52)
        self.present_combo.currentTextChanged.connect(self.present_mode_changed)
        layout.addWidget(labeled_widget("Sync mode", self.present_combo, True))

        panel = QWidget()
        panel.setLayout(layout)
        return panel

    def flow_slider_changed(self, value):
        if self.current_index != -1:
            self.profiles[self.current_index].flow_scale = value / 100.0
            self.save_profiles()

    def mode_changed(self, text):
        if self.current_index != -1:
            self.profiles[self.current_index].multiplier = text
            self.save_profiles()

    def performance_mode_changed(self, checked):
        if self.current_index != -1:
            self.profiles[self.current_index].performance_mode = checked
            self.save_profiles()

    def hdr_mode_changed(self, checked):
        if self.current_index != -1:
            self.profiles[self.current_index].hdr_mode = checked
            self.save_profiles()

    def present_mode_changed(self, text):
        if self.current_index != -1:
            self.profiles[self.current_index].experimental_present_mode = text
            self.save_profiles()

    def create_profile(self):
        default_app_name = ""
        default_display_name = ""

        dlg = ProfileInputDialog(display_name=default_display_name, app_name=default_app_name, parent=self)
        if dlg.exec() == QDialog.Accepted:
            display_name, app_name = dlg.get_inputs()

            if not app_name:
                QMessageBox.warning(self, "Error", "App Name cannot be empty.")
                return
            if app_name == DEFAULT_PROFILE_NAME or any(p.exe == app_name for p in self.profiles):
                QMessageBox.warning(self, "Error", "Profile already exists or name is reserved.")
                return

            if os.path.exists(DEFAULT_PROFILE_PATH):
                try:
                    default_data = toml.load(DEFAULT_PROFILE_PATH)
                    new_profile = GameProfile.from_dict(default_data)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to load Default profile:\n{e}")
                    new_profile = GameProfile()
            else:
                new_profile = GameProfile()

            new_profile.exe = app_name
            self.profiles.append(new_profile)

            self.display_names[app_name] = display_name if display_name else app_name
            save_display_names(self.display_names)

            self.display_names = load_display_names()

            self.profile_list.addItem(display_name if display_name else app_name)
            self.profile_list.setCurrentRow(len(self.profiles) - 1)
            self.current_index = len(self.profiles) - 1

            self.update_ui()
            self.save_profiles()

    def clear_settings_panel(self):
        self.profile_name_label.setText("")
        self.mode_combo.setCurrentIndex(0)
        self.present_combo.setCurrentIndex(0)
        self.perf_check.setChecked(False)
        self.hdr_check.setChecked(False)
        self.flow_slider.setValue(100)

    def rename_profile(self):
        row = self.profile_list.currentRow()
        if row == -1:
            return
        p = self.profiles[row]

        if p.exe == DEFAULT_PROFILE_NAME:
            QMessageBox.warning(self, "Error", "Cannot rename the Default profile.")
            return

        dlg = ProfileInputDialog(display_name=self.display_names.get(p.exe, ""), app_name=p.exe, parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_display_name, new_app_name = dlg.get_inputs()

            if not new_app_name:
                QMessageBox.warning(self, "Error", "App Name cannot be empty.")
                return
            if new_app_name == DEFAULT_PROFILE_NAME or (new_app_name != p.exe and any(profile.exe == new_app_name for profile in self.profiles)):
                QMessageBox.warning(self, "Error", "Profile already exists or name is reserved.")
                return

            old_exe = p.exe
            p.exe = new_app_name

            if old_exe in self.display_names:
                del self.display_names[old_exe]
            self.display_names[new_app_name] = new_display_name if new_display_name else new_app_name

            self.profile_list.item(row).setText(new_display_name if new_display_name else new_app_name)

            self.update_ui()
            self.save_profiles()

    def delete_profile(self):
        row = self.profile_list.currentRow()
        if self.profiles[row].exe == DEFAULT_PROFILE_NAME:
            QMessageBox.warning(self, "Error", "Cannot delete the Default profile.")
            return

        if row == -1:
            return
        exe_name = self.profiles[row].exe
        if exe_name in self.display_names:
            del self.display_names[exe_name]
            save_display_names(self.display_names)
        del self.profiles[row]
        self.profile_list.takeItem(row)

        if self.profiles:
            new_index = min(row, len(self.profiles) - 1)
            self.profile_list.setCurrentRow(new_index)
            self.current_index = new_index
            self.settings_panel.setEnabled(True)
            self.update_ui()
        else:
            self.current_index = -1
            self.settings_panel.setEnabled(False)
            self.clear_settings_panel()

        self.save_profiles()

    def profile_selected(self):
        row = self.profile_list.currentRow()
        if row == -1:
            self.current_index = -1
            self.settings_panel.setEnabled(False)
            self.clear_settings_panel()
        else:
            self.current_index = row
            self.settings_panel.setEnabled(True)
            self.update_ui()

    def update_ui(self):
        p = self.profiles[self.current_index]
        if p.exe == DEFAULT_PROFILE_NAME:
            display_name = DEFAULT_PROFILE_NAME
        else:
            display_name = self.display_names.get(p.exe, p.exe)
        self.profile_name_label.setText(f'Profile: "{display_name}"')

        if p.exe == DEFAULT_PROFILE_NAME:
            self.real_name_label.setText('Apps added from the add profile button will default to these settings.')
        elif p.exe != display_name:
            self.real_name_label.setText(f'App: {p.exe}')
        else:
            self.real_name_label.setText("")

        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(p.multiplier)
        self.mode_combo.blockSignals(False)

        self.present_combo.blockSignals(True)

        self.present_combo.setCurrentText(p.experimental_present_mode)
        self.present_combo.blockSignals(False)

        self.perf_check.blockSignals(True)
        self.perf_check.setChecked(p.performance_mode)
        self.perf_check._animate(p.performance_mode)
        self.perf_check.blockSignals(False)

        self.hdr_check.blockSignals(True)
        self.hdr_check.setChecked(p.hdr_mode)
        self.hdr_check._animate(p.hdr_mode)
        self.hdr_check.blockSignals(False)

        self.flow_slider.blockSignals(True)
        self.flow_slider.setValue(int(p.flow_scale * 100))
        self.flow_slider.blockSignals(False)

if __name__ == "__main__":
    ensure_config_exists()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
