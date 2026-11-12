import sys
import math
import random

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QGraphicsDropShadowEffect
)

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QFont
)


# ==========================================
# ANIMATED ROBOT CHARACTER
# ==========================================

class RobotWidget(QWidget):

    def __init__(self):

        super().__init__()

        self.setMinimumSize(400, 480)

        self.time = 0
        self.state = "standby"

        self.particles = [
            (
                random.randint(0, 500),
                random.randint(0, 500),
                random.uniform(0.3, 1.5)
            )
            for _ in range(45)
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def animate(self):

        self.time += 0.04

        self.update()

    def set_state(self, state):

        self.state = state.lower()
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        w = self.width()
        h = self.height()

        cx = w / 2
        cy = h / 2

        t = self.time

        # Background glow

        glow = QRadialGradient(
            QPointF(cx, cy),
            230
        )

        glow.setColorAt(0, QColor(83, 42, 160, 65))
        glow.setColorAt(0.5, QColor(35, 40, 105, 25))
        glow.setColorAt(1, QColor(8, 10, 25, 0))

        painter.fillRect(
            self.rect(),
            QBrush(glow)
        )

        # Floating particles

        for x, y, speed in self.particles:

            px = (x + math.sin(t * speed + y) * 15) % w

            py = (y - t * 12 * speed) % h

            painter.setPen(Qt.PenStyle.NoPen)

            painter.setBrush(
                QColor(155, 115, 255, 120)
            )

            painter.drawEllipse(
                QPointF(px, py),
                2,
                2
            )

        # Rotating holographic rings

        painter.save()

        painter.translate(cx, cy + 15)
        painter.rotate(t * 12)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        pen = QPen(
            QColor(130, 90, 255, 85),
            2
        )

        pen.setStyle(Qt.PenStyle.DashLine)

        painter.setPen(pen)

        painter.drawEllipse(
            QRectF(-150, -150, 300, 300)
        )

        painter.rotate(-t * 24)

        painter.setPen(
            QPen(
                QColor(30, 210, 255, 100),
                2
            )
        )

        painter.drawEllipse(
            QRectF(-170, -125, 340, 250)
        )

        painter.restore()

        # Robot floating movement

        floating = math.sin(t * 2) * 7

        robot_y = cy + floating

        # Robot outer glow

        robot_glow = QRadialGradient(
            QPointF(cx, robot_y),
            135
        )

        robot_glow.setColorAt(
            0, QColor(135, 75, 255, 100)
        )

        robot_glow.setColorAt(
            1, QColor(80, 40, 180, 0)
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(robot_glow))

        painter.drawEllipse(
            QRectF(cx - 135, robot_y - 145, 270, 290)
        )

        # Antenna

        painter.setPen(
            QPen(QColor("#A78BFA"), 4)
        )

        painter.drawLine(
            QPointF(cx, robot_y - 104),
            QPointF(cx, robot_y - 132)
        )

        antenna_glow = QColor(
            "#FF75E8"
        )

        painter.setBrush(antenna_glow)

        painter.drawEllipse(
            QPointF(cx, robot_y - 139),
            7,
            7
        )

        # Robot head

        head = QRectF(
            cx - 92,
            robot_y - 105,
            184,
            175
        )

        head_gradient = QLinearGradient(
            head.topLeft(),
            head.bottomRight()
        )

        head_gradient.setColorAt(
            0, QColor("#403B78")
        )

        head_gradient.setColorAt(
            0.5, QColor("#22294E")
        )

        head_gradient.setColorAt(
            1, QColor("#11182F")
        )

        painter.setBrush(QBrush(head_gradient))

        painter.setPen(
            QPen(QColor("#A78BFA"), 3)
        )

        painter.drawRoundedRect(
            head,
            55,
            55
        )

        # Side ear panels

        painter.setBrush(
            QColor("#6251B8")
        )

        painter.drawRoundedRect(
            QRectF(cx - 105, robot_y - 48, 17, 65),
            7,
            7
        )

        painter.drawRoundedRect(
            QRectF(cx + 88, robot_y - 48, 17, 65),
            7,
            7
        )

        # Face panel

        face = QRectF(
            cx - 76,
            robot_y - 86,
            152,
            130
        )

        painter.setBrush(
            QColor("#10182E")
        )

        painter.setPen(
            QPen(QColor("#6559B9"), 2)
        )

        painter.drawRoundedRect(
            face,
            42,
            42
        )

        # Eye animation

        blink = abs(math.sin(t * 0.8))

        eye_height = 19

        if blink > 0.985:

            eye_height = 3

        if self.state == "thinking":

            eye_height = 9

        if self.state == "speaking":

            eye_height = 23

        eye_color = QColor("#55E7FF")

        if self.state == "thinking":

            eye_color = QColor("#C18BFF")

        if self.state == "speaking":

            eye_color = QColor("#FF78DF")

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(eye_color)

        painter.drawRoundedRect(
            QRectF(
                cx - 49,
                robot_y - 43,
                34,
                eye_height
            ),
            10,
            10
        )

        painter.drawRoundedRect(
            QRectF(
                cx + 15,
                robot_y - 43,
                34,
                eye_height
            ),
            10,
            10
        )

        # Eye glow

        painter.setPen(
            QPen(
                QColor(85, 231, 255, 100),
                2
            )
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawRoundedRect(
            QRectF(cx - 52, robot_y - 46, 40, 26),
            12,
            12
        )

        painter.drawRoundedRect(
            QRectF(cx + 12, robot_y - 46, 40, 26),
            12,
            12
        )

        # Mouth animation

        mouth_width = 24

        mouth_height = 4

        if self.state == "speaking":

            mouth_height = (
                5 + abs(math.sin(t * 9)) * 15
            )

        if self.state == "listening":

            mouth_width = 15

        painter.setBrush(
            QColor("#FF75D8")
        )

        painter.drawRoundedRect(
            QRectF(
                cx - mouth_width / 2,
                robot_y + 5,
                mouth_width,
                mouth_height
            ),
            8,
            8
        )

        # Robot neck

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(
            QColor("#5550A0")
        )

        painter.drawRoundedRect(
            QRectF(
                cx - 28,
                robot_y + 65,
                56,
                22
            ),
            8,
            8
        )

        # Robot body

        body = QRectF(
            cx - 76,
            robot_y + 80,
            152,
            125
        )

        body_gradient = QLinearGradient(
            body.topLeft(),
            body.bottomRight()
        )

        body_gradient.setColorAt(
            0, QColor("#514B91")
        )

        body_gradient.setColorAt(
            1, QColor("#171D3A")
        )

        painter.setBrush(
            QBrush(body_gradient)
        )

        painter.setPen(
            QPen(QColor("#9C83FF"), 3)
        )

        painter.drawRoundedRect(
            body,
            40,
            40
        )

        # Chest energy core

        core_glow = 8 + abs(math.sin(t * 3)) * 5

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(
            QColor("#6B55F5")
        )

        painter.drawEllipse(
            QPointF(cx, robot_y + 137),
            core_glow + 12,
            core_glow + 12
        )

        painter.setBrush(
            QColor("#6CF0FF")
        )

        painter.drawEllipse(
            QPointF(cx, robot_y + 137),
            core_glow / 2,
            core_glow / 2
        )

        painter.end()


# ==========================================
# MAIN APPLICATION
# ==========================================

class ZorinWindow(QMainWindow):

    stop_requested = Signal()

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ZORIN AI")

        self.resize(1400, 850)

        self.setMinimumSize(1050, 700)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #080A18;
            }

            QWidget {
                color: white;
                font-family: Segoe UI;
            }

            QFrame#panel {
                background-color: #12152B;
                border: 1px solid #29264D;
                border-radius: 22px;
            }

            QLabel {
                background: transparent;
            }

            QPushButton {
                border: none;
                border-radius: 12px;
                padding: 13px;
                font-weight: bold;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self.create_ui()

    # ======================================
    # BUILD UI
    # ======================================

    def create_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        main = QVBoxLayout(central)

        main.setContentsMargins(30, 25, 30, 25)

        main.setSpacing(22)

        self.create_header(main)

        content = QHBoxLayout()

        content.setSpacing(22)

        self.create_robot_panel(content)

        self.create_conversation_panel(content)

        main.addLayout(content, 1)

        self.create_footer(main)

    # ======================================
    # HEADER
    # ======================================

    def create_header(self, layout):

        header = QHBoxLayout()

        title = QLabel("ZORIN")

        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 7px;
            color: #C4A5FF;
        """)

        header.addWidget(title)

        tagline = QLabel(
            "YOUR INTELLIGENT PERSONAL COMPANION"
        )

        tagline.setStyleSheet("""
            color: #8586B5;
            font-size: 10px;
            letter-spacing: 3px;
        """)

        header.addWidget(tagline)

        header.addStretch()

        self.status = QLabel(
            "● INITIALIZING"
        )

        self.status.setStyleSheet("""
            background: #282047;
            color: #D5B8FF;
            padding: 12px 20px;
            border-radius: 15px;
            font-weight: bold;
        """)

        header.addWidget(self.status)

        layout.addLayout(header)

    # ======================================
    # ROBOT PANEL
    # ======================================

    def create_robot_panel(self, layout):

        panel = QFrame()

        panel.setObjectName("panel")

        box = QVBoxLayout(panel)

        box.setContentsMargins(20, 20, 20, 20)

        heading = QLabel("MEET YOUR ASSISTANT")

        heading.setStyleSheet("""
            color: #B9A1FF;
            font-size: 12px;
            letter-spacing: 3px;
            font-weight: bold;
        """)

        box.addWidget(heading)

        self.robot = RobotWidget()

        box.addWidget(
            self.robot,
            1
        )

        self.robot_status = QLabel(
            "ZORIN IS INITIALIZING"
        )

        self.robot_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.robot_status.setStyleSheet("""
            color: #D5B5FF;
            font-size: 17px;
            font-weight: bold;
            letter-spacing: 3px;
        """)

        box.addWidget(self.robot_status)

        self.robot_description = QLabel(
            "Preparing your AI companion..."
        )

        self.robot_description.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.robot_description.setStyleSheet("""
            color: #8586A9;
            font-size: 12px;
        """)

        box.addWidget(self.robot_description)

        layout.addWidget(panel, 5)

    # ======================================
    # CONVERSATION PANEL
    # ======================================

    def create_conversation_panel(self, layout):

        panel = QFrame()

        panel.setObjectName("panel")

        box = QVBoxLayout(panel)

        box.setContentsMargins(22, 22, 22, 22)

        heading = QLabel("CONVERSATION HISTORY")

        heading.setStyleSheet("""
            color: #C4A5FF;
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 2px;
        """)

        box.addWidget(heading)

        self.messages = QVBoxLayout()

        self.messages.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.message_container = QWidget()

        self.message_container.setLayout(
            self.messages
        )

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(True)

        self.scroll.setWidget(
            self.message_container
        )

        box.addWidget(self.scroll, 1)

        layout.addWidget(panel, 4)

    # ======================================
    # FOOTER
    # ======================================

    def create_footer(self, layout):

        footer = QHBoxLayout()

        self.gemini_status = QLabel(
            "● GEMINI CONNECTION: WAITING"
        )

        self.gemini_status.setStyleSheet("""
            color: #8586A9;
            font-size: 11px;
            letter-spacing: 1px;
        """)

        footer.addWidget(
            self.gemini_status
        )

        footer.addStretch()

        memory = QPushButton("MEMORY")

        memory.setStyleSheet("""
            background: #282047;
            color: #D5B8FF;
        """)

        settings = QPushButton("SETTINGS")

        settings.setStyleSheet("""
            background: #282047;
            color: #D5B8FF;
        """)

        stop = QPushButton("⏻  STOP ZORIN")

        stop.setStyleSheet("""
            background: #8F2453;
            color: white;
        """)

        stop.clicked.connect(
            self.stop_requested.emit
        )

        footer.addWidget(memory)

        footer.addWidget(settings)

        footer.addWidget(stop)

        layout.addLayout(footer)

    # ======================================
    # STATUS UPDATES
    # ======================================

    def update_status(self, state, description=""):

        self.status.setText(
            "● " + state.upper()
        )

        self.robot_status.setText(
            state.upper()
        )

        self.robot_description.setText(
            description
        )

        self.robot.set_state(state)

    # ======================================
    # ADD CONVERSATION MESSAGE
    # ======================================

    def add_message(self, speaker, message):

        bubble = QLabel(
            f"{speaker.upper()}\n\n{message}"
        )

        bubble.setWordWrap(True)

        bubble.setStyleSheet("""
            background-color: #242044;
            color: #E8DEFF;
            padding: 16px;
            border-radius: 14px;
            font-size: 13px;
        """)

        self.messages.addWidget(bubble)

        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
        )


# ==========================================
# RUN STANDALONE INTERFACE
# ==========================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ZorinWindow()

    window.show()

    sys.exit(app.exec())