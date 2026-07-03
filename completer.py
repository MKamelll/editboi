from PySide6.QtWidgets import QCompleter, QAbstractItemView
from PySide6.QtCore import Qt, QStringListModel, QTimer
from PySide6.QtGui import QTextCursor
from keyword import kwlist, softkwlist
import builtins
from itertools import chain
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from code_editor import CodeEditor


class Completer(QCompleter):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(parent=editor)

        self.editor = editor
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setWidget(self.editor)

        self.minimum_prefix_length = 2
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self.update_completer)
        self.editor.textChanged.connect(self._debounce.start)
        self.editor.textChanged.connect(self.update_prefix)

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

    def popup_best_size(self, popup: QAbstractItemView, extra_padding: int = 0) -> int:
        padding = popup.width() - popup.viewport().width()
        frame_width = 2 * popup.frameWidth()
        longest_string = ""
        model = self.completionModel()
        for row in range(model.rowCount()):
            text = model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole)
            if text and len(text) > len(longest_string):
                longest_string = text

        metrics = popup.fontMetrics()
        text_width = metrics.horizontalAdvance(longest_string)
        return padding + frame_width + text_width + extra_padding

    def update_completer(self) -> None:
        doc_words = self.editor.get_document_words()
        all_words = sorted(set(self.words_list + doc_words))
        model = QStringListModel(all_words)
        self.setModel(model)

    def update_prefix(self) -> None:
        cursor = self.editor.textCursor()
        pos = cursor.position()
        doc = self.editor.document()
        char_before = doc.characterAt(pos - 1) if pos > 0 else ""

        if not char_before.isalnum() and char_before not in ["_", "."]:
            if popup := self.popup():
                popup.hide()
            return

        prefix = self.editor.word_under_cursor()
        if len(prefix) < self.minimum_prefix_length:
            if popup := self.popup():
                popup.hide()
            return

        if prefix != self.completionPrefix():
            self.setCompletionPrefix(prefix)

        if self.completionCount() == 0:
            if popup := self.popup():
                popup.hide()
            return

        rect = self.editor.cursorRect()
        if popup := self.popup():
            rect.setWidth(popup.sizeHintForColumn(0) + self.popup_best_size(popup))

        self.complete(rect)
