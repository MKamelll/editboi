from PySide6.QtCore import QRect, QSize, Qt, QStringListModel
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
)
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QWidget,
    QTextEdit,
    QCompleter,
    QAbstractItemView,
)

from colorscheme import make_palette
from keyword import kwlist, softkwlist
import builtins
from itertools import chain
import re
from python_highlighter import PythonHighlighter
import tree_sitter_language_pack as tslp

# refrence: https://felgo.com/doc/qt5/qtwidgets-widgets-codeeditor-example/

type Highlighter = PythonHighlighter


class CodeEditor(QPlainTextEdit):
    def __init__(self, ext: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.line_number_area = LineNumberArea(self, self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.setPalette(make_palette())
        self.text_style = QFont("DejaVu Sans Mono", 16)
        self.text_style.setFixedPitch(True)
        self.setFont(self.text_style)
        self.setTabStopDistance(
            QFontMetrics(self.text_style).horizontalAdvance(" ") * 4
        )
        self.highlighter: Highlighter | None = None
        highlighters = {"python": PythonHighlighter}

        ext_map = {".py": "python"}
        self.lang_id = ext_map.get(ext)

        if self.lang_id:
            lang = tslp.get_language(self.lang_id)
            scm = tslp.get_highlights_query(self.lang_id)
            custom_scm = ""
            try:
                with open(f"custom/{self.lang_id}.scm", "r") as f:
                    custom_scm = f.read()
            except OSError as e:
                print(f"no custom scm found for {self.lang_id}, using the default: {e}")
            if scm:
                scm += "\n" + custom_scm
            else:
                scm = custom_scm
            highlighter = highlighters.get(self.lang_id)
            if highlighter:
                self.highlighter = highlighter(lang, scm, self.document())

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.words_list = list(
            set(
                k
                for k in chain(
                    kwlist,
                    softkwlist,
                    dir(builtins),
                    dir(type),
                    dir(object),
                    ["self", "cls"],
                )
            )
        )
        self.completer = QCompleter(self.words_list)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.minimum_prefix_length = 2
        self.document().contentsChanged.connect(self.update_completer)

    def load_file(self, path: str) -> None:
        with open(path, "r") as f:
            content = f.read()
            self.setPlainText(content)
            if self.highlighter:
                self.highlighter.rehighlight()

    def save_file(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.toPlainText())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if popup := self.completer.popup():
            if popup.isVisible():
                if event.key() == Qt.Key.Key_Up:
                    row = popup.currentIndex().row()
                    prev_row = (row - 1) % self.completer.completionModel().rowCount()
                    popup.setCurrentIndex(
                        self.completer.completionModel().index(prev_row, 0)
                    )
                    return
                if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                    index = popup.currentIndex()
                    completion = self.completer.completionModel().data(index)
                    self.insert_completion(completion)
                    popup.hide()
                    return
                if event.key() in [Qt.Key.Key_Tab, Qt.Key.Key_Down]:
                    row = popup.currentIndex().row()
                    next_row = (row + 1) % self.completer.completionModel().rowCount()
                    popup.setCurrentIndex(
                        self.completer.completionModel().index(next_row, 0)
                    )
                    return
                if event.key() == Qt.Key.Key_Escape:
                    popup.hide()
                    return

        super().keyPressEvent(event)

        prefix = self.word_under_cursor()
        if len(prefix) < self.minimum_prefix_length:
            if popup := self.completer.popup():
                popup.hide()
            return

        if prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(prefix)
            if popup := self.completer.popup():
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

        rect = self.cursorRect()
        if popup := self.completer.popup():
            rect.setWidth(popup.sizeHintForColumn(0) + self.popup_best_size(popup))

        self.completer.complete(rect)

    def popup_best_size(self, popup: QAbstractItemView, extra_padding: int = 0) -> int:
        padding = popup.width() - popup.viewport().width()
        frame_width = 2 * popup.frameWidth()
        longest_string = ""
        model = self.completer.completionModel()
        for row in range(model.rowCount()):
            text = model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole)
            if text and len(text) > len(longest_string):
                longest_string = text

        metrics = popup.fontMetrics()
        text_width = metrics.horizontalAdvance(longest_string)
        return padding + frame_width + text_width + extra_padding

    def get_document_words(self) -> list[str]:
        text = self.toPlainText()
        words = re.findall(r"\b\w+\b", text)
        current_word = self.word_under_cursor()
        return list(k for k in set(words) if k != current_word)

    def update_completer(self) -> None:
        doc_words = self.get_document_words()
        all_words = sorted(set(self.words_list + doc_words))
        model = QStringListModel(all_words)
        self.completer.setModel(model)

    def insert_completion(self, completion: str):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

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
