from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextDocument,
    QTextCharFormat,
    QColor,
    QFont,
)
from dataclasses import dataclass
from tree_sitter import Language, Parser, Tree, Query, QueryCursor, Node

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
        self.types_format = QTextCharFormat()
        self.base_format = QTextCharFormat()
        self.tree: Tree | None = None
        self.editor = parent

        self.parser = Parser(language=lang)
        self.query = Query(lang, scm)
        self.cursor = QueryCursor(self.query)

        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        self.class_format.setFontWeight(QFont.Weight.Bold)

        self.keyword_format.setForeground(QColor("#00bfff"))
        self.string_format.setForeground(QColor("#deb887"))
        self.function_foramt.setForeground(QColor("#daa520"))
        self.comment_format.setForeground(QColor("#808080"))
        self.error_format.setForeground(QColor("#ff0000"))
        self.class_format.setForeground(QColor("#98f5ff"))
        self.types_format.setForeground(QColor("#f08080"))
        self.constant_format.setForeground(QColor("#a2cd5a"))
        self.variable_format.setForeground(QColor("#4eee94"))
        self.base_format.setForeground(QColor("#cccccc"))

        self.editor.contentsChange.connect(self.on_text_changed)

        self.formats = {
            "keyword": self.keyword_format,
            "string": self.string_format,
            "function": self.function_foramt,
            "function.builtin": self.types_format,
            "comment": self.comment_format,
            "error": self.error_format,
            "constructor": self.class_format,
            "type": self.types_format,
            "constant": self.constant_format,
            "operator.keyword": self.keyword_format,
            "variable.declaration": self.variable_format,
            "property": self.base_format,
            "embedded": self.base_format,
            "variable.builtin": self.keyword_format,
        }

    def on_text_changed(
        self, position: int, chars_removed: int, chars_added: int
    ) -> None:
        text = self.editor.toPlainText()
        text_bytes = text.encode("utf-8")
        if self.tree is not None:
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

            self.tree = self.parser.parse(
                text_bytes, old_tree=self.tree, encoding="utf8"
            )

        else:
            self.tree = self.parser.parse(text_bytes, encoding="utf8")

        self.rehighlightBlock(self.editor.findBlock(position))

    def highlightBlock(self, text: str) -> None:
        if not self.tree:
            return

        block_pos = self.currentBlock().position()
        block_len = self.currentBlock().length()

        self.cursor.set_byte_range(block_pos, block_pos + block_len - 1)
        captures = self.cursor.captures(self.tree.root_node)

        captured: dict[tuple[int, int], str] = {}

        for name, nodes in captures.items():
            for node in nodes:
                captured[(node.start_byte, node.end_byte)] = name

        for (node_start_byte, node_end_byte), name in captured.items():
            local_start = node_start_byte - block_pos
            local_end = node_end_byte - block_pos
            local_len = local_end - local_start

            if local_len > 0:
                if name in self.formats:
                    self.setFormat(local_start, local_len, self.formats[name])
                else:
                    self.setFormat(local_start, local_len, self.base_format)
