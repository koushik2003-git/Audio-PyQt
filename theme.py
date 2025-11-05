from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

def apply_theme(app: QApplication, dark: bool = False, accent: str = "#F59E0B") -> None:

    pal = app.palette()
    if dark:
        pal.setColor(QPalette.ColorRole.Window, QColor("#111827"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#F9FAFB"))
    else:
        pal.setColor(QPalette.ColorRole.Window, QColor("#FDF2E9"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    app.setPalette(pal)
    app.setStyleSheet("""
    QLabel#HeroTitle { font-size: 22px; font-weight: 700; color: #111827; }
    QFrame[card="true"] { background: #ffffff; border: 1px solid #E5E7EB; border-radius: 16px; color: #111827;  }
    QPushButton { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 8px 14px; font-weight: 600; color: #111827; }
    QPushButton[primary="true"] { background: #F59E0B; color: white; border: none; }
    QPushButton[secondary="true"] { background: #fff; color: #111827; border: 1px solid #E5E7EB; }
    QPushButton[danger="true"] { background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }
    QLineEdit, QTextEdit { padding: 8px 12px; border: 1px solid #E5E7EB; border-radius: 10px; background: #ffffff; color: #111827;  }
    QHeaderView::section { background: #ffffff; border: 1px solid #E5E7EB; padding: 6px; border-radius: 8px; color: #111827;  }
    QTableWidget { background: #ffffff; border: 1px solid #E5E7EB; color: #111827;  }
    """)
