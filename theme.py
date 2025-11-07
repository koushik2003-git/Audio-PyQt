from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

# ---- Brand palette (matches your screenshot) ----
ORANGE         = "#F97316"   # primary
ORANGE_HOVER   = "#EA580C"
PEACH_CANVAS   = "#FFF3E9"   # app background
PEACH_SOFT     = "#FFE7D3"   # hover / selected fill
PEACH_TOPBAR   = "#FFE9D6"
BORDER         = "#E5E7EB"
TEXT           = "#111827"
TEXT_MUTED     = "#6B7280"
WHITE          = "#FFFFFF"

def _q(h: str) -> QColor: return QColor(h)

def apply_theme(app: QApplication, dark: bool = False, accent: str = ORANGE) -> None:
    """
    Unified light (peach/orange) theme for the whole app:
    - Use: apply_theme(app, dark=False)
    - Works for Login + Dashboard + all widgets
    """
    # ---- Qt palette (light) ----
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          _q(PEACH_CANVAS))
    pal.setColor(QPalette.ColorRole.Base,            _q(WHITE))
    pal.setColor(QPalette.ColorRole.AlternateBase,   _q("#F9FAFB"))
    pal.setColor(QPalette.ColorRole.Text,            _q(TEXT))
    pal.setColor(QPalette.ColorRole.WindowText,      _q(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          _q(WHITE))
    pal.setColor(QPalette.ColorRole.ButtonText,      _q(TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     _q(TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipText,     _q(WHITE))
    pal.setColor(QPalette.ColorRole.Link,            _q("#0EA5E9"))
    pal.setColor(QPalette.ColorRole.Highlight,       _q(accent))
    pal.setColor(QPalette.ColorRole.HighlightedText, _q(WHITE))
    app.setPalette(pal)

    # ---- Global stylesheet ----
    css = f"""
    * {{ outline: none; }}
    QWidget {{
        background: {PEACH_CANVAS};
        color: {TEXT};
        font-family: 'Segoe UI','Inter',system-ui,-apple-system,Roboto,Arial,sans-serif;
        font-size: 14px;
    }}

    /* ---------- Layout blocks / Cards ---------- */
    QFrame[card="true"], QGroupBox[loginCard="true"] {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 16px;
    }}

    /* ---------- Top bar on Login ---------- */
    QFrame#TopBar {{
        background: {PEACH_TOPBAR};
        border-bottom: 1px solid #F5D3B3;
    }}

    /* ---------- Hero text on Login ---------- */
    QLabel#HeroTitle {{
        font-size: 20px;
        font-weight: 700;
        color: {TEXT};
    }}
    QLabel#H1 {{
        font-size: 28px;
        font-weight: 800;
        color: {TEXT};
    }}
    QLabel#HeroBody {{
        color: {TEXT_MUTED};
        font-size: 13px;
    }}

    /* ---------- Tabs ---------- */
    QTabWidget::pane {{ border: 0; }}
    QTabBar::tab {{
        padding: 6px 12px;
        margin-right: 6px;
        border-radius: 12px;
        background: {WHITE};
        border: 1px solid {BORDER};
        min-height: 28px;
        font-weight: 600;
        color: #374151;
    }}
    QTabBar::tab:selected {{
        background: {PEACH_SOFT};
        border: 1px solid {accent};
        color: {TEXT};
    }}
    QTabBar::tab:hover {{ background: {PEACH_SOFT}; }}

    /* ---------- Inputs ---------- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
        padding: 10px 12px;
        border: 1px solid {BORDER};
        border-radius: 10px;
        background: {WHITE};
        selection-background-color: {accent};
        selection-color: {WHITE};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
        border: 2px solid {accent};
    }}

    /* ---------- Response areas (pure white) ---------- */
    QTextBrowser#ResponseBox, QTextEdit#ResponseBox {{
        background: {WHITE};
        color: {TEXT};
        border: 1.5px solid {BORDER};
        border-radius: 12px;
        padding: 10px;
    }}

    /* ---------- Buttons ---------- */
    QPushButton[primary="true"] {{
        background: {accent};
        color: {WHITE};
        border: none;
        border-radius: 10px;
        padding: 12px 16px;
        font-weight: 600;
    }}
    QPushButton[primary="true"]:hover {{ background: {ORANGE_HOVER}; }}
    QPushButton[primary="true"]:disabled {{ background: #FBC9A8; color: #FFF; }}

    QPushButton[secondary="true"] {{
        background: {WHITE};
        color: {accent};
        border: 1px solid {accent};
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
    }}
    QPushButton[secondary="true"]:hover {{ background: {PEACH_SOFT}; }}

    QPushButton[chip="true"] {{
        background: {WHITE};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 6px 10px;
    }}
    QPushButton[chip="true"]:hover {{ border-color: {accent}; color: {accent}; }}

    /* ---------- Checkboxes & Radios ---------- */
    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {BORDER};
        border-radius: 4px;
        background: {WHITE};
    }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        border: 1px solid {accent};
        background: {accent};
    }}

    /* Toggle switch (opt-in): set checkbox property appearance='switch' */
    QCheckBox[appearance="switch"]::indicator {{
        width: 40px; height: 22px;
        border-radius: 11px;
        border: 1px solid {BORDER};
        background: #F3F4F6;
    }}
    QCheckBox[appearance="switch"]::indicator:checked {{
        background: {accent};
        border: 1px solid {accent};
    }}
    QCheckBox[appearance="switch"]::indicator:unchecked {{
        background: #E5E7EB;
    }}
    /* knob */
    QCheckBox[appearance="switch"]::indicator:checked {{
        image: none; /* no default */
    }}
    QCheckBox[appearance="switch"]::indicator:unchecked {{
        image: none;
    }}
    QCheckBox[appearance="switch"]::indicator {{
        /* draw the knob using box-shadow trick (Qt can't, so simulate via margins) */
        margin-left: 0px; margin-right: 0px;
    }}
    /* move the knob using padding via two pseudo states */
    QCheckBox[appearance="switch"]::indicator:unchecked {{
        border-radius: 11px;
        padding-left: 2px; padding-right: 20px;
    }}
    QCheckBox[appearance="switch"]::indicator:checked {{
        border-radius: 11px;
        padding-left: 20px; padding-right: 2px;
    }}

    /* ---------- Combos ---------- */
    QComboBox {{
        padding: 8px 12px;
        border: 1px solid {BORDER};
        border-radius: 10px;
        background: {WHITE};
    }}
    QComboBox:focus {{ border: 2px solid {accent}; }}
    QComboBox QAbstractItemView {{
        background: {WHITE};
        border: 1px solid {BORDER};
        selection-background-color: {PEACH_SOFT};
        selection-color: {TEXT};
    }}

    /* ---------- Tooltips ---------- */
    QToolTip {{
        background: {TEXT};
        color: {WHITE};
        border: 0;
        padding: 6px 8px;
        border-radius: 6px;
    }}

    /* ---------- Scrollbars ---------- */
    QScrollBar:vertical {{ width: 14px; background: transparent; }}
    QScrollBar::handle:vertical {{ min-height: 24px; border-radius: 7px; background: #D1D5DB; }}
    QScrollBar::handle:vertical:hover {{ background: #F59E0B; }}
    QScrollBar:horizontal {{ height: 14px; background: transparent; }}
    QScrollBar::handle:horizontal {{ min-width: 24px; border-radius: 7px; background: #D1D5DB; }}
    QScrollBar::handle:horizontal:hover {{ background: #F59E0B; }}

    /* ---------- Group titles ---------- */
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {TEXT_MUTED};
        font-weight: 600;
    }}
    """
