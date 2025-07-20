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

def ensure_config_exists():
    config_dir = os.path.dirname(CONFIG_PATH)
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(config_dir, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            f.write("version = 1\n")


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
            global_pos = self.mapToGlobal(event.pos())
            x = global_pos.x() - self._tooltip_label.width() // 2
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
            x = global_pos.x() - self._tooltip_label.width() // 2
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
        self.resize(900, 500)
        self.setFixedSize(self.size())
        self.profiles = []
        self.current_index = -1
        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.build_layout())
        self.load_profiles()

    def load_profiles(self):
        if not os.path.exists(CONFIG_PATH):
            print("No config file found.")
            return
        try:
            data = toml.load(CONFIG_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{e}")
            return

        game_entries = data.get("game", [])
        if isinstance(game_entries, dict):
            game_entries = [game_entries]

        self.profiles.clear()
        self.profile_list.clear()
        for entry in game_entries:
            profile = GameProfile.from_dict(entry)
            self.profiles.append(profile)
            self.profile_list.addItem(profile.exe)

    def save_profiles(self):
        try:
            first_line = ""
            existing = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r") as f:
                    lines = f.readlines()
                if lines and lines[0].strip().startswith("version"):
                    first_line = lines[0]
                    toml_text = "".join(lines[1:])
                    existing = toml.loads(toml_text)
                else:
                    existing = toml.loads("".join(lines))

            data = {"game": [p.to_dict() for p in self.profiles]}
            if "global" in existing:
                data["global"] = existing["global"]

            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                if first_line:
                    f.write(first_line)
                    if not first_line.endswith("\n"):
                        f.write("\n")
                toml.dump(data, f)
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

        def make_btn(text, w, h, slot, style=None):
            btn = QPushButton(text)
            btn.setFixedSize(w, h)
            if style:
                btn.setStyleSheet(style)
            btn.clicked.connect(slot)
            return btn

        pal = self.palette()
        highlight = pal.color(QPalette.Highlight).name()
        highlight_text = pal.color(QPalette.HighlightedText).name()

        btn_layout.addWidget(make_btn("+", 110, 33, self.create_profile,
                                    f"background-color: {highlight}; color: {highlight_text}; font-weight: bold; border-radius:4px;"))
        btn_layout.addStretch()
        btn_layout.addWidget(make_btn("✎", 55, 33, self.rename_profile))
        btn_layout.addWidget(make_btn("🗑", 55, 33, self.delete_profile))

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

        self.profile_name_label = QLabel()
        self.profile_name_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        layout.addWidget(self.profile_name_label)

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
        text, ok = QInputDialog.getText(self, "Create Profile", "Enter profile name:")
        if ok and text:
            if any(p.exe == text for p in self.profiles):
                QMessageBox.warning(self, "Error", "Profile already exists.")
                return
            p = GameProfile(exe=text)
            self.profiles.append(p)
            self.profile_list.addItem(p.exe)
            self.profile_list.setCurrentRow(len(self.profiles) - 1)
            self.profile_selected()
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
        text, ok = QInputDialog.getText(self, "Rename Profile", "New name:", text=p.exe)
        if ok and text:
            p.exe = text
            self.profile_list.item(row).setText(text)
            self.update_ui()
            self.save_profiles()

    def delete_profile(self):
        row = self.profile_list.currentRow()
        if row == -1:
            return
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
        self.current_index = self.profile_list.currentRow()
        if self.current_index != -1:
            self.settings_panel.setEnabled(True)
            self.update_ui()

    def update_ui(self):
        p = self.profiles[self.current_index]
        self.profile_name_label.setText(f'Profile: "{p.exe}"')

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

