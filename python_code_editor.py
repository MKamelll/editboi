from PySide6.QtCore import QRect, QSize, Qt, QPointF, Signal
from PySide6.QtGui import (
    QPaintEvent,
    QResizeEvent,
    QTextFormat,
    QPainter,
    QPalette,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QTextCursor,
    QTextBlock,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QAbstractItemView
from colorscheme import make_palette
from python_highlighter import PythonHighlighter
import tree_sitter_language_pack as tslp
from completer import Completer
import re
from tree_sitter import Language, Parser, Tree, Query, QueryCursor, Node

# refrence: https://felgo.com/doc/qt5/qtwidgets-widgets-codeeditor-example/


class PythonCodeEditor(QPlainTextEdit):
    treeUpdated = Signal(Tree)
    needsRehighlight = Signal(QTextBlock)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.line_number_area = LineNumberArea(self, self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.setPalette(make_palette())
        self.font_size = 16
        self.font_name = "DejaVu Sans Mono"
        self.tab_size = 4
        self.insert_spaces_instead_of_tabs = True
        self.text_style = QFont(self.font_name, self.font_size)
        self.text_style.setFixedPitch(True)
        self.setFont(self.text_style)
        self.setTabStopDistance(
            QFontMetrics(self.text_style).horizontalAdvance(" ") * 4
        )
        self.lang_id = "python"

        lang = tslp.get_language(self.lang_id)
        self.parser = Parser(language=lang)
        self.tree = self.build_initial_tree()

        scm = self.load_highlights_scm()
        query = Query(lang, scm)
        cursor = QueryCursor(query)
        self.highlighter = PythonHighlighter(self.tree, cursor, self)
        self.document().contentsChange.connect(self.on_text_changed)

        self.completer = Completer(self)
        self.completer.activated.connect(self.insert_completion)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def load_highlights_scm(self) -> str:
        scm = tslp.get_highlights_query(self.lang_id)
        try:
            with open(f"custom/{self.lang_id}.scm", "r") as f:
                custom_scm = f.read()
                if scm:
                    scm += "\n" + custom_scm
                else:
                    scm = custom_scm
                return scm
        except OSError as e:
            print(f"no custom scm found for {self.lang_id}, using the default: {e}")

    def load_file(self, path: str) -> None:
        with open(path, "r") as f:
            content = f.read()
            self.setPlainText(content)
            if self.highlighter:
                self.highlighter.rehighlight()

    def save_file(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.toPlainText())

    def build_initial_tree(self) -> Tree:
        text = self.toPlainText()
        text_bytes = text.encode(encoding="utf-8")
        tree = self.parser.parse(text_bytes, encoding="utf8")
        return tree

    def on_text_changed(
        self, position: int, chars_removed: int, chars_added: int
    ) -> None:
        text = self.document().toPlainText()
        text_bytes = text.encode("utf-8")

        start_byte = position
        old_end_byte = start_byte + chars_removed
        new_end_byte = start_byte + chars_added

        self.tree.edit(
            start_byte=start_byte,
            old_end_byte=old_end_byte,
            new_end_byte=new_end_byte,
            start_point=(0, 0),
            old_end_point=(0, 0),
            new_end_point=(0, 0),
        )

        self.tree = self.parser.parse(text_bytes, old_tree=self.tree, encoding="utf8")
        self.treeUpdated.emit(self.tree)

        self.needsRehighlight.emit(self.document().findBlock(position))

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self.insert_spaces_instead_of_tabs:
            return
        painter = QPainter(self.viewport())
        self.draw_indent_dots(painter, event.rect())
        painter.end()

    def draw_indent_dots(self, painter: QPainter, rect: QRect) -> None:
        metrics = self.fontMetrics()
        char_width = metrics.horizontalAdvance(" ")
        line_height = metrics.height()
        color = self.palette().color(QPalette.ColorRole.PlaceholderText)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        dot_radius = 1.5
        block = self.firstVisibleBlock()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )

        while block.isValid() and top <= rect.bottom():
            bottom = top + int(self.blockBoundingRect(block).height())
            if block.isVisible() and bottom >= rect.top():
                text = block.text()
                leading_spaces = len(text) - len(text.lstrip(" "))
                for col in range(leading_spaces):
                    x = self.contentOffset().x() + col * char_width + char_width / 2
                    y = top + line_height / 2
                    painter.drawEllipse(QPointF(x, y), dot_radius, dot_radius)
            top = bottom
            block = block.next()

    def get_popup_prev_row(self, popup: QAbstractItemView) -> int:
        row = popup.currentIndex().row()
        row_count = self.completer.completionModel().rowCount()
        prev_row = (row - 1) % row_count if row_count > 0 else row
        return prev_row

    def get_popup_next_row(self, popup: QAbstractItemView) -> int:
        row = popup.currentIndex().row()
        row_count = self.completer.completionModel().rowCount()
        next_row = (row + 1) % row_count if row_count > 0 else row
        return next_row

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if popup := self.completer.popup():
            if popup.isVisible():
                if event.key() == Qt.Key.Key_Up:
                    popup.setCurrentIndex(
                        self.completer.completionModel().index(
                            self.get_popup_prev_row(popup), 0
                        )
                    )
                    return
                if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                    index = popup.currentIndex()
                    completion = self.completer.completionModel().data(index)
                    self.insert_completion(completion)
                    popup.hide()
                    return
                if event.key() in [Qt.Key.Key_Tab, Qt.Key.Key_Down]:
                    popup.setCurrentIndex(
                        self.completer.completionModel().index(
                            self.get_popup_next_row(popup), 0
                        )
                    )
                    return
                if event.key() == Qt.Key.Key_Escape:
                    popup.hide()
                    return

        if event.key() == Qt.Key.Key_Tab and self.insert_spaces_instead_of_tabs:
            cursor = self.textCursor()
            cursor.insertText(" " * self.tab_size)
            return

        super().keyPressEvent(event)

    def insert_completion(self, completion: str) -> None:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def get_document_words(self) -> list[str]:
        text = self.toPlainText()
        words = re.findall(r"\b\w+\b", text)
        current_word = self.word_under_cursor()
        return list(k for k in set(words) if k != current_word)

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
    def __init__(self, editor: PythonCodeEditor, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.python_code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.python_code_editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.python_code_editor.line_number_area_paint_event(event)
