from code_editor import CodeEditor
from highlighter import Highlighter
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_file: str | None = None

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Open", self.open_file, shortcut="Ctrl+o")
        file_menu.addAction("Save", self.save_file, shortcut="Ctrl+s")
        file_menu.addAction("Save as", self.save_as, shortcut="Ctrl+Shift+s")
        file_menu.addAction("Quit", self.quit, shortcut="Ctrl+q")

        edit_menu = self.menuBar().addMenu("Edit")
        tools_menu = self.menuBar().addMenu("Tools")
        help_menu = self.menuBar().addMenu("Help")
        about_menu = self.menuBar().addMenu("About")

        self.code_editor = CodeEditor(self)
        self.highlighter = Highlighter(self.code_editor.document())
        self.setCentralWidget(self.code_editor)

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py);;All Files (*)"
        )

        if path:
            with open(path, "r") as f:
                content = f.read()
                self.code_editor.setPlainText(content)

            self.current_file = path

    def save_file(self) -> None:
        if self.current_file:
            with open(self.current_file, "w") as f:
                f.write(self.code_editor.toPlainText())
        else:
            self.save_as()

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Python Files (*.py);;All Files (*)"
        )
        if path:
            with open(path, "w") as f:
                f.write(self.code_editor.toPlainText())
            self.current_file = path

    def quit(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.close()
