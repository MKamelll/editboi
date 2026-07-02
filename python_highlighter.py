from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextDocument,
    QTextCharFormat,
    QColor,
    QFont,
)
from PySide6.QtCore import QRegularExpression
from dataclasses import dataclass
from keyword import kwlist, softkwlist
from itertools import chain
from tree_sitter import Language, Parser, Tree, Query, QueryCursor
import logging


@dataclass
class SyntaxTheme:
    keyword = QColor("#00bfff")
    string = QColor("#deb887")
    comment = QColor("#808080")
    function = QColor("#daa520")
    variable = QColor("#4eee94")
    constant = QColor("#a2cd5a")
    kind = QColor("#f08080")
    preprocessor = QColor("#ffd700")
    error = QColor("#ff0000")
    warning = QColor("#ffff00")
    klass = QColor("#98f5ff")
    base = QColor("#cccccc")


# reference: https://felgo.com/doc/qt5/qtwidgets-richtext-syntaxhighlighter-example/
# refrence: https://wiki.python.org/python/PyQt(2f)Python(20)syntax(20)highlighting.html


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, lang: Language, scm: str, parent: QTextDocument) -> None:
        super().__init__(parent)
        self.keyword_format = QTextCharFormat()
        self.class_format = QTextCharFormat()
        self.comment_format = QTextCharFormat()
        self.function_foramt = QTextCharFormat()
        self.string_format = QTextCharFormat()
        self.variable_format = QTextCharFormat()
        self.error_format = QTextCharFormat()
        self.constant_format = QTextCharFormat()
        self.kind_format = QTextCharFormat()
        self.base_format = QTextCharFormat()
        self.theme = SyntaxTheme()
        self.tree: Tree | None = None
        self.editor = parent
        self.parser = Parser(language=lang)
        self.query = Query(lang, scm)
        self.cursor = QueryCursor(self.query)

        self.keyword_format.setForeground(self.theme.keyword)
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        self.error_format.setForeground(self.theme.error)

        self.class_format.setFontWeight(QFont.Weight.Bold)
        self.class_format.setForeground(self.theme.klass)

        self.comment_format.setForeground(self.theme.comment)

        self.kind_format.setForeground(self.theme.kind)
        self.string_format.setForeground(self.theme.string)
        self.variable_format.setForeground(self.theme.variable)
        self.function_foramt.setForeground(self.theme.function)
        self.constant_format.setForeground(self.theme.constant)
        self.base_format.setForeground(self.theme.base)

        self.editor.contentsChange.connect(self.on_text_changed)

        self.formats = {
            "keyword": self.keyword_format,
            "string": self.string_format,
            "function": self.function_foramt,
            "function.builtin": self.kind_format,
            "comment": self.comment_format,
            "error": self.error_format,
            "constructor": self.class_format,
            "type": self.class_format,
            "constant": self.constant_format,
            "operator": self.keyword_format,
            "variable": self.variable_format,
            "property": self.base_format,
            "embedded": self.base_format,
        }

    def on_text_changed(
        self, position: int, chars_removed: int, chars_added: int
    ) -> None:
        text = self.editor.toPlainText()
        text_bytes = text.encode("utf-16-le")
        if self.tree is not None:
            start_byte = position * 2
            old_end_byte = (start_byte + chars_removed) * 2
            new_end_byte = (start_byte + chars_added) * 2

            self.tree.edit(
                start_byte=start_byte,
                old_end_byte=old_end_byte,
                new_end_byte=new_end_byte,
                start_point=(0, 0),
                old_end_point=(0, 0),
                new_end_point=(0, 0),
            )

            self.tree = self.parser.parse(
                text_bytes, old_tree=self.tree, encoding="utf16le"
            )

        else:
            self.tree = self.parser.parse(text_bytes, encoding="utf16le")

        self.rehighlightBlock(self.editor.findBlock(position))

    def highlightBlock(self, text: str) -> None:
        if not self.tree:
            return

        block_pos = self.currentBlock().position()
        block_len = self.currentBlock().length()

        block_start_byte = block_pos * 2
        block_end_byte = (block_pos + block_len - 1) * 2

        self.cursor.set_byte_range(block_start_byte, block_end_byte)
        captures = self.cursor.captures(self.tree.root_node)

        for name, nodes in captures.items():
            for node in nodes:
                local_start = node.start_byte // 2 - block_pos
                local_end = node.end_byte // 2 - block_pos
                local_len = local_end - local_start

                node_text = node.text.decode(encoding="utf-16-le") if node.text else ""

                if local_len > 0:
                    if name == "variable" and node_text == "self":
                        self.setFormat(local_start, local_len, self.keyword_format)
                    elif name in self.formats:
                        self.setFormat(local_start, local_len, self.formats[name])
                    else:
                        self.setFormat(local_start, local_len, self.base_format)
