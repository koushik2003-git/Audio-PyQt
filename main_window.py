"""
main_window.py
Demo window with two tabs: Dummy and AudioTabWidget (from audio_tab.py)
"""
import sys
import time
from typing import List, Tuple, Optional
from PyQt6 import QtCore, QtWidgets

from utils.logger import get_logger
from ui.audio_tab import AudioTabWidget, EventBridge


# =============================================
# DummyController emits fake diarization via QTimer
# =============================================
class DummyController(QtCore.QObject):
    def __init__(self, parent: Optional[QtCore.QObject] = None, config_path: str = "./config.yaml"):
        super().__init__(parent)
        self.logger = get_logger(config_path=config_path)
        self.bridge: Optional[EventBridge] = None
        self._timer: Optional[QtCore.QTimer] = None
        self._running = False
        self._paused = False
        self._tick = 0

    def set_ui_bridge(self, bridge: EventBridge):
        self.bridge = bridge

    def start_all(self):
        self.logger.info("[DummyController] start_all() called")
        self._running = True
        self._paused = False
        if not self._timer:
            self._timer = QtCore.QTimer(self)
            self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)

    def pause_all(self):
        self.logger.info("[DummyController] pause_all() called")
        self._paused = True

    def resume_all(self):
        self.logger.info("[DummyController] resume_all() called")
        self._paused = False

    def stop_all(self):
        self.logger.info("[DummyController] stop_all() called")
        self._running = False
        if self._timer:
            self._timer.stop()
        if self.bridge:
            self.bridge.emit_final_summary("Final summary: decisions, actions, owners…")

    def _on_tick(self):
        if not self._running or self._paused or not self.bridge:
            return
        self._tick += 1
        ts = time.strftime("%H:%M:%S")
        self.bridge.emit_diarization(
            speaker=f"Speaker {1 + (self._tick % 3)}",
            timestamp=ts,
            language="en",
            aggression=0.1 * (self._tick % 5),
            sentiment=["Neutral", "Positive", "Negative"][self._tick % 3],
        )
        self.bridge.emit_partial_summary(f"Partial summary chunk #{self._tick}: key points captured…")


# =============================================
# Dummy Tab + MainWindow
# =============================================
class DummyTab(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel("This is a dummy tab. Replace with your own content.")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller: DummyController):
        super().__init__()
        self.setWindowTitle("Audio Meeting UI — Demo")
        self.resize(1100, 700)
        self.logger = get_logger()

        tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(tabs)

        tabs.addTab(DummyTab(), "Dummy")
        tabs.addTab(AudioTabWidget(controller=controller, meeting_init_func=self._init_meeting), "Audio")

    def _init_meeting(self, purpose: str, participants: List[str]) -> Tuple[bool, str]:
        self.logger.info(f"[MainWindow] Init meeting | purpose={purpose}, participants={participants}")
        if not purpose:
            return False, "Purpose required"
        if not participants:
            return False, "At least one participant required"
        return True, "OK"


# =============================================
# Entry Point
# =============================================
if __name__ == "__main__":
    logger = get_logger(config_path="../config.yaml")
    app = QtWidgets.QApplication(sys.argv)
    controller = DummyController(config_path="../config.yaml")

    win = MainWindow(controller)
    win.show()
    sys.exit(app.exec())
