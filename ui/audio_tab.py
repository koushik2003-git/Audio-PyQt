"""
audio_tab.py
Reusable PyQt6 Audio Tab widget for meeting-based audio pipelines.
Includes initialization form, live audio controls, diarization, and summary panes.
"""

from typing import Callable, List, Optional, Tuple
from PyQt6 import QtCore, QtGui, QtWidgets
from utils.logger import get_logger


# =============================================
# Thread-safe signal bridge (backend → UI)
# =============================================
class EventBridge(QtCore.QObject):
    diarization_signal = QtCore.pyqtSignal(dict)
    partial_summary_signal = QtCore.pyqtSignal(str)
    final_summary_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._logger = get_logger()

    @QtCore.pyqtSlot(str, str, str, float, str)
    def emit_diarization(self, speaker: str, timestamp: str, language: str, aggression: float, sentiment: str):
        payload = {
            "speaker": speaker,
            "timestamp": timestamp,
            "language": language,
            "aggression": aggression,
            "sentiment": sentiment,
        }
        self._logger.debug(f"[UI Bridge] Emitting diarization: {payload}")
        self.diarization_signal.emit(payload)

    @QtCore.pyqtSlot(str)
    def emit_partial_summary(self, text: str):
        self._logger.debug("[UI Bridge] Emitting partial summary")
        self.partial_summary_signal.emit(text)

    @QtCore.pyqtSlot(str)
    def emit_final_summary(self, text: str):
        self._logger.debug("[UI Bridge] Emitting final summary")
        self.final_summary_signal.emit(text)


# =============================================
# Reusable Audio Tab Widget
# =============================================
class AudioTabWidget(QtWidgets.QWidget):
    """Reusable tab with meeting setup, live control buttons, diarization, and summaries."""

    def __init__(
        self,
        controller: Optional[object] = None,
        meeting_init_func: Optional[Callable[[str, List[str]], Tuple[bool, str]]] = None,
        config_path: str = "./config.yaml",
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.logger = get_logger(config_path)
        self.controller = controller
        self.meeting_init_func = meeting_init_func or self._default_init_func
        self.bridge = EventBridge(self)

        # Link controller to UI bridge
        if self.controller and hasattr(self.controller, "set_ui_bridge"):
            try:
                self.controller.set_ui_bridge(self.bridge)
                self.logger.info("[AudioTab] UI bridge connected to controller.")
            except Exception:
                self.logger.warning("[AudioTab] Controller.set_ui_bridge failed.")

        self._build_ui()
        self._wire_signals()

    # ------------------ UI ------------------
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QtWidgets.QLabel("🎧 Live Audio Meeting")
        title.setFont(QtGui.QFont("Inter", 18, QtGui.QFont.Weight.DemiBold))
        layout.addWidget(title)

        # === Card container ===
        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        card.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 10px; }")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)

        # --- Step 1: Meeting Init ---
        form_box = QtWidgets.QGroupBox("Step 1 · Meeting Details")
        form_layout = QtWidgets.QFormLayout(form_box)
        self.input_purpose = QtWidgets.QLineEdit()
        self.input_purpose.setPlaceholderText("Purpose of meeting (e.g. Weekly Sync)")
        self.input_participants = QtWidgets.QLineEdit()
        self.input_participants.setPlaceholderText("Comma-separated names (e.g. Alice, Bob)")
        self.btn_init = QtWidgets.QPushButton("Initialize Meeting")
        form_layout.addRow("Purpose:", self.input_purpose)
        form_layout.addRow("Participants:", self.input_participants)
        form_layout.addRow("", self.btn_init)

        # --- Step 2: Controls ---
        self.controls_box = QtWidgets.QGroupBox("Step 2 · Controls")
        controls_layout = QtWidgets.QHBoxLayout(self.controls_box)
        self.btn_start_stop = QtWidgets.QPushButton("Start")
        self.btn_start_stop.setCheckable(True)
        self.btn_pause_resume = QtWidgets.QPushButton("Pause")
        self.btn_pause_resume.setCheckable(True)
        self.btn_pause_resume.setEnabled(False)
        self.lbl_status = QtWidgets.QLabel("Status: Idle")
        self.lbl_status.setStyleSheet("color: gray;")
        controls_layout.addWidget(self.btn_start_stop)
        controls_layout.addWidget(self.btn_pause_resume)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.lbl_status)
        self.controls_box.setVisible(False)

        # --- Step 3: Panes ---
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Diarization table
        self.table_diar = QtWidgets.QTableWidget(0, 5)
        self.table_diar.setHorizontalHeaderLabels(["Time", "Speaker", "Language", "Aggression", "Sentiment"])
        self.table_diar.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_diar.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        # Summaries
        right_box = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_box)
        lbl_partial = QtWidgets.QLabel("Partial Summary")
        self.text_partial = QtWidgets.QTextEdit()
        self.text_partial.setReadOnly(True)
        lbl_final = QtWidgets.QLabel("Final Summary (on Stop)")
        self.text_final = QtWidgets.QTextEdit()
        self.text_final.setReadOnly(True)
        right_layout.addWidget(lbl_partial)
        right_layout.addWidget(self.text_partial, 2)
        right_layout.addWidget(lbl_final)
        right_layout.addWidget(self.text_final, 1)

        splitter.addWidget(self.table_diar)
        splitter.addWidget(right_box)
        splitter.setSizes([600, 400])

        # Combine
        card_layout.addWidget(form_box)
        card_layout.addWidget(self.controls_box)
        card_layout.addWidget(splitter)
        layout.addWidget(card)

    def _wire_signals(self):
        self.btn_init.clicked.connect(self._on_initialize_meeting)
        self.btn_start_stop.clicked.connect(self._on_start_stop_toggled)
        self.btn_pause_resume.clicked.connect(self._on_pause_resume_toggled)
        self.bridge.diarization_signal.connect(self._append_diarization_row)
        self.bridge.partial_summary_signal.connect(self._append_partial_summary)
        self.bridge.final_summary_signal.connect(self._show_final_summary)

    # ------------------ Meeting Init ------------------
    def _default_init_func(self, purpose: str, participants: List[str]) -> Tuple[bool, str]:
        if not purpose.strip():
            return False, "Purpose required"
        if not participants:
            return False, "At least one participant required"
        return True, "OK"

    @QtCore.pyqtSlot()
    def _on_initialize_meeting(self):
        purpose = self.input_purpose.text().strip()
        participants = [p.strip() for p in self.input_participants.text().split(",") if p.strip()]
        self.logger.info(f"[AudioTab] Init requested | purpose={purpose} | participants={participants}")
        ok, msg = False, "Unknown error"
        try:
            ok, msg = self.meeting_init_func(purpose, participants)
        except Exception as e:
            msg = f"Initialization failed: {e}"
            self.logger.error(msg, exc_info=True)
        if ok:
            self.controls_box.setVisible(True)
            self.lbl_status.setText("Status: Ready")
            self._flash_message("Meeting initialized successfully.")
        else:
            self._flash_message(msg, error=True)

    # ------------------ Controls ------------------
    @QtCore.pyqtSlot(bool)
    def _on_start_stop_toggled(self, checked: bool):
        try:
            if checked:
                self.btn_start_stop.setText("Stop")
                self.btn_pause_resume.setEnabled(True)
                self.lbl_status.setText("Status: Running")
                if self.controller and hasattr(self.controller, "start_all"):
                    self.controller.start_all()
            else:
                self.btn_start_stop.setText("Start")
                self.btn_pause_resume.setChecked(False)
                self.btn_pause_resume.setEnabled(False)
                self.lbl_status.setText("Status: Stopped")
                if self.controller and hasattr(self.controller, "stop_all"):
                    self.controller.stop_all()
        except Exception as e:
            self.logger.error(f"[AudioTab] Start/Stop error: {e}", exc_info=True)

    @QtCore.pyqtSlot(bool)
    def _on_pause_resume_toggled(self, checked: bool):
        try:
            if checked:
                self.btn_pause_resume.setText("Resume")
                self.lbl_status.setText("Status: Paused")
                if self.controller and hasattr(self.controller, "pause_all"):
                    self.controller.pause_all()
            else:
                self.btn_pause_resume.setText("Pause")
                self.lbl_status.setText("Status: Running")
                if self.controller and hasattr(self.controller, "resume_all"):
                    self.controller.resume_all()
        except Exception as e:
            self.logger.error(f"[AudioTab] Pause/Resume error: {e}", exc_info=True)

    # ------------------ UI Update Slots ------------------
    @QtCore.pyqtSlot(dict)
    def _append_diarization_row(self, payload: dict):
        row = self.table_diar.rowCount()
        self.table_diar.insertRow(row)
        self.table_diar.setItem(row, 0, QtWidgets.QTableWidgetItem(payload.get("timestamp", "")))
        self.table_diar.setItem(row, 1, QtWidgets.QTableWidgetItem(payload.get("speaker", "")))
        self.table_diar.setItem(row, 2, QtWidgets.QTableWidgetItem(payload.get("language", "")))
        self.table_diar.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{payload.get('aggression', 0):.2f}"))
        self.table_diar.setItem(row, 4, QtWidgets.QTableWidgetItem(payload.get("sentiment", "")))
        self.table_diar.scrollToBottom()

    @QtCore.pyqtSlot(str)
    def _append_partial_summary(self, text: str):
        self.text_partial.append(text)
        self.text_partial.verticalScrollBar().setValue(self.text_partial.verticalScrollBar().maximum())

    @QtCore.pyqtSlot(str)
    def _show_final_summary(self, text: str):
        self.text_final.setPlainText(text)
        self._flash_message("Final summary received.")

    def _flash_message(self, text: str, error: bool = False):
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Icon.Critical if error else QtWidgets.QMessageBox.Icon.Information)
        box.setWindowTitle("Audio Tab")
        box.setText(text)
        box.exec()
