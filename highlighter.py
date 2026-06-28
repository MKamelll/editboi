from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextDocument,
    QTextCharFormat,
    QColor,
    QFont,
)
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRegularExpression, QRegularExpressionMatchIterator
from dataclasses import dataclass
from keyword import kwlist
import re


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


class HighlightingRule:
    def __init__(self, pattern: QRegularExpression, form: QTextCharFormat):
        self.pattern = pattern
        self.form = form


class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument) -> None:
        super().__init__(parent)
        self.keyword_format = QTextCharFormat()
        self.class_format = QTextCharFormat()
        self.comment_format = QTextCharFormat()
        self.quotation_format = QTextCharFormat()
        self.function_foramt = QTextCharFormat()
        self.multiline_string_format = QTextCharFormat()
        self.theme = SyntaxTheme()

        self.keyword_format.setForeground(self.theme.keyword)
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        keyword_patterns = [rf"\b{k}\b" for k in kwlist]

        self.highlighting_rules = [
            HighlightingRule(QRegularExpression(p), self.keyword_format)
            for p in keyword_patterns
        ]

        self.class_format.setFontWeight(QFont.Weight.Bold)
        self.class_format.setForeground(self.theme.klass)
        self.highlighting_rules.append(
            HighlightingRule(
                QRegularExpression(r"\bclass\s+(\w+)\b"), self.class_format
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
                QRegularExpression(r"\bdef\s+(\w+)"),
                self.function_foramt,
            )
        )

        self.comment_format.setForeground(self.theme.comment)
        self.highlighting_rules.append(
            HighlightingRule(QRegularExpression("#[^\n]*"), self.comment_format)
        )

        self.multiline_expression = QRegularExpression(r'"""|\'\'\'')
        self.multiline_string_format.setForeground(self.theme.string)

    def highlightBlock(self, text: str) -> None:
        for rule in self.highlighting_rules:
            match_iter = rule.pattern.globalMatch(text)
            while match_iter.hasNext():
                _match = match_iter.next()
                if rule.form in [self.class_format, self.function_foramt]:
                    self.setFormat(
                        _match.capturedStart(1), _match.capturedLength(1), rule.form
                    )
                else:
                    self.setFormat(
                        _match.capturedStart(), _match.capturedLength(), rule.form
                    )
