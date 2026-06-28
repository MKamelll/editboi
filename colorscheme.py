from PySide6.QtGui import QPalette, QColor

EDITOR_BG = "#0a0a1a"
EDITOR_FG = "#e8e8f0"
LINE_HIGHLIGHT = "#1a1a3a"
SELECTION_BG = "#2a2a5a"
SELECTION_FG = "#ffffff"
CURSOR = "#ffffff"

# Gutter
GUTTER_BG = "#07070f"
GUTTER_FG = "#4a4a7a"  # inactive line numbers
GUTTER_FG_ACTIVE = "#9999cc"  # current line number

# Scrollbar
SCROLLBAR_BG = "#1e1e3a"
SCROLLBAR_HANDLE = "#3a3a6a"

# Syntax
SYN_KEYWORD = "#7788ff"
SYN_STRING = "#88cc88"
SYN_COMMENT = "#4466aa"
SYN_FUNCTION = "#aaddff"
SYN_TYPE = "#ffcc66"
SYN_NUMBER = "#ff9966"
SYN_OPERATOR = "#cc88ff"
SYN_BUILTIN = "#66bbff"

# UI chrome
BORDER = "#1e1e3a"
STATUSBAR_BG = "#07070f"
STATUSBAR_FG = "#6666aa"
TOOLTIP_BG = "#1a1a3a"
TOOLTIP_FG = "#e8e8f0"


def make_palette() -> QPalette:
    p = QPalette()

    bg = QColor(EDITOR_BG)
    fg = QColor(EDITOR_FG)
    dark_bg = QColor(GUTTER_BG)
    mid_bg = QColor(LINE_HIGHLIGHT)
    sel_bg = QColor(SELECTION_BG)
    sel_fg = QColor(SELECTION_FG)
    muted = QColor(GUTTER_FG)

    p.setColor(QPalette.ColorRole.Window, bg)
    p.setColor(QPalette.ColorRole.WindowText, fg)
    p.setColor(QPalette.ColorRole.Base, bg)
    p.setColor(QPalette.ColorRole.AlternateBase, mid_bg)
    p.setColor(QPalette.ColorRole.Text, fg)
    p.setColor(QPalette.ColorRole.BrightText, QColor(CURSOR))
    p.setColor(QPalette.ColorRole.Button, dark_bg)
    p.setColor(QPalette.ColorRole.ButtonText, fg)
    p.setColor(QPalette.ColorRole.Highlight, sel_bg)
    p.setColor(QPalette.ColorRole.HighlightedText, sel_fg)
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(TOOLTIP_BG))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(TOOLTIP_FG))
    p.setColor(QPalette.ColorRole.PlaceholderText, muted)
    p.setColor(QPalette.ColorRole.Mid, mid_bg)
    p.setColor(QPalette.ColorRole.Dark, dark_bg)
    p.setColor(QPalette.ColorRole.Shadow, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Link, QColor(SYN_FUNCTION))
    p.setColor(QPalette.ColorRole.LinkVisited, QColor(SYN_BUILTIN))

    return p
