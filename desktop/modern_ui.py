import sys
import math
import random

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QMessageBox
)

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QLinearGradient, QRadialGradient, QFont
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

        # Floating particles
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
        self.resize(1250, 820)
        self.setMinimumSize(950, 680)

        # Memory dashboard reference
        self.memory_dashboard = None

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
                padding: 13px 20px;
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
        """)

        self.build_interface()

    def build_interface(self):

        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)
        main.setContentsMargins(22, 18, 22, 18)
        main.setSpacing(16)

        # Header
        header = QHBoxLayout()

        logo = QLabel("✦ ZORIN")
        logo.setFont(
            QFont("Segoe UI", 25, QFont.Weight.Bold)
        )
        logo.setStyleSheet("color: #C084FC;")

        tagline = QLabel("YOUR PERSONAL AI UNIVERSE")
        tagline.setStyleSheet("color: #A5A0BD;")

        self.connection = QLabel("● INITIALIZING")

        header.addWidget(logo)
        header.addWidget(tagline)
        header.addStretch()
        header.addWidget(self.connection)

        main.addLayout(header)

        # Main panels
        content = QHBoxLayout()
        content.setSpacing(18)

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

        # Conversation panel
        chat_panel = QFrame()
        chat_panel.setObjectName("panel")

        cl = QVBoxLayout(chat_panel)

        chat_title = QLabel("✧ CONVERSATION")
        chat_title.setFont(
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

        cl.addWidget(chat_title)
        cl.addWidget(self.scroll, 1)

        content.addWidget(robot_panel, 5)
        content.addWidget(chat_panel, 6)

        main.addLayout(content, 1)

        # Footer
        footer = QHBoxLayout()

        self.memory_button = QPushButton("🧠 MEMORY")

        settings = QPushButton("⚙ SETTINGS")

        stop = QPushButton("⏻ STOP ZORIN")
        stop.setObjectName("stop")

        # Connect MEMORY button
        self.memory_button.clicked.connect(
            self.open_memory_dashboard
        )

        stop.clicked.connect(
            self.stop_requested.emit
        )

        footer.addWidget(self.memory_button)
        footer.addWidget(settings)
        footer.addStretch()
        footer.addWidget(stop)

        main.addLayout(footer)

        self.add_message(
            "ZORIN",
            "Hello! I'm ZORIN. I'm ready to assist you. ✨"
        )

    # ==========================================
    # MEMORY DASHBOARD INTEGRATION
    # ==========================================

    def open_memory_dashboard(self):

        try:

            from desktop.memory_ui import MemoryDashboard

            # Create dashboard only once
            if self.memory_dashboard is None:

                self.memory_dashboard = MemoryDashboard(self)

            else:

                # Refresh existing dashboard
                self.memory_dashboard.refresh_all()

            # Display dashboard
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

    def update_status(self, state, description=""):

        self.robot.set_state(state)

        self.status.setText(state.upper())
        self.description.setText(description)

        self.connection.setText(
            "● " + state.upper()
        )

    def add_message(self, speaker, message):

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
            f"color: {color}; font-weight: bold;"
        )

        text = QLabel(message)
        text.setWordWrap(True)

        layout.addWidget(name)
        layout.addWidget(text)

        self.chat_layout.addWidget(bubble)

        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
        )


def main():

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    window = ZorinWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()