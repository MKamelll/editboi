from code_editor import CodeEditor
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

        self.code_editor = CodeEditor(".py", self)
        self.setCentralWidget(self.code_editor)

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py);;All Files (*)"
        )

        if path:
            self.code_editor.load_file(path)
            self.current_file = path

    def save_file(self) -> None:
        if self.current_file:
            self.code_editor.save_file(self.current_file)
        else:
            self.save_as()

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Python Files (*.py);;All Files (*)"
        )
        if path:
            self.code_editor.save_file(path)
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
