import sys
from PySide6.QtWidgets import QApplication
from mainwindow import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.setWindowTitle("editorboi")
    w.resize(640, 420)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
