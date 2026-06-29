import sys
from code_editor import CodeEditor
from highlighter import Highlighter
from PySide6.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Open", self.open_file)
        file_menu.addAction("Save", self.save_file)
        file_menu.addAction("Save as", self.save_as)
        file_menu.addAction("Quit", self.close)

        edit_menu = self.menuBar().addMenu("Edit")
        tools_menu = self.menuBar().addMenu("Tools")
        help_menu = self.menuBar().addMenu("Help")
        about_menu = self.menuBar().addMenu("About")

        self.code_editor = CodeEditor(self)
        self.highlighter = Highlighter(self.code_editor.document())
        self.setCentralWidget(self.code_editor)

    def open_file(self) -> None:
        pass

    def save_file(self) -> None:
        pass

    def save_as(self) -> None:
        pass


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.setWindowTitle("editorboi")
    w.resize(640, 420)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
