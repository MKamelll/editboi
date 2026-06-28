import sys

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QAction,
    QPaintEvent,
    QResizeEvent,
    QColor,
    QTextFormat,
    QPainter,
    QPalette,
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPlainTextEdit,
    QWidget,
    QTextEdit,
)

from colorscheme import make_palette


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.line_number_area = LineNumberArea(self, self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.setPalette(make_palette())
        self.text_style = QFont("DejaVu Sans Mono", 16)
        self.setFont(self.text_style)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self.palette().color(QPalette.ColorRole.Dark))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width(),
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def line_number_area_width(self) -> int:
        digits = 1
        _max = max(1, self.blockCount())
        while _max >= 10:
            _max //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def update_line_number_area_width(self, new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def highlight_current_line(self) -> None:
        extra_selections: list[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = self.palette().color(QPalette.ColorRole.Highlight)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)


class LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.code_editor.line_number_area_paint_event(event)


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
