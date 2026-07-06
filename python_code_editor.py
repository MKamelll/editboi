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
        self.indent_level = 0
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

        self.highlight_scm = self.load_highlights_scm()
        self.highlight_query = Query(lang, self.highlight_scm)
        self.highlight_cursor = QueryCursor(self.highlight_query)
        self.highlighter = PythonHighlighter(self.tree, self.highlight_cursor, self)
        self.document().contentsChange.connect(self.on_text_changed)

        self.indent_scm = self.load_indents_scm()
        self.indent_query = Query(lang, self.indent_scm) if self.indent_scm else None
        self.indent_cursor = (
            QueryCursor(self.indent_query) if self.indent_query else None
        )

        self.completer = Completer(self)
        self.completer.activated.connect(self.insert_completion)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def load_highlights_scm(self) -> str:
        scm = tslp.get_highlights_query(self.lang_id)
        try:
            with open(f"custom/{self.lang_id}/highlights.scm", "r") as f:
                custom_scm = f.read()
                if scm:
                    scm += "\n" + custom_scm
                else:
                    scm = custom_scm
                return scm
        except OSError as e:
            print(f"no custom scm found for {self.lang_id}, using the default: {e}")

    def load_indents_scm(self) -> str:
        scm = tslp.get_indents_query(self.lang_id)
        try:
            with open(f"custom/{self.lang_id}/indents.scm", "r") as f:
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

    def maybe_dedent_line(self, row: int) -> None:
        if not self.indent_cursor:
            return
        text = self.get_line_text(row).strip()
        first_word = text.split()[0].rstrip(":") if text else ""

        if first_word not in ["else", "elif", "except", "finally"]:
            return

        matches = self.indent_cursor.matches(self.tree.root_node)
        for index, capture in matches:
            for node in capture.get("indent.error_branch", []):
                if node.start_point[0] != row:
                    continue
                node_text = node.text.decode("utf-8") if node.text else ""
                if node_text != first_word:
                    continue
                error_node = node.parent
                parent = error_node.parent if error_node else None
                valid_parents = {
                    "else": (
                        "if_statement",
                        "for_statement",
                        "while_statement",
                        "try_statement",
                    ),
                    "elif": ("if_statement",),
                    "except": ("try_statement",),
                    "finally": ("try_statement",),
                }[first_word]
                while parent is not None:
                    if parent.type in valid_parents:
                        target_indent = self.get_line_indent(parent.start_point[0])
                        self.set_line_indent(row, target_indent)
                        return
                    parent = parent.parent

    def cursor_pos_to_utf8_byte_offset(self, cursor_pos: int) -> int:
        text = self.toPlainText()
        prefix = text[:cursor_pos]
        return len(prefix.encode("utf-8"))

    def set_line_indent(self, row: int, target_indent: int) -> None:
        block = self.document().findBlockByNumber(row)
        if not block.isValid():
            return
        text = block.text().lstrip(" ")
        cursor = QTextCursor(block)
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.insertText(" " * target_indent + text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def maybe_indent_line(self, row: int) -> None:
        if not self.indent_cursor:
            return
        prev_row = max(0, row - 1)
        matches = self.indent_cursor.matches(self.tree.root_node)
        begins: set[int] = set()
        branches: set[int] = set()
        dedents: set[int] = set()
        aligns: list[tuple[int, int, int]] = []

        for index, capture in matches:
            for name, nodes in capture.items():
                for node in nodes:
                    if name == "indent.begin":
                        begins.add(node.start_point[0])
                    elif name == "indent.branch":
                        branches.add(node.start_point[0])
                    elif name == "indent.dedent_next":
                        dedents.add(node.start_point[0])
                    elif name == "indent.align":
                        aligns.append(
                            (
                                node.start_point[0],
                                node.start_point[1],
                                node.end_point[0],
                            )
                        )

        for open_row, open_col, close_row in aligns:
            if open_row <= prev_row < close_row:
                self.set_line_indent(row, open_col + 1)
                return

        base_indent = self.get_line_indent(prev_row)

        if prev_row in begins or prev_row in branches:
            self.set_line_indent(row, base_indent + self.tab_size)
            return
        if prev_row in dedents:
            self.set_line_indent(row, max(0, base_indent - self.tab_size))
            return

        self.set_line_indent(row, base_indent)

    def get_line_text(self, row: int) -> str:
        cursor = self.textCursor()
        block = cursor.block()
        if not block.isValid():
            return ""

        return block.text()

    def get_line_indent(self, row: int) -> int:
        block = self.document().findBlockByNumber(row)
        if not block.isValid():
            return 0
        text = block.text()
        return len(text) - len(text.lstrip(" "))

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
            self.setTextCursor(cursor)
            return

        if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            cursor = self.textCursor()
            self.maybe_dedent_line(cursor.blockNumber())
            super().keyPressEvent(event)
            new_row = self.textCursor().blockNumber()
            new_row_text = self.document().findBlockByNumber(new_row).text()
            if new_row_text.strip() == "":
                self.maybe_indent_line(new_row)
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
