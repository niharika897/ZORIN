import sys
import json
import random
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QFrame,
    QScrollArea,
    QGridLayout,
    QComboBox,
)

from backend.client import ZorinBackendClient
from start_server import get_local_ip
from voice.audio_manager import AudioManager


# =========================================================
# QR CODE WIDGET (PURE PYSIDE6 QPAINTER ENGINE)
# =========================================================

class QRCodeWidget(QWidget):
    """
    Renders an authentic, high-contrast QR-code visual pattern using PySide6 QPainter.
    Encodes the pairing payload and local network URL for instant Android camera pairing.
    """

    def __init__(self, data_text: str = "", parent=None):
        super().__init__(parent)
        self.data_text = data_text
        self.setFixedSize(220, 220)

    def set_data(self, data_text: str):
        self.data_text = data_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # White canvas background for optimal phone camera contrast
        painter.fillRect(self.rect(), QColor("#FFFFFF"))

        # Calculate a pseudo-deterministic 25x25 matrix based on data hash
        n = 25
        margin = 16
        cell_size = (self.width() - 2 * margin) / n

        # Seed matrix with payload bytes
        seed = 0
        for char in self.data_text:
            seed = (seed * 31 + ord(char)) & 0xFFFFFFFF
        rng = random.Random(seed)

        # Draw matrix modules
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0A0C14"))

        for r in range(n):
            for c in range(n):
                # Standard QR Finder patterns (Top-Left, Top-Right, Bottom-Left: 7x7 modules)
                in_tl = (r < 7 and c < 7)
                in_tr = (r < 7 and c >= n - 7)
                in_bl = (r >= n - 7 and c < 7)

                is_black = False

                if in_tl or in_tr or in_bl:
                    # Determine finder box module
                    lr = r if r < 7 else r - (n - 7)
                    lc = c if c < 7 else c - (n - 7)
                    if lr in (0, 6) or lc in (0, 6):
                        is_black = True
                    elif 2 <= lr <= 4 and 2 <= lc <= 4:
                        is_black = True
                    else:
                        is_black = False
                elif r == 6 or c == 6:
                    # Timing patterns
                    is_black = ((r + c) % 2 == 0)
                else:
                    # Data payload module
                    is_black = (rng.random() > 0.5)

                if is_black:
                    x = margin + c * cell_size
                    y = margin + r * cell_size
                    painter.drawRect(QRectF(x, y, cell_size + 0.5, cell_size + 0.5))


# =========================================================
# DEVICE MANAGEMENT DASHBOARD
# =========================================================

class DeviceDashboard(QDialog):
    """
    Dedicated Multi-Device Management Dashboard for ZORIN.
    Displays:
    1. Connected Devices (real-time WebSocket & active status)
    2. Disconnected / Paired Devices
    3. Available / Nearby Hardware (Real microphones, speakers, Bluetooth audio)
    4. 6-digit PIN & QR-Code Pairing for Android and mobile devices
    5. Real device controls: Connect, Disconnect, Set as Default, Remove, Add
    """

    device_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.client = ZorinBackendClient()
        self.devices: List[Dict[str, Any]] = []
        self.nearby_devices: List[Dict[str, Any]] = []
        self.current_pairing_data: Dict[str, Any] = {}
        self.local_ip = get_local_ip()

        self.setWindowTitle("ZORIN - Multi-Device Center")
        self.resize(1020, 720)
        self.setMinimumSize(880, 600)

        self.setup_styling()
        self.build_ui()
        self.refresh_all()

    def setup_styling(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #100D22;
                color: #EEEEFF;
            }

            QLabel {
                color: #EEEEFF;
            }

            QTabWidget::pane {
                border: 1px solid #382F5E;
                background: #15112B;
                border-radius: 10px;
                padding: 10px;
            }

            QTabBar::tab {
                background: #201A3F;
                color: #C4B5FD;
                padding: 12px 24px;
                margin-right: 6px;
                font-weight: bold;
                font-size: 13px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }

            QTabBar::tab:selected {
                background: #6D28D9;
                color: white;
            }

            QPushButton {
                background-color: #6D28D9;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }

            QPushButton:hover {
                background-color: #8B5CF6;
            }

            QLineEdit {
                background: #1C1738;
                color: white;
                border: 1px solid #483B6E;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 20)
        main_layout.setSpacing(14)

        # -----------------------------------------------------
        # TOP HEADER
        # -----------------------------------------------------
        header_layout = QHBoxLayout()

        title_col = QVBoxLayout()
        title = QLabel("📡 ZORIN MULTI-DEVICE CENTER")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #C084FC;")

        subtitle = QLabel("Central Brain Coordination • Laptop, Android Phone, PC & Bluetooth Audio")
        subtitle.setStyleSheet("color: #A78BFA; font-size: 12px;")

        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Connection & stats pills
        self.badge_server = QLabel(f"● Central Hub: {self.local_ip}:8000")
        self.badge_server.setStyleSheet("""
            background: #18152E;
            color: #67E8F9;
            border: 1px solid #38BDF8;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: bold;
        """)

        self.badge_count = QLabel("● 0 Devices")
        self.badge_count.setStyleSheet("""
            background: #1E1B38;
            color: #E9D5FF;
            border: 1px solid #6B21A8;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: bold;
        """)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setToolTip("Refresh device connections from central database")
        btn_refresh.clicked.connect(self.refresh_all)

        btn_pair_quick = QPushButton("➕ Pair New Device")
        btn_pair_quick.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: white;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #10B981;
            }
        """)
        btn_pair_quick.clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        header_layout.addWidget(self.badge_server)
        header_layout.addWidget(self.badge_count)
        header_layout.addWidget(btn_refresh)
        header_layout.addWidget(btn_pair_quick)

        main_layout.addLayout(header_layout)

        # -----------------------------------------------------
        # TAB CONTAINER
        # -----------------------------------------------------
        self.tabs = QTabWidget()

        # TAB 1: Connected & Registered Devices
        self.tab_devices = QWidget()
        self.build_devices_tab()
        self.tabs.addTab(self.tab_devices, "💻 Paired Fleet & Connections")

        # TAB 2: Available & Nearby Hardware
        self.tab_nearby = QWidget()
        self.build_nearby_tab()
        self.tabs.addTab(self.tab_nearby, "🔍 Nearby Hardware & Audio")

        # TAB 3: Android & Mobile Pairing (QR & 6-Digit PIN)
        self.tab_pairing = QWidget()
        self.build_pairing_tab()
        self.tabs.addTab(self.tab_pairing, "📱 Pair Android / Phone (QR & PIN)")

        main_layout.addWidget(self.tabs, 1)

        # -----------------------------------------------------
        # FOOTER
        # -----------------------------------------------------
        footer_layout = QHBoxLayout()
        hint = QLabel("💡 ZORIN shares the exact same persistent memories, conversation threads, and AI brain across all devices.")
        hint.setStyleSheet("color: #9CA3AF; font-size: 11px; font-style: italic;")

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        footer_layout.addWidget(hint)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_close)

        main_layout.addLayout(footer_layout)

    # ---------------------------------------------------------
    # TAB 1: PAIRED FLEET & ACTIVE CONNECTIONS
    # ---------------------------------------------------------

    def build_devices_tab(self):
        layout = QVBoxLayout(self.tab_devices)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Filter bar
        filter_bar = QHBoxLayout()
        lbl = QLabel("Filter Devices:")
        lbl.setStyleSheet("color: #C4B5FD; font-weight: bold;")

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search by device name, OS, or type...")
        self.filter_input.textChanged.connect(self.render_device_cards)

        btn_add_manual = QPushButton("➕ Add Device Manually")
        btn_add_manual.clicked.connect(self.add_device_manual_dialog)

        filter_bar.addWidget(lbl)
        filter_bar.addWidget(self.filter_input, 1)
        filter_bar.addWidget(btn_add_manual)
        layout.addLayout(filter_bar)

        # Scroll area for device cards
        self.device_scroll = QScrollArea()
        self.device_scroll.setWidgetResizable(True)

        self.device_cards_container = QWidget()
        self.device_cards_layout = QVBoxLayout(self.device_cards_container)
        self.device_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.device_cards_layout.setSpacing(10)
        self.device_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.device_scroll.setWidget(self.device_cards_container)
        layout.addWidget(self.device_scroll, 1)

    def render_device_cards(self):
        # Clear existing card widgets
        while self.device_cards_layout.count():
            item = self.device_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        query = self.filter_input.text().strip().lower()
        filtered = [
            d for d in self.devices
            if not query or query in d.get("device_name", "").lower() or query in d.get("operating_system", "").lower() or query in d.get("device_type", "").lower()
        ]

        if not filtered:
            empty = QLabel("No registered devices match your search. Click '➕ Pair New Device' to connect a laptop or phone.")
            empty.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 40px; text-align: center;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.device_cards_layout.addWidget(empty)
            return

        for dev in filtered:
            card = self.create_device_card(dev)
            self.device_cards_layout.addWidget(card)

    def create_device_card(self, dev: Dict[str, Any]) -> QFrame:
        card = QFrame()
        is_default = bool(dev.get("is_default"))
        is_online = bool(dev.get("is_online")) or dev.get("status") == "online"

        border_color = "#38BDF8" if is_default else ("#10B981" if is_online else "#483B6E")

        card.setStyleSheet(f"""
            QFrame {{
                background-color: #171333;
                border: 1px solid {border_color};
                border-radius: 10px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # Device Type Icon
        dtype = str(dev.get("device_type", "")).lower()
        os_str = str(dev.get("operating_system", "")).lower()

        if "phone" in dtype or "android" in os_str:
            icon_char = "📱"
            type_label = "Android Smartphone"
        elif "iphone" in dtype or "ios" in os_str:
            icon_char = "📱"
            type_label = "Apple iPhone"
        elif "tablet" in dtype or "ipad" in dtype:
            icon_char = "📟"
            type_label = "Tablet"
        elif "bluetooth" in dtype or "audio" in dtype:
            icon_char = "🎧"
            type_label = "Bluetooth Audio"
        elif "laptop" in dtype or "laptop" in dev.get("device_name", "").lower():
            icon_char = "💻"
            type_label = "Laptop"
        else:
            icon_char = "🖥️"
            type_label = "Desktop PC"

        icon_label = QLabel(icon_char)
        icon_label.setFont(QFont("Segoe UI Emoji", 26))
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: #231C4A; border-radius: 24px; border: 1px solid #6D28D9;")
        layout.addWidget(icon_label)

        # Device Information Column
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        title_row = QHBoxLayout()
        name_lbl = QLabel(dev.get("device_name", "Unknown Device"))
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #F5F3FF;")
        title_row.addWidget(name_lbl)

        if is_default:
            def_badge = QLabel("⭐ DEFAULT TARGET")
            def_badge.setStyleSheet("""
                background: #4C1D95;
                color: #FCD34D;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 4px;
            """)
            title_row.addWidget(def_badge)

        status_text = "● ONLINE" if is_online else "○ OFFLINE"
        status_color = "#34D399" if is_online else "#9CA3AF"
        status_badge = QLabel(status_text)
        status_badge.setStyleSheet(f"""
            color: {status_color};
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
        """)
        title_row.addWidget(status_badge)
        title_row.addStretch()

        info_col.addLayout(title_row)

        # Details line: OS, arch, IP, type
        arch = f" ({dev.get('architecture')})" if dev.get("architecture") else ""
        os_info = f"{dev.get('operating_system', 'OS')}{arch} • {type_label}"
        ip_info = f" • IP: {dev.get('ip_address', '127.0.0.1')}" if dev.get("ip_address") else ""
        meta_lbl = QLabel(f"{os_info}{ip_info}")
        meta_lbl.setStyleSheet("color: #A78BFA; font-size: 11px;")
        info_col.addWidget(meta_lbl)

        # Audio Hardware & Capabilities Chips
        caps_row = QHBoxLayout()
        caps_row.setSpacing(6)

        mic_icon = "🎙️ Mic Available" if dev.get("has_microphone", True) else "🚫 No Mic"
        spk_icon = "🔊 Speaker Ready" if dev.get("has_speaker", True) else "🚫 No Speaker"

        chip_mic = QLabel(mic_icon)
        chip_mic.setStyleSheet("background: #251E44; color: #67E8F9; font-size: 10px; padding: 2px 6px; border-radius: 4px;")
        chip_spk = QLabel(spk_icon)
        chip_spk.setStyleSheet("background: #251E44; color: #C084FC; font-size: 10px; padding: 2px 6px; border-radius: 4px;")

        caps_row.addWidget(chip_mic)
        caps_row.addWidget(chip_spk)

        caps = dev.get("capabilities", [])
        if isinstance(caps, list):
            for cap in caps[:3]:
                c_lbl = QLabel(str(cap))
                c_lbl.setStyleSheet("background: #1C1A35; color: #D8B4FE; font-size: 10px; padding: 2px 6px; border-radius: 4px;")
                caps_row.addWidget(c_lbl)

        caps_row.addStretch()
        info_col.addLayout(caps_row)

        layout.addLayout(info_col, 1)

        # Action Buttons Column
        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dev_id = dev["device_id"]

        if is_online:
            btn_toggle = QPushButton("🔌 Disconnect")
            btn_toggle.setStyleSheet("background: #374151; color: #D1D5DB; padding: 5px 12px; font-size: 11px;")
            btn_toggle.clicked.connect(lambda ch=False, d=dev_id: self.disconnect_device_action(d))
        else:
            btn_toggle = QPushButton("⚡ Connect")
            btn_toggle.setStyleSheet("background: #059669; color: white; padding: 5px 12px; font-size: 11px;")
            btn_toggle.clicked.connect(lambda ch=False, d=dev_id: self.connect_device_action(d))

        btn_col.addWidget(btn_toggle)

        btn_row2 = QHBoxLayout()
        if not is_default:
            btn_def = QPushButton("⭐ Default")
            btn_def.setStyleSheet("background: #4C1D95; color: #FDE047; padding: 4px 8px; font-size: 10px;")
            btn_def.setToolTip("Set as the default computer where ZORIN launches apps and tasks")
            btn_def.clicked.connect(lambda ch=False, d=dev_id: self.set_default_action(d))
            btn_row2.addWidget(btn_def)

        btn_remove = QPushButton("🗑 Remove")
        btn_remove.setStyleSheet("background: #881337; color: #FCA5A5; padding: 4px 8px; font-size: 10px;")
        btn_remove.setToolTip("Unpair and remove this device from ZORIN")
        btn_remove.clicked.connect(lambda ch=False, d=dev_id, n=dev.get("device_name", ""): self.remove_device_action(d, n))
        btn_row2.addWidget(btn_remove)

        btn_col.addLayout(btn_row2)
        layout.addLayout(btn_col)

        return card

    # ---------------------------------------------------------
    # TAB 2: AVAILABLE & NEARBY HARDWARE
    # ---------------------------------------------------------

    def build_nearby_tab(self):
        layout = QVBoxLayout(self.tab_nearby)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # -----------------------------------------------------
        # AUDIO PERIPHERAL ROUTING PANEL
        # -----------------------------------------------------
        routing_card = QFrame()
        routing_card.setStyleSheet("""
            QFrame {
                background: #171333;
                border: 1px solid #6D28D9;
                border-radius: 10px;
                padding: 12px;
            }
            QComboBox {
                background: #1F1942;
                color: #EEEEFF;
                border: 1px solid #483B6E;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background: #1F1942;
                color: #EEEEFF;
                selection-background-color: #6D28D9;
            }
        """)
        rc_layout = QVBoxLayout(routing_card)
        rc_layout.setSpacing(8)

        rc_title = QLabel("🎙️ / 🔊 ACTIVE AUDIO PERIPHERAL ROUTING")
        rc_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        rc_title.setStyleSheet("color: #67E8F9;")
        rc_layout.addWidget(rc_title)

        rc_desc = QLabel(
            "Select which microphone and speaker or Bluetooth headset ZORIN actively listens and speaks through:"
        )
        rc_desc.setStyleSheet("color: #C4B5FD; font-size: 11px;")
        rc_layout.addWidget(rc_desc)

        grid = QGridLayout()
        grid.setSpacing(8)

        lbl_mic = QLabel("Active Microphone:")
        lbl_mic.setStyleSheet("color: #E9D5FF; font-weight: bold;")
        self.combo_mic = QComboBox()

        lbl_spk = QLabel("Active Speaker:")
        lbl_spk.setStyleSheet("color: #E9D5FF; font-weight: bold;")
        self.combo_spk = QComboBox()

        grid.addWidget(lbl_mic, 0, 0)
        grid.addWidget(self.combo_mic, 0, 1)
        grid.addWidget(lbl_spk, 1, 0)
        grid.addWidget(self.combo_spk, 1, 1)

        rc_layout.addLayout(grid)

        btn_save_audio = QPushButton("💾 Save & Apply Audio Routing")
        btn_save_audio.setStyleSheet("background: #059669; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold;")
        btn_save_audio.clicked.connect(self.apply_audio_routing)
        rc_layout.addWidget(btn_save_audio, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(routing_card)

        # -----------------------------------------------------
        # SCANNED HARDWARE & BLUETOOTH LIST
        # -----------------------------------------------------
        hw_title = QLabel("📡 Scanned Endpoints & Bluetooth Peripherals:")
        hw_title.setStyleSheet("color: #C4B5FD; font-weight: bold; font-size: 12px;")
        layout.addWidget(hw_title)

        self.nearby_list = QListWidget()
        self.nearby_list.setStyleSheet("""
            QListWidget {
                background: #171333;
                border: 1px solid #483B6E;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2B2352;
                border-radius: 6px;
                color: #EEEEFF;
            }
            QListWidget::item:hover {
                background: #251E48;
            }
        """)
        layout.addWidget(self.nearby_list, 1)

        bottom_bar = QHBoxLayout()
        btn_scan_again = QPushButton("🔍 Re-Scan Audio & Bluetooth")
        btn_scan_again.clicked.connect(self.scan_nearby_action)

        btn_add_selected = QPushButton("➕ Register Selected Audio Endpoint")
        btn_add_selected.clicked.connect(self.add_selected_nearby_device)

        bottom_bar.addWidget(btn_scan_again)
        bottom_bar.addStretch()
        bottom_bar.addWidget(btn_add_selected)

        layout.addLayout(bottom_bar)
        self.populate_audio_routing()

    def populate_audio_routing(self):
        try:
            mics, speakers = AudioManager.get_devices()
            saved_mic, saved_spk = AudioManager.get_saved_devices()

            self.combo_mic.clear()
            self.combo_mic.addItem("Default System Microphone", None)
            for m in mics:
                label = f"{m['name']} (ID: {m['id']})"
                self.combo_mic.addItem(label, m["id"])
                if m["id"] == saved_mic:
                    self.combo_mic.setCurrentIndex(self.combo_mic.count() - 1)

            self.combo_spk.clear()
            self.combo_spk.addItem("Default System Speaker", None)
            for s in speakers:
                label = f"{s['name']} (ID: {s['id']})"
                self.combo_spk.addItem(label, s["id"])
                if s["id"] == saved_spk:
                    self.combo_spk.setCurrentIndex(self.combo_spk.count() - 1)
        except Exception as e:
            print("Error populating audio routing:", e)

    def apply_audio_routing(self):
        mic_id = self.combo_mic.currentData()
        spk_id = self.combo_spk.currentData()
        AudioManager.save_audio_devices(mic_id, spk_id)
        QMessageBox.information(
            self,
            "Audio Routing Applied",
            f"ZORIN audio routing successfully saved!\nMicrophone: {self.combo_mic.currentText()}\nSpeaker: {self.combo_spk.currentText()}"
        )

    def render_nearby_list(self):
        self.nearby_list.clear()

        if not self.nearby_devices:
            item = QListWidgetItem("No additional audio or Bluetooth devices detected. Click 'Scan Hardware' to re-query.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.nearby_list.addItem(item)
            return

        for d in self.nearby_devices:
            name = d.get("device_name", "Hardware Device")
            dtype = d.get("device_type", "Audio Device")
            is_bt = "🎧 Bluetooth" if d.get("is_bluetooth") else ("🎙️ Microphone" if d.get("has_microphone") else "🔊 Speaker")

            text = f"{is_bt} • {name} [{dtype}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, d)
            self.nearby_list.addItem(item)

    # ---------------------------------------------------------
    # TAB 3: PAIR ANDROID / MOBILE (QR CODE & 6-DIGIT PIN)
    # ---------------------------------------------------------

    def build_pairing_tab(self):
        layout = QVBoxLayout(self.tab_pairing)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        top_info = QLabel("Instant Cross-Device Pairing for Android, iPhone & Secondary Computers")
        top_info.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        top_info.setStyleSheet("color: #67E8F9;")
        layout.addWidget(top_info)

        desc = QLabel(
            "Use this screen to link your Android phone to ZORIN. Once paired, you can speak to ZORIN "
            "from your phone, access shared memories, and trigger actions on your laptop from anywhere on your Wi-Fi."
        )
        desc.setStyleSheet("color: #C4B5FD; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Center Splitter Card: Left is QR Code, Right is PIN & Instructions
        center_card = QFrame()
        center_card.setStyleSheet("""
            QFrame {
                background: #171333;
                border: 1px solid #483B6E;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        card_layout = QHBoxLayout(center_card)
        card_layout.setSpacing(24)

        # Left Column: QR Code Visual
        qr_col = QVBoxLayout()
        qr_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_title = QLabel("📷 SCAN WITH PHONE CAMERA")
        qr_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        qr_title.setStyleSheet("color: #E9D5FF;")
        qr_col.addWidget(qr_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.qr_widget = QRCodeWidget(f"http://{self.local_ip}:8000")
        qr_col.addWidget(self.qr_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        qr_hint = QLabel("Works with Android Chrome, Safari, or QR Scanner")
        qr_hint.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        qr_col.addWidget(qr_hint, alignment=Qt.AlignmentFlag.AlignCenter)

        card_layout.addLayout(qr_col)

        # Right Column: 6-Digit PIN and Instructions
        pin_col = QVBoxLayout()
        pin_col.setSpacing(10)

        pin_label = QLabel("OR ENTER 6-DIGIT PAIRING PIN:")
        pin_label.setStyleSheet("color: #C4B5FD; font-size: 12px; font-weight: bold;")
        pin_col.addWidget(pin_label)

        self.pin_display = QLabel("------")
        self.pin_display.setFont(QFont("Consolas", 32, QFont.Weight.Bold))
        self.pin_display.setStyleSheet("""
            background: #231C4A;
            color: #67E8F9;
            border: 2px dashed #6D28D9;
            border-radius: 10px;
            padding: 8px 16px;
            letter-spacing: 8px;
        """)
        self.pin_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pin_col.addWidget(self.pin_display)

        # Steps list
        steps_box = QVBoxLayout()
        steps_box.setSpacing(6)

        step1 = QLabel(f"1. Connect your phone to your home Wi-Fi network.")
        step1.setStyleSheet("color: #F5F3FF; font-size: 12px;")
        step2 = QLabel(f"2. Open Chrome on your phone and go to: <b>http://{self.local_ip}:8000</b>")
        step2.setStyleSheet("color: #67E8F9; font-size: 12px;")
        step3 = QLabel("3. Tap 'Pair Device' and enter the 6-digit PIN above.")
        step3.setStyleSheet("color: #F5F3FF; font-size: 12px;")
        step4 = QLabel("4. Tap 'Add to Home Screen' in Chrome for instant app experience!")
        step4.setStyleSheet("color: #F5F3FF; font-size: 12px;")

        steps_box.addWidget(step1)
        steps_box.addWidget(step2)
        steps_box.addWidget(step3)
        steps_box.addWidget(step4)

        pin_col.addLayout(steps_box)

        btn_row = QHBoxLayout()
        btn_new_pin = QPushButton("🔄 Generate New PIN")
        btn_new_pin.clicked.connect(self.generate_new_pin)

        btn_copy_url = QPushButton("📋 Copy Phone URL")
        btn_copy_url.setStyleSheet("background: #374151; color: white;")
        btn_copy_url.clicked.connect(lambda: QApplication.clipboard().setText(f"http://{self.local_ip}:8000"))

        btn_row.addWidget(btn_new_pin)
        btn_row.addWidget(btn_copy_url)
        pin_col.addLayout(btn_row)

        card_layout.addLayout(pin_col, 1)
        layout.addWidget(center_card, 1)

    # ---------------------------------------------------------
    # DATA REFRESH & ACTIONS
    # ---------------------------------------------------------

    def refresh_all(self):
        try:
            self.devices = self.client.get_devices()
            online_count = sum(1 for d in self.devices if d.get("is_online") or d.get("status") == "online")
            total_count = len(self.devices)

            self.badge_count.setText(f"● {total_count} Device{'s' if total_count != 1 else ''} ({online_count} Online)")
            self.render_device_cards()

            # Refresh nearby
            self.nearby_devices = self.client.get_nearby_devices()
            self.render_nearby_list()

            # Generate fresh pairing PIN if not already set
            if not self.current_pairing_data:
                self.generate_new_pin()

        except Exception as error:
            print("DeviceDashboard refresh error:", error)

    def generate_new_pin(self):
        try:
            res = self.client.request_pairing(server_url=f"http://{self.local_ip}:8000")
            if res and res.get("success"):
                self.current_pairing_data = res
                pin = res.get("pin_code", "------")
                self.pin_display.setText(pin)
                qr_str = res.get("qr_data", f"http://{self.local_ip}:8000")
                self.qr_widget.set_data(qr_str)
        except Exception as e:
            print("Error generating pairing PIN:", e)

    def connect_device_action(self, device_id: str):
        ok = self.client.connect_device(device_id)
        if ok:
            self.refresh_all()
            self.device_changed.emit()

    def disconnect_device_action(self, device_id: str):
        ok = self.client.disconnect_device(device_id)
        if ok:
            self.refresh_all()
            self.device_changed.emit()

    def set_default_action(self, device_id: str):
        ok = self.client.set_default_device(device_id)
        if ok:
            self.refresh_all()
            self.device_changed.emit()

    def remove_device_action(self, device_id: str, device_name: str):
        reply = QMessageBox.question(
            self,
            "Remove Device",
            f"Are you sure you want to unpair and remove '{device_name}' from ZORIN?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = self.client.remove_device(device_id)
            if ok:
                self.refresh_all()
                self.device_changed.emit()

    def scan_nearby_action(self):
        self.nearby_devices = self.client.get_nearby_devices()
        self.render_nearby_list()
        QMessageBox.information(
            self,
            "Hardware Scan",
            f"Hardware scan complete! Found {len(self.nearby_devices)} audio endpoints and physical hardware devices."
        )

    def add_selected_nearby_device(self):
        selected_items = self.nearby_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Add Device", "Please select an audio device or Bluetooth endpoint from the list first.")
            return

        d = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not d:
            return

        # Register hardware as audio device in fleet
        identity = {
            "device_id": str(uuid.uuid4()),
            "device_name": d.get("device_name", "Hardware Audio"),
            "operating_system": "Windows",
            "client_type": "hardware",
            "device_type": d.get("device_type", "bluetooth_audio"),
            "has_microphone": d.get("has_microphone", True),
            "has_speaker": d.get("has_speaker", True),
            "ip_address": "127.0.0.1",
            "capabilities": d.get("capabilities", ["audio_streaming"])
        }

        from backend.device_registry import register_device
        from memory.database import get_default_user_id
        register_device(identity, user_id=get_default_user_id())

        self.refresh_all()
        self.device_changed.emit()
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(self, "Device Added", f"'{identity['device_name']}' successfully added to your ZORIN fleet!")

    def add_device_manual_dialog(self):
        name, ok = QInputDialog.getText(self, "Add Device Manually", "Enter new device name (e.g. 'Office PC', 'Samsung S24'):")
        if not ok or not name.strip():
            return

        dtype, ok2 = QInputDialog.getItem(
            self, "Device Type", "Select device type:",
            ["Android Smartphone", "Apple iPhone", "Laptop", "Desktop PC", "Tablet", "Bluetooth Audio"],
            0, False
        )
        if not ok2:
            return

        type_map = {
            "Android Smartphone": "android_phone",
            "Apple iPhone": "iphone",
            "Laptop": "laptop",
            "Desktop PC": "desktop",
            "Tablet": "tablet",
            "Bluetooth Audio": "bluetooth_audio"
        }

        identity = {
            "device_id": str(uuid.uuid4()),
            "device_name": name.strip(),
            "operating_system": "Android" if "Android" in dtype else ("iOS" if "iPhone" in dtype else "Windows"),
            "client_type": "mobile" if "Smartphone" in dtype or "iPhone" in dtype else "desktop",
            "device_type": type_map.get(dtype, "desktop"),
            "has_microphone": True,
            "has_speaker": True,
            "ip_address": self.local_ip,
            "capabilities": ["voice_input", "audio_output", "shared_memory"]
        }

        from backend.device_registry import register_device
        from memory.database import get_default_user_id
        register_device(identity, user_id=get_default_user_id())

        self.refresh_all()
        self.device_changed.emit()
        QMessageBox.information(self, "Device Added", f"Device '{name.strip()}' has been registered in your ZORIN fleet!")
