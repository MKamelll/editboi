from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextDocument,
    QTextCharFormat,
    QColor,
    QFont,
)
from dataclasses import dataclass
from tree_sitter import Language, Tree, Query, QueryCursor, Node
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_code_editor import PythonCodeEditor

# reference: https://felgo.com/doc/qt5/qtwidgets-richtext-syntaxhighlighter-example/
# refrence: https://wiki.python.org/python/PyQt(2f)Python(20)syntax(20)highlighting.html


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(
        self,
        tree: Tree,
        cursor: QueryCursor,
        editor: "PythonCodeEditor",
    ) -> None:
        super().__init__(editor)
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
        self.tree = tree
        self.editor = editor
        self.cursor = cursor
        self.setDocument(self.editor.document())

        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        self.keyword_format.setForeground(QColor("#00bfff"))
        self.string_format.setForeground(QColor("#deb887"))
        self.function_foramt.setForeground(QColor("#daa520"))
        self.comment_format.setForeground(QColor("#808080"))
        self.error_format.setForeground(QColor("#ff0000"))
        self.class_format.setForeground(QColor("#98f5ff"))
        self.decorator_format = self.class_format
        self.types_format.setForeground(QColor("#f08080"))
        self.function_builtin_format = self.types_format
        self.constant_format.setForeground(QColor("#a2cd5a"))
        self.variable_format.setForeground(QColor("#4eee94"))
        self.base_format.setForeground(QColor("#cccccc"))

        self.editor.treeUpdated.connect(self.update_tree)
        self.editor.needsRehighlight.connect(self.rehighlightBlock)

        self.formats = {
            "keyword": self.keyword_format,
            "string": self.string_format,
            "function": self.function_foramt,
            "function.method": self.function_foramt,
            "function.decorator": self.decorator_format,
            "function.builtin": self.function_builtin_format,
            "comment": self.comment_format,
            "error": self.error_format,
            "type": self.types_format,
            "constant.builtin": self.constant_format,
            "operator.keyword": self.keyword_format,
            "variable.declaration": self.variable_format,
            "variable.builtin": self.keyword_format,
            "class": self.class_format,
            "property.declaration": self.variable_format,
        }

    def update_tree(self, tree: Tree) -> None:
        self.tree = tree

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
