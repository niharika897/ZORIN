import sys
import math
import random
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QMessageBox, QComboBox,
    QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QInputDialog
)

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QLinearGradient, QRadialGradient, QFont, QAction
)

from memory.database import Database
from config.settings import (
    get_voice_preference,
    set_voice_preference,
    get_voice_gender
)


# =========================================================
# ANIMATED ROBOT WIDGET (ORIGINAL PRESERVED CANVAS)
# =========================================================

class RobotWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.setMinimumSize(380, 440)
        self.t = 0
        self.state = "idle"

        self.particles = [
            [random.random(), random.random(), random.uniform(1, 3)]
            for _ in range(65)
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def animate(self):
        self.t += 1

        for p in self.particles:
            p[1] -= 0.002
            if p[1] < 0:
                p[1] = 1

        self.update()

    def set_state(self, state):
        self.state = state.lower()
        self.update()

    def glow(self, painter, x, y, radius, color):
        gradient = QRadialGradient(x, y, radius)
        gradient.setColorAt(0, QColor(color))
        gradient.setColorAt(
            1,
            QColor(color.red(), color.green(), color.blue(), 0)
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(x, y), radius, radius)

    def paintEvent(self, event):

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        p.fillRect(self.rect(), QColor("#100D22"))

        # Floating ambient particles
        for x, y, size in self.particles:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(190, 130, 255, 130))
            p.drawEllipse(QPointF(x * w, y * h), size, size)

        # Background glow
        self.glow(p, cx, cy, 190, QColor(120, 50, 255, 75))

        # Holographic rings
        for i in range(3):
            p.save()
            p.translate(cx, cy - 10)
            p.rotate(self.t * (1 if i % 2 == 0 else -1))

            pen = QPen(
                QColor(150, 110, 255, 130 - i * 25),
                2
            )
            pen.setStyle(Qt.PenStyle.DashLine)

            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            r = 125 + i * 17

            p.drawEllipse(
                QRectF(-r, -r * 0.4, r * 2, r * 0.8)
            )

            p.restore()

        # Floating robot
        floating = math.sin(self.t * 0.045) * 8

        p.save()
        p.translate(cx, cy - 10 + floating)

        # Robot shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 100))
        p.drawEllipse(QRectF(-90, 150, 180, 25))

        # Robot body
        body = QLinearGradient(-70, 30, 70, 150)
        body.setColorAt(0, QColor("#A855F7"))
        body.setColorAt(0.5, QColor("#3948A5"))
        body.setColorAt(1, QColor("#111B48"))

        p.setPen(QPen(QColor("#C4B5FD"), 2))
        p.setBrush(body)

        p.drawRoundedRect(
            QRectF(-72, 35, 144, 115),
            40, 40
        )

        # Arms
        p.setPen(QPen(QColor("#A78BFA"), 9))
        p.drawLine(-65, 65, -90, 105)
        p.drawLine(65, 65, 90, 105)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#C4B5FD"))

        p.drawEllipse(QPointF(-91, 108), 11, 11)
        p.drawEllipse(QPointF(91, 108), 11, 11)

        # Chest
        p.setPen(QPen(QColor("#60A5FA"), 2))
        p.setBrush(QColor("#10152F"))

        p.drawRoundedRect(
            QRectF(-38, 65, 76, 58),
            18, 18
        )

        pulse = 13 + math.sin(self.t * 0.12) * 4

        self.glow(
            p, 0, 94, 35,
            QColor(56, 189, 248, 140)
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#67E8F9"))

        p.drawEllipse(
            QPointF(0, 94),
            pulse / 2,
            pulse / 2
        )

        # Neck
        p.setBrush(QColor("#7770C9"))

        p.drawRoundedRect(
            QRectF(-15, 10, 30, 30),
            8, 8
        )

        # Head
        head = QLinearGradient(-70, -130, 70, 10)
        head.setColorAt(0, QColor("#E9D5FF"))
        head.setColorAt(0.5, QColor("#8057E8"))
        head.setColorAt(1, QColor("#263B86"))

        p.setPen(QPen(QColor("#C4B5FD"), 3))
        p.setBrush(head)

        p.drawRoundedRect(
            QRectF(-85, -130, 170, 140),
            48, 48
        )

        # Face
        p.setPen(QPen(QColor("#93C5FD"), 2))
        p.setBrush(QColor("#10152F"))

        p.drawRoundedRect(
            QRectF(-68, -110, 136, 100),
            35, 35
        )

        # Antenna
        p.setPen(QPen(QColor("#C4B5FD"), 4))
        p.drawLine(0, -130, 0, -153)

        self.glow(
            p, 0, -160, 20,
            QColor(236, 72, 153, 150)
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#F0ABFC"))

        p.drawEllipse(QPointF(0, -160), 7, 7)

        # Ears
        p.setBrush(QColor("#A78BFA"))

        p.drawRoundedRect(
            QRectF(-96, -85, 14, 38),
            7, 7
        )

        p.drawRoundedRect(
            QRectF(82, -85, 14, 38),
            7, 7
        )

        # Eyes
        eye = (
            QColor("#67E8F9")
            if self.state in ("speaking", "listening")
            else QColor("#F0ABFC")
        )

        blink = self.t % 160 < 7
        eye_height = 3 if blink else 19

        p.setBrush(eye)

        p.drawRoundedRect(
            QRectF(-47, -77, 27, eye_height),
            10, 10
        )

        p.drawRoundedRect(
            QRectF(20, -77, 27, eye_height),
            10, 10
        )

        # Mouth
        mouth = 5

        if self.state == "speaking":
            mouth = (
                8 + abs(math.sin(self.t * 0.25)) * 15
            )
        elif self.state == "listening":
            mouth = 9

        p.setBrush(QColor("#F0ABFC"))

        p.drawRoundedRect(
            QRectF(-15, -35, 30, mouth),
            8, 8
        )

        p.restore()

        # Robot name
        p.setPen(QColor("#E9D5FF"))
        p.setFont(
            QFont("Segoe UI", 18, QFont.Weight.Bold)
        )

        p.drawText(
            QRectF(0, h - 55, w, 28),
            Qt.AlignmentFlag.AlignCenter,
            "Z O R I N"
        )

        p.setPen(QColor("#A5A0BD"))
        p.setFont(QFont("Segoe UI", 9))

        p.drawText(
            QRectF(0, h - 28, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "YOUR PERSONAL AI COMPANION"
        )


# =========================================================
# MAIN ZORIN DESKTOP WINDOW
# =========================================================

class ZorinWindow(QMainWindow):

    stop_requested = Signal()
    voice_toggle_requested = Signal()
    text_submitted = Signal(str)
    conversation_switched = Signal(int)
    new_conversation_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ZORIN AI")
        self.resize(1320, 840)
        self.setMinimumSize(1000, 700)

        self.memory_dashboard = None
        self.device_dashboard = None
        self.voice_combo = None
        self.active_conversation_id = None
        self.conversation_rows = []
        self.is_voice_active = False

        self.setStyleSheet("""
            QMainWindow {
                background: #090817;
            }

            QLabel {
                color: #F5F3FF;
            }

            QFrame#panel {
                background: #15132A;
                border: 1px solid #493477;
                border-radius: 20px;
            }

            QPushButton {
                background: #292044;
                color: white;
                border: 1px solid #8057B8;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #60408A;
            }

            QPushButton#stop {
                background: #581C36;
                border: 1px solid #EC4899;
            }

            QPushButton#voice_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7928CA, stop:1 #2A85FF);
                color: white;
                border: 1px solid #C084FC;
                border-radius: 12px;
                padding: 11px 18px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#voice_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333EA, stop:1 #38BDF8);
            }

            QPushButton#voice_btn_active {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DC2626, stop:1 #E11D48);
                color: white;
                border: 1px solid #F43F5E;
                border-radius: 12px;
                padding: 11px 18px;
                font-size: 13px;
                font-weight: bold;
            }

            QLineEdit {
                background: #1D1A35;
                color: #F5F3FF;
                border: 1px solid #604C91;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #C084FC;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QListWidget {
                background: transparent;
                color: #E9D5FF;
                border: none;
                outline: none;
            }

            QListWidget::item {
                background: #1B1830;
                border-radius: 8px;
                padding: 4px;
                margin: 2px 0;
            }

            QListWidget::item:selected {
                background: #493477;
                border: 1px solid #A78BFA;
            }
        """)

        self.build_interface()
        self.load_conversations()

    # ==========================================
    # DATABASE HELPERS
    # ==========================================

    def get_database_connection(self):
        database = Database()
        return database.get_connection()

    def get_conversations(self):
        connection = self.get_database_connection()
        try:
            rows = connection.execute("""
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m
                    ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.created_at DESC, c.id DESC
            """).fetchall()
            return [dict(row) for row in rows]
        except Exception:
            return []
        finally:
            connection.close()

    def get_conversation_messages(self, conversation_id):
        connection = self.get_database_connection()
        try:
            rows = connection.execute("""
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
            """, (conversation_id,)).fetchall()
            return [dict(row) for row in rows]
        except Exception:
            return []
        finally:
            connection.close()

    # ==========================================
    # BUILD USER INTERFACE
    # ==========================================

    def build_interface(self):

        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)
        main.setContentsMargins(22, 16, 22, 16)
        main.setSpacing(14)

        # --------------------------------------
        # HEADER
        # --------------------------------------
        header = QHBoxLayout()

        logo = QLabel("✦ ZORIN")
        logo.setFont(QFont("Segoe UI", 25, QFont.Weight.Bold))
        logo.setStyleSheet("color: #C084FC;")

        tagline = QLabel("YOUR PERSONAL AI UNIVERSE")
        tagline.setStyleSheet("color: #A5A0BD; font-size: 11px;")

        # Real Connected Device Indicator (Clickable button that opens Device Center)
        self.device_badge = QPushButton("● Central Hub (Syncing...)")
        self.device_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.device_badge.setStyleSheet("""
            QPushButton {
                background: #18152E;
                color: #67E8F9;
                border: 1px solid #38BDF8;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #251F48;
                color: white;
            }
        """)
        self.device_badge.setToolTip("Click to open ZORIN Multi-Device Center")
        self.device_badge.clicked.connect(self.open_device_dashboard)

        # Dedicated Devices Button in Header
        self.devices_button = QPushButton("📱 DEVICES")
        self.devices_button.setStyleSheet("""
            QPushButton {
                background: #1E1738;
                color: #67E8F9;
                border: 1px solid #38BDF8;
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2B2154;
                color: white;
            }
        """)
        self.devices_button.clicked.connect(self.open_device_dashboard)

        # Voice Selector Dropdown
        self.voice_combo = QComboBox()
        self.voice_combo.setStyleSheet("""
            QComboBox {
                background: #1E1738;
                color: #E9D5FF;
                border: 1px solid #6D4C9A;
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #15132A;
                color: #F5F3FF;
                selection-background-color: #60408A;
            }
        """)
        self.voice_combo.addItem("👨 Male Voice (Puck)", "Puck")
        self.voice_combo.addItem("👩 Female Voice (Aoede)", "Aoede")
        saved_voice = get_voice_preference()
        self.voice_combo.setCurrentIndex(1 if saved_voice.lower() == "aoede" else 0)
        self.voice_combo.currentIndexChanged.connect(self.on_voice_selection_changed)

        # Memory Button in Header
        self.memory_button = QPushButton("🧠 MEMORY")
        self.memory_button.clicked.connect(self.open_memory_dashboard)

        # Conversation History Drawer Button
        self.history_button = QPushButton("☰")
        self.history_button.setToolTip("Toggle Conversation History")
        self.history_button.setFixedSize(44, 38)
        self.history_button.clicked.connect(self.toggle_history)

        # Connection / Voice State Badge
        self.connection = QLabel("● IDLE")
        self.connection.setStyleSheet("color: #93C5FD; font-weight: bold; font-size: 12px; padding-left: 6px;")

        header.addWidget(logo)
        header.addWidget(tagline)
        header.addStretch()
        header.addWidget(self.device_badge)
        header.addWidget(self.devices_button)
        header.addWidget(self.voice_combo)
        header.addWidget(self.memory_button)
        header.addWidget(self.history_button)
        header.addWidget(self.connection)

        main.addLayout(header)

        # --------------------------------------
        # MAIN PANELS (ORIGINAL 2-COLUMN LAYOUT)
        # --------------------------------------
        content = QHBoxLayout()
        content.setSpacing(18)

        # LEFT PANEL: ROBOT ASSISTANT
        robot_panel = QFrame()
        robot_panel.setObjectName("panel")

        rl = QVBoxLayout(robot_panel)
        rl.setContentsMargins(18, 14, 18, 16)
        rl.setSpacing(10)

        title = QLabel("MEET YOUR ASSISTANT")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #D8B4FE;")

        self.robot = RobotWidget()

        self.status = QLabel("ZORIN IS READY")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.status.setStyleSheet("color: #67E8F9;")

        self.description = QLabel("Say 'Hey Zorin' or click below to start voice.")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setStyleSheet("color: #A5A0BD; font-size: 11px;")
        self.description.setWordWrap(True)

        # MANUAL MICROPHONE / VOICE BUTTON
        self.voice_button = QPushButton("🎙️ START VOICE CONVERSATION")
        self.voice_button.setObjectName("voice_btn")
        self.voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_button.clicked.connect(self.voice_toggle_requested.emit)

        rl.addWidget(title)
        rl.addWidget(self.robot, 1)
        rl.addWidget(self.status)
        rl.addWidget(self.description)
        rl.addWidget(self.voice_button)

        # RIGHT PANEL: CONVERSATION WITH COLLAPSIBLE SIDEBAR
        chat_panel = QFrame()
        chat_panel.setObjectName("panel")

        chat_main = QHBoxLayout(chat_panel)
        chat_main.setContentsMargins(12, 14, 12, 14)
        chat_main.setSpacing(12)

        # COLLAPSIBLE HISTORY SIDEBAR (Hidden by default, preserves original appearance)
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("""
            QFrame {
                background: #100E20;
                border: 1px solid #33264F;
                border-radius: 14px;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("PAST CHATS")
        sidebar_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sidebar_title.setStyleSheet("color: #D8B4FE; border: none;")

        self.new_chat_button = QPushButton("+ New Conversation")
        self.new_chat_button.clicked.connect(self.new_chat)

        self.search_conversations = QLineEdit()
        self.search_conversations.setPlaceholderText("⌕ Search chats...")
        self.search_conversations.textChanged.connect(self.filter_conversations)

        self.conversation_list = QListWidget()
        self.conversation_list.itemClicked.connect(self.open_selected_conversation)

        sidebar_layout.addWidget(sidebar_title)
        sidebar_layout.addWidget(self.new_chat_button)
        sidebar_layout.addWidget(self.search_conversations)
        sidebar_layout.addWidget(self.conversation_list, 1)

        # CHAT DISPLAY & INPUT AREA
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(10)

        # CONVERSATION TOP BAR WITH RENAME, EDIT, AND DELETE OPTIONS
        chat_top_bar = QHBoxLayout()
        chat_top_bar.setContentsMargins(0, 0, 0, 0)
        chat_top_bar.setSpacing(6)

        self.chat_title = QLabel("✧ CONVERSATION")
        self.chat_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.chat_title.setStyleSheet("color: #C084FC;")

        chat_top_bar.addWidget(self.chat_title)
        chat_top_bar.addStretch()

        self.btn_rename_chat = QPushButton("✎ Rename")
        self.btn_rename_chat.setToolTip("Rename current conversation")
        self.btn_rename_chat.setStyleSheet("""
            QPushButton {
                background: #1F1A35;
                color: #D8B4FE;
                border: 1px solid #4E3C75;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #503882;
                color: white;
            }
        """)
        self.btn_rename_chat.clicked.connect(self.rename_current_conversation)

        self.btn_edit_chat = QPushButton("✏ Edit")
        self.btn_edit_chat.setToolTip("Edit conversation title")
        self.btn_edit_chat.setStyleSheet("""
            QPushButton {
                background: #1F1A35;
                color: #A78BFA;
                border: 1px solid #4E3C75;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #503882;
                color: white;
            }
        """)
        self.btn_edit_chat.clicked.connect(self.edit_current_conversation)

        self.btn_delete_chat = QPushButton("🗑 Delete")
        self.btn_delete_chat.setToolTip("Delete current conversation")
        self.btn_delete_chat.setStyleSheet("""
            QPushButton {
                background: #2D1424;
                color: #F87171;
                border: 1px solid #881337;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #9F1239;
                color: white;
            }
        """)
        self.btn_delete_chat.clicked.connect(self.delete_current_conversation)

        chat_top_bar.addWidget(self.btn_rename_chat)
        chat_top_bar.addWidget(self.btn_edit_chat)
        chat_top_bar.addWidget(self.btn_delete_chat)

        chat_layout.addLayout(chat_top_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(12)
        self.scroll.setWidget(self.chat_widget)

        # COMMAND & TEXT INPUT ROW
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a message or command (e.g. 'Open Chrome', 'Remember I like coffee')...")
        self.text_input.returnPressed.connect(self.submit_text)

        self.btn_send = QPushButton("➤ SEND")
        self.btn_send.clicked.connect(self.submit_text)

        self.btn_mic_quick = QPushButton("🎙️")
        self.btn_mic_quick.setToolTip("Toggle Voice Conversation")
        self.btn_mic_quick.setFixedSize(44, 40)
        self.btn_mic_quick.clicked.connect(self.voice_toggle_requested.emit)

        input_bar.addWidget(self.text_input, 1)
        input_bar.addWidget(self.btn_send)
        input_bar.addWidget(self.btn_mic_quick)

        chat_layout.addWidget(self.scroll, 1)
        chat_layout.addLayout(input_bar)

        chat_main.addWidget(self.sidebar)
        chat_main.addWidget(chat_area, 1)

        # Hidden by default to preserve the exact original interface look
        self.sidebar.hide()

        content.addWidget(robot_panel, 5)
        content.addWidget(chat_panel, 7)

        main.addLayout(content, 1)

        # --------------------------------------
        # FOOTER
        # --------------------------------------
        footer = QHBoxLayout()

        settings = QPushButton("⚙ SETTINGS")
        settings.clicked.connect(self.open_memory_dashboard)

        devices_btn = QPushButton("📱 DEVICES")
        devices_btn.clicked.connect(self.open_device_dashboard)

        stop = QPushButton("⏻ STOP ZORIN")
        stop.setObjectName("stop")
        stop.clicked.connect(self.stop_requested.emit)

        footer.addWidget(settings)
        footer.addWidget(devices_btn)
        footer.addStretch()
        footer.addWidget(stop)

        main.addLayout(footer)

        self.add_message(
            "ZORIN",
            "Hello! I am ZORIN, your personal AI assistant. I'm ready to listen or receive commands. ✨"
        )

    # ==========================================
    # REAL CONNECTED DEVICE BADGE
    # ==========================================

    def update_device_badge(self, devices: List[Dict[str, Any]], server_online: bool = True):
        count = len(devices)
        if not server_online:
            self.device_badge.setText("● Local Standalone Mode")
            self.device_badge.setStyleSheet("""
                QPushButton {
                    background: #1F1424;
                    color: #F87171;
                    border: 1px solid #EF4444;
                    border-radius: 10px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #331A26;
                }
            """)
            self.device_badge.setToolTip("Central server offline; using direct local memory vault. Click to manage devices.")
            return

        default_name = "Laptop"
        device_names = []
        for d in devices:
            name = d.get("device_name") or d.get("device_id") or "Device"
            device_names.append(name)
            if d.get("is_default"):
                default_name = name

        badge_text = f"● Central Hub: {count} Device{'s' if count != 1 else ''} Paired ({default_name})"
        self.device_badge.setText(badge_text)
        self.device_badge.setStyleSheet("""
            QPushButton {
                background: #18152E;
                color: #67E8F9;
                border: 1px solid #38BDF8;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #251F48;
                color: white;
            }
        """)

        tooltip_lines = ["📡 ZORIN Central Hub Connected (Click to open Device Center)", f"Total Paired Devices: {count}"]
        for d in devices:
            is_def = " (Default Execution Target)" if d.get("is_default") else ""
            os_info = f" [{d.get('operating_system', 'OS')}]"
            tooltip_lines.append(f"  • {d.get('device_name', 'Device')}{os_info}{is_def}")
        self.device_badge.setToolTip("\n".join(tooltip_lines))

    # ==========================================
    # VOICE WORKFLOW UI UPDATES
    # ==========================================

    def set_voice_active(self, active: bool):
        self.is_voice_active = active
        if active:
            self.voice_button.setText("⏹ STOP VOICE SESSION")
            self.voice_button.setObjectName("voice_btn_active")
            self.btn_mic_quick.setText("⏹")
        else:
            self.voice_button.setText("🎙️ START VOICE CONVERSATION")
            self.voice_button.setObjectName("voice_btn")
            self.btn_mic_quick.setText("🎙️")
        self.voice_button.style().unpolish(self.voice_button)
        self.voice_button.style().polish(self.voice_button)

    # ==========================================
    # TEXT SUBMISSION
    # ==========================================

    def submit_text(self):
        text = self.text_input.text().strip()
        if not text:
            return
        self.text_input.clear()
        self.text_submitted.emit(text)

    # ==========================================
    # SHOW / HIDE HISTORY SIDEBAR
    # ==========================================

    def toggle_history(self):
        if not self.sidebar.isHidden():
            self.sidebar.hide()
            self.history_button.setToolTip("Show Conversation History")
        else:
            self.sidebar.show()
            self.history_button.setToolTip("Hide Conversation History")
            self.load_conversations()

    def load_conversations(self):
        try:
            self.conversation_rows = self.get_conversations()
            self.display_conversations(self.conversation_rows)
        except Exception as error:
            print("Conversation history error:", error)

    def display_conversations(self, conversations):
        self.conversation_list.clear()

        for conv in conversations:
            cid = conv["id"]
            title = conv.get("title") or f"Conversation #{cid}"

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, cid)

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(4)

            title_btn = QPushButton(title)
            title_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #E9D5FF;
                    border: none;
                    text-align: left;
                    padding: 5px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background: #332750;
                    color: white;
                }
            """)
            title_btn.clicked.connect(lambda ch=False, c=cid: self.switch_to_conversation(c))

            menu_btn = QPushButton("⋯")
            menu_btn.setFixedSize(28, 28)
            menu_btn.setStyleSheet("""
                QPushButton {
                    background: #251E3A;
                    color: #D8B4FE;
                    border: 1px solid #4E3C75;
                    border-radius: 6px;
                    font-size: 16px;
                    padding: 0;
                }
                QPushButton:hover {
                    background: #6D4C9A;
                    color: white;
                }
            """)
            menu_btn.clicked.connect(lambda ch=False, c=cid, b=menu_btn: self.show_conversation_actions(c, b))

            row_layout.addWidget(title_btn, 1)
            row_layout.addWidget(menu_btn)

            item.setSizeHint(row.sizeHint())
            self.conversation_list.addItem(item)
            self.conversation_list.setItemWidget(item, row)

    def filter_conversations(self, text):
        query = text.strip().lower()
        if not query:
            self.display_conversations(self.conversation_rows)
            return

        filtered = [c for c in self.conversation_rows if query in (c.get("title") or "").lower()]
        self.display_conversations(filtered)

    def switch_to_conversation(self, conversation_id):
        self.active_conversation_id = conversation_id
        messages = self.get_conversation_messages(conversation_id)

        # Clear existing bubbles
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Populate with conversation messages
        for msg in messages:
            speaker = "YOU" if msg.get("role") == "user" else "ZORIN"
            self.add_message(speaker, msg.get("content", ""), refresh_history=False)

        title = f"Conversation #{conversation_id}"
        for c in self.conversation_rows:
            if c.get("id") == conversation_id and c.get("title"):
                title = c["title"]
                break

        self.chat_title.setText(f"✧ {title.upper()}")
        self.conversation_switched.emit(conversation_id)

    def get_or_create_active_conversation_id(self) -> int:
        if self.active_conversation_id is not None:
            return self.active_conversation_id
        if self.conversation_rows:
            self.active_conversation_id = self.conversation_rows[0]["id"]
            return self.active_conversation_id
        db = Database()
        cid = db.create_conversation(title="New Conversation")
        self.active_conversation_id = cid
        return cid

    def rename_current_conversation(self):
        cid = self.get_or_create_active_conversation_id()
        self.rename_conversation(cid)

    def edit_current_conversation(self):
        """Allows editing conversation title or details."""
        cid = self.get_or_create_active_conversation_id()
        current_title = "Conversation"
        for c in self.conversation_rows:
            if c.get("id") == cid:
                current_title = c.get("title") or current_title
                break

        new_title, ok = QInputDialog.getText(
            self, "Edit Conversation Title", "Edit conversation title:", text=current_title
        )
        if ok and new_title.strip():
            conn = self.get_database_connection()
            try:
                conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title.strip(), cid))
                conn.commit()
            finally:
                conn.close()
            self.chat_title.setText(f"✧ {new_title.strip().upper()}")
            self.load_conversations()

    def delete_current_conversation(self):
        cid = self.get_or_create_active_conversation_id()
        self.delete_conversation(cid)

    def show_conversation_actions(self, conversation_id, button):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #19142A;
                color: #F5F3FF;
                border: 1px solid #604C91;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #60408A;
            }
        """)

        rename_action = QAction("✎  Rename", self)
        rename_action.triggered.connect(lambda: self.rename_conversation(conversation_id))
        menu.addAction(rename_action)

        edit_action = QAction("✏  Edit Title", self)
        edit_action.triggered.connect(lambda: self.rename_conversation(conversation_id))
        menu.addAction(edit_action)

        delete_action = QAction("🗑  Delete", self)
        delete_action.triggered.connect(lambda: self.delete_conversation(conversation_id))
        menu.addAction(delete_action)

        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def rename_conversation(self, conversation_id):
        current_title = "Conversation"
        for c in self.conversation_rows:
            if c["id"] == conversation_id:
                current_title = c.get("title") or current_title
                break

        new_title, ok = QInputDialog.getText(
            self, "Rename Conversation", "New title:", text=current_title
        )
        if ok and new_title.strip():
            conn = self.get_database_connection()
            try:
                conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title.strip(), conversation_id))
                conn.commit()
            finally:
                conn.close()
            if self.active_conversation_id == conversation_id:
                self.chat_title.setText(f"✧ {new_title.strip().upper()}")
            self.load_conversations()

    def delete_conversation(self, conversation_id):
        reply = QMessageBox.question(
            self, "Delete Conversation",
            "Are you sure you want to delete this conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn = self.get_database_connection()
            try:
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                conn.commit()
            finally:
                conn.close()

            if self.active_conversation_id == conversation_id:
                self.new_chat()
            else:
                self.load_conversations()

    def open_selected_conversation(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid:
            self.switch_to_conversation(cid)

    def new_chat(self):
        self.active_conversation_id = None
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.chat_title.setText("✧ NEW CONVERSATION")
        self.add_message("ZORIN", "Fresh conversation ready. How can I help you? ✨", refresh_history=False)
        self.new_conversation_requested.emit()

    # ==========================================
    # VOICE SETTINGS INTEGRATION
    # ==========================================

    def on_voice_selection_changed(self, index):
        if self.voice_combo is None:
            return
        voice_name = self.voice_combo.itemData(index)
        try:
            set_voice_preference(voice_name)
            label = get_voice_gender(voice_name)
            self.description.setText(f"{label.title()} voice saved ({voice_name}). Ready for conversation.")
            print(f"ZORIN: Voice preference updated: {voice_name} ({label}).")
        except Exception as error:
            QMessageBox.warning(self, "VOICE SETTING", f"Unable to save voice preference.\n\n{error}")

    def set_voice_selection(self, gender):
        if self.voice_combo is None:
            return
        index = 1 if str(gender).lower() == "female" else 0
        self.voice_combo.blockSignals(True)
        self.voice_combo.setCurrentIndex(index)
        self.voice_combo.blockSignals(False)

    # ==========================================
    # MEMORY DASHBOARD
    # ==========================================

    def open_memory_dashboard(self):
        try:
            from desktop.memory_ui import MemoryDashboard
            if self.memory_dashboard is None:
                self.memory_dashboard = MemoryDashboard(self)
            else:
                self.memory_dashboard.refresh_all()
            self.memory_dashboard.show()
            self.memory_dashboard.raise_()
            self.memory_dashboard.activateWindow()
        except Exception as error:
            QMessageBox.critical(self, "ZORIN MEMORY ERROR", f"Unable to open Memory Center.\n\n{error}")

    def open_device_dashboard(self):
        try:
            from desktop.device_ui import DeviceDashboard
            if self.device_dashboard is None:
                self.device_dashboard = DeviceDashboard(self)
            else:
                self.device_dashboard.refresh_all()
            self.device_dashboard.show()
            self.device_dashboard.raise_()
            self.device_dashboard.activateWindow()
        except Exception as error:
            QMessageBox.critical(self, "ZORIN DEVICE ERROR", f"Unable to open Device Center.\n\n{error}")

    # ==========================================
    # STATUS & MESSAGES
    # ==========================================

    def update_status(self, state, description=""):
        self.robot.set_state(state)
        self.status.setText(state.upper())
        self.description.setText(description)
        self.connection.setText("● " + state.upper())
        if state in ("speaking", "listening"):
            self.set_voice_active(True)
        elif state in ("idle", "ready"):
            self.set_voice_active(False)

    def add_message(self, speaker, message, refresh_history=True):
        bubble = QFrame()
        if speaker.upper() == "ZORIN":
            background = "#292044"
            color = "#D8B4FE"
        else:
            background = "#173047"
            color = "#67E8F9"

        bubble.setStyleSheet(f"""
            QFrame {{
                background: {background};
                border: 1px solid #604C91;
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(bubble)
        name = QLabel(speaker.upper())
        name.setStyleSheet(f"color: {color}; font-weight: bold; border: none;")

        text = QLabel(str(message))
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text.setStyleSheet("background: transparent; border: none; font-size: 13px;")

        layout.addWidget(name)
        layout.addWidget(text)

        # Message context menu for Edit, Copy, Delete on speech bubbles
        bubble.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        bubble.customContextMenuRequested.connect(
            lambda pos, b=bubble, t=text, s=speaker: self.show_message_menu(b, pos, t, s)
        )

        self.chat_layout.addWidget(bubble)

        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
        )

        if refresh_history:
            QTimer.singleShot(250, self.load_conversations)

    def show_message_menu(self, bubble, pos, text_label, speaker):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #19142A;
                color: #F5F3FF;
                border: 1px solid #604C91;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #60408A;
            }
        """)

        copy_action = QAction("📋  Copy Text", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(text_label.text()))
        menu.addAction(copy_action)

        edit_action = QAction("✏  Edit Message", self)
        def do_edit():
            new_text, ok = QInputDialog.getMultiLineText(
                self, "Edit Message", "Edit message text:", text_label.text()
            )
            if ok and new_text.strip():
                old_text = text_label.text()
                text_label.setText(new_text.strip())
                if self.active_conversation_id:
                    try:
                        conn = self.get_database_connection()
                        conn.execute(
                            "UPDATE messages SET content = ? WHERE id = (SELECT id FROM messages WHERE conversation_id = ? AND content = ? LIMIT 1)",
                            (new_text.strip(), self.active_conversation_id, old_text)
                        )
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
        edit_action.triggered.connect(do_edit)
        menu.addAction(edit_action)

        delete_action = QAction("🗑  Delete Message", self)
        def do_delete():
            confirm = QMessageBox.question(
                self, "Delete Message", "Delete this message bubble?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                old_text = text_label.text()
                if self.active_conversation_id:
                    try:
                        conn = self.get_database_connection()
                        conn.execute(
                            "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE conversation_id = ? AND content = ? LIMIT 1)",
                            (self.active_conversation_id, old_text)
                        )
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                bubble.deleteLater()
        delete_action.triggered.connect(do_delete)
        menu.addAction(delete_action)

        menu.exec(bubble.mapToGlobal(pos))


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = ZorinWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
