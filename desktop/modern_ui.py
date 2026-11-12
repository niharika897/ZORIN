import sys
import math
import random

from datetime import datetime, date, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QMessageBox,
    QLineEdit, QListWidget, QListWidgetItem,
    QInputDialog, QMenu, QComboBox
)

from PySide6.QtCore import (
    Qt, QTimer, QPointF, QRectF, Signal
)

from config.settings import (
    get_voice_preference,
    set_voice_preference,
    get_voice_gender,
)

from PySide6.QtGui import (
    QPainter, QColor, QPen,
    QLinearGradient, QRadialGradient,
    QFont, QAction
)


class RobotWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.setMinimumSize(400, 480)
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

        for particle in self.particles:
            particle[1] -= 0.002

            if particle[1] < 0:
                particle[1] = 1

        self.update()

    def set_state(self, state):
        self.state = state.lower()
        self.update()

    def glow(self, painter, x, y, radius, color):
        gradient = QRadialGradient(x, y, radius)

        gradient.setColorAt(0, QColor(color))

        gradient.setColorAt(
            1,
            QColor(
                color.red(),
                color.green(),
                color.blue(),
                0
            )
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        painter.drawEllipse(
            QPointF(x, y),
            radius,
            radius
        )

    def paintEvent(self, event):

        p = QPainter(self)

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        p.fillRect(self.rect(), QColor("#100D22"))

        # Floating particles
        for x, y, size in self.particles:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(190, 130, 255, 130))

            p.drawEllipse(
                QPointF(x * w, y * h),
                size,
                size
            )

        # Background glow
        self.glow(
            p, cx, cy, 190,
            QColor(120, 50, 255, 75)
        )

        # Holographic rings
        for i in range(3):

            p.save()
            p.translate(cx, cy - 10)

            p.rotate(
                self.t * (1 if i % 2 == 0 else -1)
            )

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

        # Shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 100))

        p.drawEllipse(
            QRectF(-90, 150, 180, 25)
        )

        # Body
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
            if self.state == "speaking"
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
            QRectF(0, h - 65, w, 30),
            Qt.AlignmentFlag.AlignCenter,
            "Z O R I N"
        )

        p.setPen(QColor("#A5A0BD"))
        p.setFont(QFont("Segoe UI", 9))

        p.drawText(
            QRectF(0, h - 38, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "YOUR PERSONAL AI COMPANION"
        )


class ZorinWindow(QMainWindow):

    stop_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ZORIN AI")
        self.resize(1450, 850)
        self.setMinimumSize(1100, 700)

        self.memory_dashboard = None

        self.active_conversation_id = None
        self.conversation_rows = []

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
                padding: 10px 15px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #60408A;
            }

            QPushButton#stop {
                background: #581C36;
                border: 1px solid #EC4899;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QLineEdit {
                background: #201B35;
                color: white;
                border: 1px solid #493477;
                border-radius: 10px;
                padding: 10px;
            }

            QListWidget {
                background: transparent;
                color: #E9D5FF;
                border: none;
                outline: none;
            }

            QListWidget::item {
                background: #201B35;
                border-radius: 9px;
                padding: 4px;
                margin: 3px 0;
            }

            QListWidget::item:selected {
                background: #493477;
                border: 1px solid #A78BFA;
            }

            QListWidget::item:hover {
                background: #332750;
            }
        """)

        self.build_interface()
        self.load_conversations()

    # ==========================================
    # DATABASE
    # ==========================================

    def get_database_connection(self):

        from memory.database import Database

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

        finally:
            connection.close()

    # ==========================================
    # MAIN INTERFACE
    # ==========================================

    def build_interface(self):

        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)

        main.setContentsMargins(22, 18, 22, 18)
        main.setSpacing(16)

        # HEADER
        header = QHBoxLayout()

        logo = QLabel("✦ ZORIN")

        logo.setFont(
            QFont("Segoe UI", 25, QFont.Weight.Bold)
        )

        logo.setStyleSheet("color: #C084FC;")

        tagline = QLabel("YOUR PERSONAL AI UNIVERSE")

        tagline.setStyleSheet("color: #A5A0BD;")

        # MEMORY BUTTON IN HEADER
        self.memory_button = QPushButton("🧠 MEMORY")
        self.memory_button.setFixedHeight(42)

        self.memory_button.clicked.connect(
            self.open_memory_dashboard
        )

        # VOICE SELECTOR
        self.voice_combo = QComboBox()
        self.voice_combo.addItem("MALE VOICE", "Puck")
        self.voice_combo.addItem("FEMALE VOICE", "Aoede")
        self.voice_combo.setFixedSize(150, 42)
        self.voice_combo.setToolTip(
            "Choose ZORIN's speaking voice"
        )
        saved_voice = get_voice_preference()
        self.voice_combo.setCurrentIndex(
            1 if saved_voice == "Aoede" else 0
        )
        self.voice_combo.currentIndexChanged.connect(
            self.on_voice_selection_changed
        )

        # HISTORY BUTTON
        self.history_button = QPushButton("☰")
        self.history_button.setFixedSize(45, 42)

        self.history_button.setToolTip(
            "Conversation History"
        )

        self.history_button.clicked.connect(
            self.toggle_history
        )

        header.addWidget(logo)
        header.addWidget(tagline)
        header.addStretch()
        header.addWidget(self.voice_combo)
        header.addWidget(self.memory_button)
        header.addWidget(self.history_button)

        main.addLayout(header)

        # MAIN PANELS
        content = QHBoxLayout()
        content.setSpacing(18)

        # ROBOT PANEL
        robot_panel = QFrame()
        robot_panel.setObjectName("panel")

        rl = QVBoxLayout(robot_panel)

        title = QLabel("MEET YOUR ASSISTANT")

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.robot = RobotWidget()

        self.status = QLabel("ZORIN IS GETTING READY")

        self.status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status.setFont(
            QFont("Segoe UI", 12, QFont.Weight.Bold)
        )

        self.description = QLabel(
            "Initializing your AI companion..."
        )

        self.description.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        rl.addWidget(title)
        rl.addWidget(self.robot, 1)
        rl.addWidget(self.status)
        rl.addWidget(self.description)

        # CONVERSATION PANEL
        chat_panel = QFrame()
        chat_panel.setObjectName("panel")

        chat_main = QHBoxLayout(chat_panel)

        chat_main.setContentsMargins(10, 12, 10, 12)
        chat_main.setSpacing(12)

        # HISTORY SIDEBAR
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(245)

        self.sidebar.setStyleSheet("""
            QFrame {
                background: #100E20;
                border: 1px solid #33264F;
                border-radius: 15px;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)

        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(10)

        sidebar_title = QLabel("YOUR CHATS")

        sidebar_title.setFont(
            QFont("Segoe UI", 13, QFont.Weight.Bold)
        )

        sidebar_title.setStyleSheet(
            "color: #D8B4FE; border: none;"
        )

        self.new_chat_button = QPushButton("+ New Conversation")

        self.new_chat_button.clicked.connect(
            self.new_chat
        )

        self.search_conversations = QLineEdit()

        self.search_conversations.setPlaceholderText(
            "⌕ Search conversations..."
        )

        self.search_conversations.textChanged.connect(
            self.filter_conversations
        )

        self.conversation_list = QListWidget()

        self.conversation_list.itemClicked.connect(
            self.open_selected_conversation
        )

        sidebar_layout.addWidget(sidebar_title)
        sidebar_layout.addWidget(self.new_chat_button)
        sidebar_layout.addWidget(self.search_conversations)
        sidebar_layout.addWidget(self.conversation_list, 1)

        # CHAT DISPLAY
        chat_area = QWidget()

        chat_layout = QVBoxLayout(chat_area)

        chat_layout.setContentsMargins(5, 0, 5, 0)
        chat_layout.setSpacing(12)

        self.chat_title = QLabel("✧ CONVERSATION")

        self.chat_title.setFont(
            QFont("Segoe UI", 16, QFont.Weight.Bold)
        )

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.chat_widget = QWidget()

        self.chat_layout = QVBoxLayout(
            self.chat_widget
        )

        self.chat_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.chat_layout.setSpacing(14)

        self.scroll.setWidget(self.chat_widget)

        chat_layout.addWidget(self.chat_title)
        chat_layout.addWidget(self.scroll, 1)

        chat_main.addWidget(self.sidebar)
        chat_main.addWidget(chat_area, 1)

        # HIDDEN BY DEFAULT
        self.sidebar.hide()

        content.addWidget(robot_panel, 5)
        content.addWidget(chat_panel, 8)

        main.addLayout(content, 1)

        # FOOTER
        footer = QHBoxLayout()

        settings = QPushButton("⚙ SETTINGS")

        stop = QPushButton("⏹ STOP ZORIN")
        stop.setObjectName("stop")

        stop.clicked.connect(
            self.stop_requested.emit
        )

        footer.addWidget(settings)
        footer.addStretch()
        footer.addWidget(stop)

        main.addLayout(footer)

        self.add_message(
            "ZORIN",
            "Hello! I'm ZORIN. I'm ready to assist you. ✨"
        )

    # ==========================================
    # SHOW / HIDE HISTORY
    # ==========================================

    def toggle_history(self):

        if self.sidebar.isVisible():

            self.sidebar.hide()

            self.history_button.setToolTip(
                "Show Conversation History"
            )

        else:

            self.sidebar.show()

            self.history_button.setToolTip(
                "Hide Conversation History"
            )

            self.load_conversations()

    # ==========================================
    # CONVERSATION HISTORY
    # ==========================================

    def load_conversations(self):

        try:

            self.conversation_rows = self.get_conversations()

            self.display_conversations(
                self.conversation_rows
            )

        except Exception as error:

            print(
                "CONVERSATION HISTORY ERROR:",
                error
            )

    # ==========================================
    # DISPLAY CONVERSATIONS WITH THREE-DOT MENU
    # ==========================================

    def display_conversations(self, conversations):

        self.conversation_list.clear()

        for conversation in conversations:

            conversation_id = conversation["id"]

            title = (
                conversation.get("title")
                or "New Conversation"
            )

            item = QListWidgetItem()

            item.setData(
                Qt.ItemDataRole.UserRole,
                conversation_id
            )

            # ROW WIDGET
            row = QWidget()

            row_layout = QHBoxLayout(row)

            row_layout.setContentsMargins(5, 3, 5, 3)
            row_layout.setSpacing(5)

            # CONVERSATION TITLE BUTTON
            title_button = QPushButton(title)

            title_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            title_button.setToolTip(title)

            title_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #E9D5FF;
                    border: none;
                    text-align: left;
                    padding: 7px;
                    font-weight: normal;
                }

                QPushButton:hover {
                    background: #332750;
                    color: white;
                }
            """)

            # THREE-DOT BUTTON
            menu_button = QPushButton("⋯")

            menu_button.setFixedSize(35, 35)

            menu_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            menu_button.setToolTip(
                "Conversation options"
            )

            menu_button.setStyleSheet("""
                QPushButton {
                    background: #292044;
                    color: #D8B4FE;
                    font-size: 22px;
                    border: 1px solid #604C91;
                    border-radius: 8px;
                    padding: 0px;
                }

                QPushButton:hover {
                    background: #7252CF;
                    color: white;
                }
            """)

            # OPEN CONVERSATION
            title_button.clicked.connect(
                lambda checked=False, current=item:
                self.open_selected_conversation(current)
            )

            # OPEN THREE-DOT MENU
            menu_button.clicked.connect(
                lambda checked=False,
                cid=conversation_id,
                btn=menu_button:
                self.show_conversation_actions(cid, btn)
            )

            row_layout.addWidget(title_button, 1)
            row_layout.addWidget(menu_button)

            item.setSizeHint(row.sizeHint())

            self.conversation_list.addItem(item)

            self.conversation_list.setItemWidget(
                item,
                row
            )

    # ==========================================
    # SEARCH CONVERSATIONS
    # ==========================================

    def filter_conversations(self, text):

        search = text.strip().lower()

        if not search:

            self.display_conversations(
                self.conversation_rows
            )

            return

        filtered = []

        for conversation in self.conversation_rows:

            title = str(
                conversation.get("title", "")
            ).lower()

            if search in title:
                filtered.append(conversation)

        self.display_conversations(filtered)

    # ==========================================
    # OPEN CONVERSATION
    # ==========================================

    def open_selected_conversation(self, item):

        conversation_id = item.data(
            Qt.ItemDataRole.UserRole
        )

        if conversation_id is None:
            return

        self.active_conversation_id = conversation_id

        try:

            messages = self.get_conversation_messages(
                conversation_id
            )

            self.clear_chat()

            conversation = next(
                (
                    c for c in self.conversation_rows
                    if c["id"] == conversation_id
                ),
                None
            )

            if conversation:

                self.chat_title.setText(
                    conversation.get(
                        "title",
                        "CONVERSATION"
                    )
                )

            for message in messages:

                role = message["role"].lower()

                speaker = (
                    "ZORIN"
                    if role in ("assistant", "zorin", "ai")
                    else "YOU"
                )

                self.add_message(
                    speaker,
                    message["content"],
                    refresh_history=False
                )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Conversation Error",
                str(error)
            )

    # ==========================================
    # THREE-DOT MENU ACTIONS
    # ==========================================

    def show_conversation_actions(
        self,
        conversation_id,
        button
    ):

        menu = QMenu(self)

        rename_action = QAction("✏ Rename", self)
        delete_action = QAction("🗑 Delete", self)

        menu.addAction(rename_action)
        menu.addAction(delete_action)

        selected_action = menu.exec(
            button.mapToGlobal(
                button.rect().bottomRight()
            )
        )

        if selected_action == rename_action:

            self.rename_conversation(conversation_id)

        elif selected_action == delete_action:

            self.delete_conversation(conversation_id)

    # ==========================================
    # RENAME CONVERSATION
    # ==========================================

    def rename_conversation(self, conversation_id):

        conversation = next(
            (
                c for c in self.conversation_rows
                if c["id"] == conversation_id
            ),
            None
        )

        if not conversation:
            return

        new_title, accepted = QInputDialog.getText(
            self,
            "Rename Conversation",
            "Enter a new conversation name:",
            text=conversation.get("title", "")
        )

        if not accepted:
            return

        new_title = new_title.strip()

        if not new_title:
            return

        connection = self.get_database_connection()

        try:

            connection.execute(
                """
                UPDATE conversations
                SET title = ?
                WHERE id = ?
                """,
                (new_title, conversation_id)
            )

            connection.commit()

        finally:
            connection.close()

        self.load_conversations()

        if self.active_conversation_id == conversation_id:

            self.chat_title.setText(new_title)

    # ==========================================
    # DELETE CONVERSATION
    # ==========================================

    def delete_conversation(self, conversation_id):

        answer = QMessageBox.question(
            self,
            "Delete Conversation",
            "Are you sure you want to delete this conversation?\n\n"
            "Its saved messages will also be deleted.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = self.get_database_connection()

        try:

            connection.execute(
                """
                DELETE FROM conversations
                WHERE id = ?
                """,
                (conversation_id,)
            )

            connection.commit()

        finally:
            connection.close()

        if self.active_conversation_id == conversation_id:

            self.active_conversation_id = None

            self.clear_chat()

            self.chat_title.setText(
                "✧ CONVERSATION"
            )

        self.load_conversations()

    # ==========================================
    # NEW CONVERSATION
    # ==========================================

    def new_chat(self):

        self.active_conversation_id = None

        self.clear_chat()

        self.chat_title.setText(
            "✧ NEW CONVERSATION"
        )

        self.search_conversations.clear()

        self.add_message(
            "ZORIN",
            "A fresh conversation. What would you like to talk about? ✨",
            refresh_history=False
        )

    # ==========================================
    # CHAT DISPLAY
    # ==========================================

    def clear_chat(self):

        while self.chat_layout.count():

            item = self.chat_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def add_message(
        self,
        speaker,
        message,
        refresh_history=True
    ):

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

        name.setStyleSheet(
            f"color: {color}; font-weight: bold; border: none;"
        )

        text = QLabel(str(message))
        text.setWordWrap(True)

        text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        text.setStyleSheet(
            "background: transparent; border: none;"
        )

        layout.addWidget(name)
        layout.addWidget(text)

        self.chat_layout.addWidget(bubble)

        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
        )

        if refresh_history:

            QTimer.singleShot(
                250,
                self.load_conversations
            )

    # ==========================================
    # MEMORY CENTER
    # ==========================================

    def on_voice_selection_changed(self, index):
        """Persist the selected voice for the next Gemini session."""
        if self.voice_combo is None:
            return

        voice_name = self.voice_combo.itemData(index)

        try:
            set_voice_preference(voice_name)
            label = get_voice_gender(voice_name)
            self.description.setText(
                f"{label.title()} voice saved. It will be used "
                "when the next voice session starts. If ZORIN is "
                "currently talking, let this conversation finish first."
            )
            print(
                f"ZORIN: Manual voice selection saved: {voice_name} ({label})."
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                "VOICE SETTING",
                f"Unable to save voice preference.\\n\\n{error}"
            )

    def set_voice_selection(self, gender):
        """Synchronize the selector after a spoken voice-change command."""
        if self.voice_combo is None:
            return

        index = 1 if str(gender).lower() == "female" else 0
        self.voice_combo.blockSignals(True)
        self.voice_combo.setCurrentIndex(index)
        self.voice_combo.blockSignals(False)

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

            QMessageBox.critical(
                self,
                "ZORIN MEMORY ERROR",
                f"Unable to open Memory Center.\n\n{error}"
            )

    # ==========================================
    # STATUS
    # ==========================================

    def update_status(self, state, description=""):

        self.robot.set_state(state)

        self.status.setText(state.upper())

        self.description.setText(description)


def main():

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    window = ZorinWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()