
from typing import Optional
import os

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QGraphicsDropShadowEffect, QDialog, QFrame, QToolButton
)
from PyQt6.QtGui import QPixmap, QIcon, QColor
from PyQt6.QtCore import Qt

__all__ = ["LoginPage", "LoginDialog"]


class LoginPage(QWidget):
    """Anthrobyte-styled login page matching the provided screenshot layout exactly."""

    def __init__(self, parent: Optional[QWidget] = None, assets_path: Optional[str] = None):
        super().__init__(parent)
        self.assets_path = assets_path or os.path.join(os.path.dirname(__file__), "assets")
        self.LOGO_FILE = os.path.join(self.assets_path, "AB_small_logo.png")
        self.LOGO_SIZE = 28  # px, tuned to match screenshot
        self.CARD_WIDTH = 420  # right-hand card width
        self._setup_ui()

    # --------------------------- UI ---------------------------
    def _setup_ui(self) -> None:
        self.setObjectName("LoginPage")
        # Background and widget styling tuned to the screenshot
        self.setStyleSheet("""
            QWidget#LoginPage { background-color: #F5E1D2; } /* soft peach */
            QLabel.HeroTitle { font-size: 36px; font-weight: 800; color: #111; }
            QLabel.Subtitle  { font-size: 14px; color: #545454; }
            QLabel.Heading   { font-size: 16px; font-weight: 700; color: #111; }
            QLabel.Field     { font-size: 13px; color: #222; }
            QLineEdit {
                border: 1px solid #E3CDBD;
                border-radius: 8px;
                padding: 10px 12px;
                background: white;
                font-size: 13px;
                selection-background-color: #FFE7CC;
            }
            QPushButton#Primary {
                background-color: #EAD7C0;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: 600;
            }
            QPushButton#Primary:hover { background-color: #DFCBB3; }
            QFrame#Card {
                background: white;
                border-radius: 14px;
            }
        """)

        main = QHBoxLayout(self)
        main.setContentsMargins(28, 24, 28, 24)
        main.setSpacing(24)

        # -------- Left column --------
        left = QVBoxLayout()
        left.setSpacing(10)

        # top row with logo + "SAP Agent"
        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)

        logo_label = QLabel()
        logo_pix = self._load_logo_pixmap()
        if logo_pix:
            logo_label.setPixmap(logo_pix.scaled(self.LOGO_SIZE, self.LOGO_SIZE,
                                                 Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
            logo_label.setFixedSize(self.LOGO_SIZE, self.LOGO_SIZE)
        else:
            # fallback: emoji so layout stays correct if asset is missing
            logo_label.setText("")
            logo_label.setStyleSheet("font-size: 22px;")
        logo_row.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignVCenter)

        sap = QLabel("Audio Agent")
        sap.setObjectName("Heading")
        sap.setStyleSheet("font-size:16px; font-weight:700; color:#111;")
        logo_row.addWidget(sap, 0, Qt.AlignmentFlag.AlignVCenter)
        logo_row.addStretch(1)
        left.addLayout(logo_row)

        title = QLabel("We Don’t Just Implement AI.\nWe Guide Transformation.")
        title.setObjectName("HeroTitle")
        title.setWordWrap(True)
        left.addWidget(title)

        subtitle = QLabel("In a world of AI consultants, dashboards, and automation vendors, Anthrobyte offers something rarer.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        left.addWidget(subtitle)
        left.addStretch(1)

        # -------- Right card --------
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(self.CARD_WIDTH)

        # drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)

        form = QVBoxLayout(card)
        form.setContentsMargins(22, 22, 22, 22)
        form.setSpacing(12)

        # Email
        email_label = QLabel("Email or Username")
        email_label.setObjectName("Field")
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Email or Username…")
        self.input_username.setMinimumHeight(40)

        # Password
        pass_label = QLabel("Password")
        pass_label.setObjectName("Field")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Password")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setMinimumHeight(40)

        # Eye button (trailing)
        eye = QToolButton(self.input_password)
        eye.setCursor(Qt.CursorShape.PointingHandCursor)
        eye.setToolTip("Show/Hide password")
        eye.setIcon(QIcon.fromTheme("view-password"))
        if eye.icon().isNull():
            eye.setText("👁")
        eye.setCheckable(True)
        eye.setAutoRaise(True)
        eye.setFixedSize(28, 20)
        eye.clicked.connect(self._toggle_password)
        # reserve trailing space and reposition
        self.input_password.setTextMargins(0, 0, 28, 0)
        def _resize_event(e, _old=self.input_password.resizeEvent):
            self._reposition_eye(eye)
            if callable(_old):
                _old(e)
        self.input_password.resizeEvent = _resize_event  # type: ignore[assignment]

        # Remember checkbox (optional)
        self.remember = QCheckBox("Remember me")

        # Login button
        self.btn_login = QPushButton("Login")
        self.btn_login.setObjectName("Primary")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)

        # Form layout
        form.addWidget(email_label)
        form.addWidget(self.input_username)
        form.addWidget(pass_label)
        form.addWidget(self.input_password)
        form.addWidget(self.remember)
        form.addSpacing(6)
        # button aligned right
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_login)
        form.addLayout(btn_row)

        # Place left + right
        main.addLayout(left, stretch=2)
        main.addWidget(card, stretch=1, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # final position of eye after geometry exists
        self._reposition_eye(eye)

    def _reposition_eye(self, btn: QToolButton) -> None:
        r = self.input_password.rect()
        btn.move(r.right() - btn.width() - 6, (r.height() - btn.height()) // 2)

    def _toggle_password(self, checked: bool) -> None:
        self.input_password.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _do_login(self) -> None:
        # Defer auth to caller; just accept if inside a QDialog
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        if not username or not password:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing info", "Please enter both username and password.")
            return
        dlg = self.window()
        if isinstance(dlg, QDialog):
            dlg.accept()

    def _load_logo_pixmap(self) -> Optional[QPixmap]:
        try:
            if os.path.exists(self.LOGO_FILE):
                return QPixmap(self.LOGO_FILE)
        except Exception:
            pass
        return None

    # Helper for callers
    def get_credentials(self):
        return self.input_username.text().strip(), self.input_password.text().strip()


class LoginDialog(QDialog):
    """Dialog wrapper exposing get_credentials() for the main app."""
    def __init__(self, parent: Optional[QWidget] = None, assets_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Anthrobyte AI Agent Dashboard")
        self.resize(1100, 700)  # tuned to screenshot canvas size
        self.setModal(True)

        self.page = LoginPage(self, assets_path=assets_path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.page)

    def get_credentials(self):
        return self.page.get_credentials()
