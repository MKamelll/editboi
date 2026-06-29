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


@dataclass
class SyntaxTheme:
    keyword = QColor("#00bfff")
    string = QColor("#deb887")
    comment = QColor("#808080")
    function = QColor("#daa520")
    kind = QColor("#98f5ff")
    variable = QColor("#4eee94")
    constant = QColor("#a2cd5a")
    builtin = QColor("#f08080")
    preprocessor = QColor("#ffd700")
    doc_string = QColor("#ffe4b5")
    error = QColor("#ff0000")
    warning = QColor("#ffff00")
    klass = QColor("#98f5ff")


# reference: https://felgo.com/doc/qt5/qtwidgets-richtext-syntaxhighlighter-example/
# refrence: https://wiki.python.org/python/PyQt(2f)Python(20)syntax(20)highlighting.html


class HighlightingRule:
    def __init__(
        self, pattern: QRegularExpression, form: QTextCharFormat, group: int = 0
    ):
        self.pattern = pattern
        self.form = form
        self.group = group


class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument) -> None:
        super().__init__(parent)
        self.keyword_format = QTextCharFormat()
        self.class_format = QTextCharFormat()
        self.comment_format = QTextCharFormat()
        self.quotation_format = QTextCharFormat()
        self.function_foramt = QTextCharFormat()
        self.multiline_string_format = QTextCharFormat()
        self.builtin_format = QTextCharFormat()
        self.builtin = {
            "int",
            "str",
            "float",
            "bool",
            "list",
            "dict",
            "tuple",
            "set",
            "bytes",
            "None",
            "True",
            "False",
            "super",
        }
        self.theme = SyntaxTheme()

        self.keyword_format.setForeground(self.theme.keyword)
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        keyword_patterns = [
            rf"\b{k}\b" for k in chain(kwlist, softkwlist) if k not in self.builtin
        ]

        self.highlighting_rules = [
            HighlightingRule(QRegularExpression(p), self.keyword_format)
            for p in keyword_patterns
        ]

        self.builtin_format.setForeground(self.theme.builtin)
        self.highlighting_rules.extend(
            HighlightingRule(QRegularExpression(t), self.builtin_format)
            for t in self.builtin
        )

        self.class_format.setFontWeight(QFont.Weight.Bold)
        self.class_format.setForeground(self.theme.klass)
        self.highlighting_rules.append(
            HighlightingRule(
                QRegularExpression(r"\bclass\s+(\w+)\b"), self.class_format, 1
            )
        )

        self.quotation_format.setForeground(self.theme.string)
        self.highlighting_rules.append(
            HighlightingRule(
                QRegularExpression(r'"[^"]*"|\'[^\']*\''), self.quotation_format
            )
        )

        self.function_foramt.setForeground(self.theme.function)
        self.highlighting_rules.append(
            HighlightingRule(
                QRegularExpression(r"\bdef\s+(\w+)"), self.function_foramt, 1
            )
        )

        self.comment_format.setForeground(self.theme.comment)
        self.highlighting_rules.append(
            HighlightingRule(QRegularExpression("#[^\n]*"), self.comment_format)
        )

        self.triple_double = QRegularExpression('"""')
        self.triple_single = QRegularExpression("'''")
        self.multiline_string_format.setForeground(self.theme.string)

    def highlightBlock(self, text: str) -> None:
        for rule in self.highlighting_rules:
            match_iter = rule.pattern.globalMatch(text)
            while match_iter.hasNext():
                _match = match_iter.next()
                self.setFormat(
                    _match.capturedStart(rule.group),
                    _match.capturedLength(rule.group),
                    rule.form,
                )

        self.setCurrentBlockState(0)

        if not self.match_multiline(text, self.triple_double, 1):
            self.match_multiline(text, self.triple_single, 2)

    def match_multiline(self, text: str, delim: QRegularExpression, in_state: int):
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            _match = delim.match(text)
            start = _match.capturedStart()
            add = _match.capturedLength()

        while start >= 0:
            _match = delim.match(text, start + add)
            end = _match.capturedStart()
            if end >= add:
                length = end - start + add + _match.capturedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add

            self.setFormat(start, length, self.multiline_string_format)
            _match = delim.match(text, start + length)
            start = _match.capturedStart()

        return self.currentBlockState() == in_state
