import sys

from PySide6.QtCore import Qt
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
    QTextEdit,
    QComboBox,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QFormLayout,
)

from memory.memory_manager import MemoryManager


class MemoryDashboard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.memory = MemoryManager()

        self.core_memories = []
        self.long_memories = []
        self.selected_memory = None

        self.setWindowTitle("ZORIN - Memory Center")
        self.resize(1000, 720)
        self.setMinimumSize(800, 600)

        self.setStyleSheet("""
            QDialog {
                background-color: #10101c;
                color: #eeeeff;
            }

            QLabel {
                color: #eeeeff;
                font-size: 13px;
            }

            QTabWidget::pane {
                border: 1px solid #383452;
                background: #171629;
                border-radius: 8px;
            }

            QTabBar::tab {
                background: #24213b;
                color: #c9c4e8;
                padding: 12px 22px;
                margin-right: 4px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
            }

            QTabBar::tab:selected {
                background: #7958d6;
                color: white;
            }

            QPushButton {
                background-color: #7252cf;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 9px 16px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #9274ed;
            }

            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background: #24223a;
                color: white;
                border: 1px solid #484266;
                border-radius: 6px;
                padding: 8px;
            }

            QListWidget {
                background: #19182b;
                color: #eeeeff;
                border: 1px solid #383452;
                border-radius: 8px;
                padding: 6px;
            }

            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #34304b;
            }

            QListWidget::item:selected {
                background: #59439c;
            }

            QGroupBox {
                border: 1px solid #484266;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                color: #c7b6ff;
                font-weight: bold;
            }
        """)

        self.build_ui()
        self.refresh_all()

    # --------------------------------------------------
    # MAIN INTERFACE
    # --------------------------------------------------

    def build_ui(self):

        main_layout = QVBoxLayout(self)

        heading = QLabel("🧠  ZORIN MEMORY CENTER")

        heading.setStyleSheet("""
            font-size: 25px;
            font-weight: bold;
            color: #c7adff;
            padding: 12px;
        """)

        subtitle = QLabel(
            "Manage what ZORIN remembers about you."
        )

        subtitle.setStyleSheet(
            "color: #aaa3c9; padding-left: 14px;"
        )

        main_layout.addWidget(heading)
        main_layout.addWidget(subtitle)

        self.tabs = QTabWidget()

        self.build_core_tab()
        self.build_long_term_tab()
        self.build_search_tab()

        main_layout.addWidget(self.tabs)

        bottom = QHBoxLayout()

        refresh_button = QPushButton("↻ Refresh")
        refresh_button.clicked.connect(self.refresh_all)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        bottom.addWidget(refresh_button)
        bottom.addStretch()
        bottom.addWidget(close_button)

        main_layout.addLayout(bottom)

    # --------------------------------------------------
    # CORE MEMORY
    # --------------------------------------------------

    def build_core_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)

        description = QLabel(
            "Protected memories containing important facts, "
            "preferences and information about you."
        )

        description.setWordWrap(True)

        self.core_list = QListWidget()

        buttons = QHBoxLayout()

        add_button = QPushButton("+ Add Core Memory")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")

        add_button.clicked.connect(self.add_core_memory)

        edit_button.clicked.connect(
            lambda: self.edit_selected_memory("core")
        )

        delete_button.clicked.connect(
            lambda: self.delete_selected_memory("core")
        )

        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)

        layout.addWidget(description)
        layout.addWidget(self.core_list)
        layout.addLayout(buttons)

        self.tabs.addTab(page, "Core Memory")

    # --------------------------------------------------
    # LONG TERM MEMORY
    # --------------------------------------------------

    def build_long_term_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)

        description = QLabel(
            "Information ZORIN has learned and stored over time."
        )

        self.long_list = QListWidget()

        buttons = QHBoxLayout()

        add_button = QPushButton("+ Add Memory")
        edit_button = QPushButton("Edit")
        pin_button = QPushButton("Pin to Core")
        delete_button = QPushButton("Delete")

        add_button.clicked.connect(self.add_long_memory)

        edit_button.clicked.connect(
            lambda: self.edit_selected_memory("long")
        )

        pin_button.clicked.connect(
            self.pin_selected_memory
        )

        delete_button.clicked.connect(
            lambda: self.delete_selected_memory("long")
        )

        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(pin_button)
        buttons.addWidget(delete_button)

        layout.addWidget(description)
        layout.addWidget(self.long_list)
        layout.addLayout(buttons)

        self.tabs.addTab(page, "Long-term Memory")

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    def build_search_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)

        description = QLabel(
            "Search through ZORIN's stored memories."
        )

        search_row = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Search memories..."
        )

        search_button = QPushButton("Search")

        search_button.clicked.connect(
            self.search_memories
        )

        self.search_input.returnPressed.connect(
            self.search_memories
        )

        search_row.addWidget(self.search_input)
        search_row.addWidget(search_button)

        self.search_results = QListWidget()

        layout.addWidget(description)
        layout.addLayout(search_row)
        layout.addWidget(self.search_results)

        self.tabs.addTab(page, "Search")

    # --------------------------------------------------
    # NORMALIZE MEMORY RECORDS
    # --------------------------------------------------

    def to_dict(self, memory):

        if isinstance(memory, dict):
            return memory

        if hasattr(memory, "__dict__"):
            return vars(memory)

        return {}

    def memory_content(self, memory):

        data = self.to_dict(memory)

        return str(
            data.get("content")
            or data.get("memory")
            or data.get("text")
            or ""
        )

    def memory_id(self, memory):

        data = self.to_dict(memory)

        return data.get("id")

    # --------------------------------------------------
    # REFRESH ALL
    # --------------------------------------------------

    def refresh_all(self):

        try:

            self.core_memories = [
                self.to_dict(item)
                for item in self.memory.get_core_memories()
            ]

            self.long_memories = [
                self.to_dict(item)
                for item in self.memory.get_all_memories()
            ]

            self.populate_core_list()
            self.populate_long_list()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Memory Refresh Error",
                str(error)
            )

    # --------------------------------------------------
    # POPULATE LISTS
    # --------------------------------------------------

    def populate_core_list(self):

        self.core_list.clear()

        for memory in self.core_memories:

            content = self.memory_content(memory)

            item = QListWidgetItem(
                "🔒  " + content
            )

            item.setData(
                Qt.UserRole,
                memory
            )

            self.core_list.addItem(item)

    def populate_long_list(self):

        self.long_list.clear()

        for memory in self.long_memories:

            content = self.memory_content(memory)

            item = QListWidgetItem(
                "🧠  " + content
            )

            item.setData(
                Qt.UserRole,
                memory
            )

            self.long_list.addItem(item)

    # --------------------------------------------------
    # ADD MEMORY DIALOG
    # --------------------------------------------------

    def memory_input_dialog(self, title):

        dialog = QDialog(self)

        dialog.setWindowTitle(title)
        dialog.resize(480, 360)

        layout = QVBoxLayout(dialog)

        form = QFormLayout()

        content_input = QTextEdit()

        content_input.setPlaceholderText(
            "Enter the information ZORIN should remember..."
        )

        category_input = QComboBox()

        category_input.addItems([
            "personal",
            "preferences",
            "education",
            "career",
            "projects",
            "general",
        ])

        importance_input = QSpinBox()

        importance_input.setRange(1, 10)
        importance_input.setValue(5)

        form.addRow(
            "Memory:",
            content_input
        )

        form.addRow(
            "Category:",
            category_input
        )

        form.addRow(
            "Importance:",
            importance_input
        )

        layout.addLayout(form)

        buttons = QHBoxLayout()

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")

        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)

        layout.addLayout(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None

        content = content_input.toPlainText().strip()

        if not content:

            QMessageBox.warning(
                self,
                "Empty Memory",
                "Please enter something to remember."
            )

            return None

        return {
            "content": content,
            "category": category_input.currentText(),
            "importance": importance_input.value(),
        }

    # --------------------------------------------------
    # ADD CORE MEMORY
    # --------------------------------------------------

    def add_core_memory(self):

        data = self.memory_input_dialog(
            "Add Core Memory"
        )

        if not data:
            return

        try:

            self.memory.remember_core(
                data["content"],
                data["category"],
                importance=data["importance"]
            )

            self.refresh_all()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Unable to Add Memory",
                str(error)
            )

    # --------------------------------------------------
    # ADD LONG TERM MEMORY
    # --------------------------------------------------

    def add_long_memory(self):

        data = self.memory_input_dialog(
            "Add Long-term Memory"
        )

        if not data:
            return

        try:

            self.memory.remember(
                data["content"],
                data["category"],
                importance=data["importance"]
            )

            self.refresh_all()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Unable to Add Memory",
                str(error)
            )

    # --------------------------------------------------
    # GET SELECTED MEMORY
    # --------------------------------------------------

    def get_selected_memory(self, memory_type):

        if memory_type == "core":

            item = self.core_list.currentItem()

        else:

            item = self.long_list.currentItem()

        if item is None:

            QMessageBox.information(
                self,
                "Select Memory",
                "Please select a memory first."
            )

            return None

        return item.data(Qt.UserRole)

    # --------------------------------------------------
    # EDIT MEMORY
    # --------------------------------------------------

    def edit_selected_memory(self, memory_type):

        memory = self.get_selected_memory(memory_type)

        if not memory:
            return

        old_content = self.memory_content(memory)

        new_content, accepted = QInputDialog.getMultiLineText(
            self,
            "Edit Memory",
            "Update memory:",
            old_content
        )

        if not accepted:
            return

        new_content = new_content.strip()

        if not new_content:

            QMessageBox.warning(
                self,
                "Invalid Memory",
                "Memory cannot be empty."
            )

            return

        try:

            self.memory.update_memory(
                self.memory_id(memory),
                new_content
            )

            self.refresh_all()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Edit Error",
                str(error)
            )

    # --------------------------------------------------
    # PIN MEMORY
    # --------------------------------------------------

    def pin_selected_memory(self):

        memory = self.get_selected_memory("long")

        if not memory:
            return

        try:

            self.memory.pin_memory(
                self.memory_id(memory)
            )

            self.refresh_all()

            QMessageBox.information(
                self,
                "Memory Updated",
                "Memory moved to Core Memory."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Pin Error",
                str(error)
            )

    # --------------------------------------------------
    # DELETE MEMORY
    # --------------------------------------------------

    def delete_selected_memory(self, memory_type):

        memory = self.get_selected_memory(memory_type)

        if not memory:
            return

        confirmation = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this memory?"
        )

        if confirmation != QMessageBox.Yes:
            return

        try:

            self.memory.forget(
                self.memory_id(memory),
                allow_core=True
            )

            self.refresh_all()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Delete Error",
                str(error)
            )

    # --------------------------------------------------
    # SEARCH MEMORIES
    # --------------------------------------------------

    def search_memories(self):

        query = self.search_input.text().strip()

        if not query:
            return

        self.search_results.clear()

        try:

            results = self.memory.recall(query)

            if not results:

                self.search_results.addItem(
                    "No matching memories found."
                )

                return

            for result in results:

                data = self.to_dict(result)

                content = self.memory_content(data)

                self.search_results.addItem(content)

        except Exception as error:

            QMessageBox.critical(
                self,
                "Search Error",
                str(error)
            )

    # --------------------------------------------------
    # UNPIN MEMORY
    # --------------------------------------------------

    def unpin_selected_memory(self):

        memory = self.get_selected_memory("core")

        if not memory:
            return

        try:

            self.memory.unpin_memory(
                self.memory_id(memory)
            )

            self.refresh_all()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Unpin Error",
                str(error)
            )


# ------------------------------------------------------
# STANDALONE MEMORY CENTER
# ------------------------------------------------------

def main():

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    window = MemoryDashboard()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()