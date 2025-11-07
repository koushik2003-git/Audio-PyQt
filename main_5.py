import sys
import logging
from random import randint, choice, uniform

from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QAbstractScrollArea, QComboBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QTextOption


from login.login_page import LoginDialog
from login.login_setup import setup_logging, authenticate

from theme import apply_theme
from dotenv import load_dotenv
load_dotenv()
from queue import Queue
from audioMaster import MasterController
import re
from PyQt6.QtGui import QColor




# -------------------------
# Audio module as a QWidget
# -------------------------
class AudioTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio — Extracted Tab")
        self.ui_queue = Queue()
        self.controller = MasterController("./config.yaml", ui_queue = self.ui_queue)
        self._build_ui()

        # Recording state
        self.audio_running = False
        self.audio_stopped = True
        self.audio_counter = 0
        self._last_transcript = None  # track last displayed line to prevent duplicates

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_ui_queue)
        self.update_timer.start(500) 

    # ======================================================
    # 🧱 UI Layout
    # ======================================================
    def _build_ui(self):
        # self.central = QWidget()
        # self.setCentralWidget(self.central)
        # root = QVBoxLayout(self.central)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # --- Title ---
        title = QLabel("💡 Live Audio Meeting")
        title.setObjectName("HeroTitle")
        root.addWidget(title)

        # --- Step 1: Meeting details ---
        step1 = QFrame()
        step1.setProperty("card", True)
        s1 = QVBoxLayout(step1)
        s1.setContentsMargins(16, 16, 16, 16)
        s1.setSpacing(12)

        x = QLabel("Step 1: Meeting Details")
        x.setObjectName("H3")
        s1.addWidget(x)

        row = QHBoxLayout()
        lbl_purp = QLabel("Purpose")
        lbl_purp.setObjectName("FieldLabel")
        lbl_purp.setMinimumWidth(120)
        self.audio_purpose = QLineEdit()
        self.audio_purpose.setPlaceholderText("e.g., quarterly planning")
        self.audio_purpose.setMinimumHeight(40)
        self.audio_purpose.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.audio_purpose.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.audio_purpose.setStyleSheet("padding: 6px 12px;")

        lbl_part = QLabel("Participants")
        lbl_part.setObjectName("FieldLabel")
        lbl_part.setMinimumWidth(120)
        self.audio_participants = QLineEdit()
        self.audio_participants.setPlaceholderText("a,b,c or names/emails")
        self.audio_participants.setMinimumHeight(40)
        self.audio_participants.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row.addWidget(lbl_purp)
        row.addWidget(self.audio_purpose)
        row.addWidget(lbl_part)
        row.addWidget(self.audio_participants)
        s1.addLayout(row)
        root.addWidget(step1)

        # --- Step 2: Controls ---
        step2 = QFrame()
        step2.setProperty("card", True)
        s2 = QVBoxLayout(step2)
        s2.setContentsMargins(16, 16, 16, 16)
        s2.setSpacing(12)
        h = QHBoxLayout()
        h.setSpacing(8)

        self.btn_audio_init = QPushButton("Initialize Meeting")
        self.btn_audio_init.setProperty("secondary", True)
        self.btn_audio_init.clicked.connect(self._audio_init)
        h.addWidget(self.btn_audio_init)

        self.btn_audio_record = QPushButton("Start")
        self.btn_audio_record.setProperty("primary", True)
        self.btn_audio_record.clicked.connect(self._audio_start)
        h.addWidget(self.btn_audio_record)

        self.btn_audio_pause = QPushButton("Pause")
        self.btn_audio_pause.setProperty("secondary", True)
        self.btn_audio_pause.clicked.connect(self._audio_pause_or_resume)
        self.btn_audio_pause.setEnabled(False)
        h.addWidget(self.btn_audio_pause)

        self.btn_audio_stop = QPushButton("Stop")
        self.btn_audio_stop.setProperty("danger", True)
        self.btn_audio_stop.clicked.connect(self._audio_stop)
        self.btn_audio_stop.setEnabled(False)
        h.addWidget(self.btn_audio_stop)

        s2.addLayout(h)

        self.audio_status = QLabel("Status: Ready")
        self.audio_status.setObjectName("Caption")
        ctrl = QHBoxLayout()
        ctrl.addWidget(self.audio_status)
        ctrl.addStretch(1)
        s2.addLayout(ctrl)
        root.addWidget(step2)

        # --- Step 3: Transcript + Summary ---
        top = QHBoxLayout()

        self.audio_table = QTableWidget()
        # self.audio_table.setColumnCount(6)
        # self.audio_table.setHorizontalHeaderLabels(
        #     ["Time", "Speaker", "Language", "Aggression", "Sentiment", "Transcript"]
        # )
        # 🎨 Improved column order and styling
        self.audio_table.setColumnCount(5)
        self.audio_table.setHorizontalHeaderLabels([
            "Transcript",
            "Aggression",
            "Sentiment",
            "Time",
            "Speaker / Language"
        ])

        header = self.audio_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setDefaultSectionSize(150)
        self.audio_table.horizontalHeader().setStretchLastSection(True)
        self.audio_table.setMinimumHeight(260)

        # Subtle clean theme for better readability
        self.audio_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                gridline-color: #f0f0f0;
                selection-background-color: #fef6e4;
                selection-color: #000000;
                font-size: 13px;
                color: #111827;
            }
            QHeaderView::section {
                background-color: #fdf5e6;
                border: 1px solid #dddddd;
                font-weight: bold;
                padding: 6px;
                color: #333333;
            }
            QTableCornerButton::section {
                background-color: #fdf5e6;
                border: 1px solid #dddddd;
            }
        """)



        # Enable scroll bars and adjust behavior
        self.audio_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.audio_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.audio_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.audio_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.audio_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.audio_table.setWordWrap(True)  # Allows multi-line transcript cells

        # Optional: nicer styled scrollbar for consistency
        self.audio_table.horizontalScrollBar().setStyleSheet("""
            QScrollBar:horizontal {
                border: none;
                background: #f8f8f8;
                height: 10px;
                margin: 0px 20px 0px 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #ffb74d;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #ffa726;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
        """)

        # Same for vertical scroll (optional)
        self.audio_table.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: #f8f8f8;
                width: 10px;
                margin: 20px 0px 20px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #ffb74d;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ffa726;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        header = self.audio_table.horizontalHeader()
        header = self.audio_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Transcript → user-resizable
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Aggression
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Sentiment
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Time
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Speaker/Language
        # header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audio_table.setMinimumHeight(260)
        top.addWidget(self.audio_table, 2)

        right_side = QVBoxLayout()
        partial_group = QGroupBox("Partial Summary")
        partial_layout = QVBoxLayout(partial_group)
        self.partial_summary = QTextEdit()
        self.partial_summary.setReadOnly(True)
        partial_layout.addWidget(self.partial_summary)
        right_side.addWidget(partial_group)

        final_group = QGroupBox("Final Summary")
        final_layout = QVBoxLayout(final_group)
        self.final_summary = QTextEdit()
        self.final_summary.setReadOnly(True)
        final_layout.addWidget(self.final_summary)
        right_side.addWidget(final_group)

        top.addLayout(right_side, 1)
        root.addLayout(top)



    # ======================================================
    # 🎛️ Control Logic
    # ======================================================
    def _audio_init(self):
        """Reset UI + state."""
        self.audio_table.setRowCount(0)
        self.partial_summary.clear()
        self.final_summary.clear()
        self.audio_status.setText("Status: Initialized")

        self.btn_audio_record.setEnabled(True)
        self.btn_audio_pause.setEnabled(False)
        self.btn_audio_pause.setText("Pause")
        self.btn_audio_stop.setEnabled(False)
        QMessageBox.information(self, "Meeting Initialized", "Meeting Initialized.")

    def _audio_start(self):
        """Start actual audio recording using MasterController."""
        self.controller.start_all()
        self.audio_running = True
        self.audio_stopped = False
        self.audio_status.setText("Status: Recording started...")
        self.btn_audio_record.setEnabled(False)
        self.btn_audio_pause.setEnabled(True)
        self.btn_audio_stop.setEnabled(True)

    def _audio_pause_or_resume(self):
        if self.audio_running:
            self._audio_pause()
        else:
            self._audio_resume()

    def _audio_pause(self):
        self.controller.pause_all()
        self.audio_running = False
        self.audio_status.setText("Status: Paused")
        self.btn_audio_pause.setText("Resume")

    def _audio_resume(self):
        self.controller.resume_all()
        self.audio_running = True
        self.audio_status.setText("Status: Recording resumed")
        self.btn_audio_pause.setText("Pause")

    def _audio_stop(self):
        """Stop all threads gracefully."""
        self.controller.stop_all()
        self.audio_running = False
        self.audio_stopped = True
        self.audio_status.setText("Status: Stopped")
        self.btn_audio_record.setEnabled(True)
        self.btn_audio_pause.setEnabled(False)
        self.btn_audio_pause.setText("Pause")
        self.btn_audio_stop.setEnabled(False)
        QMessageBox.information(self, "Meeting Ended", "All threads stopped, final summary generated.")


    def _process_ui_queue(self):
        """Fetch backend updates and show them in the UI with formatting."""
        while not self.ui_queue.empty():
            msg = self.ui_queue.get()
            msg_type = msg.get("type")

            # === Handle transcript updates (table) ===
            if msg_type == "transcript":

                transcript = msg.get("transcript", "").strip()

                # 🚫 Skip empty, noise, or duplicate entries
                if not transcript or transcript.lower() in ("<nlb>", "<nlb", "nlb>"):
                    continue
                if hasattr(self, "_last_transcript") and self._last_transcript == transcript:
                    continue
                self._last_transcript = transcript
                row = self.audio_table.rowCount()
                self.audio_table.insertRow(row)

                transcript = msg.get("transcript", "    ")
                aggression = msg.get("aggression", 0.0)
                sentiment = msg.get("sentiment", "Neutral")
                time_val = msg.get("time", "")
                speaker = msg.get("speaker", "")
                language = msg.get("language", "en")

                # === Column 1: Transcript (main text wide) ===
                transcript_item = QTableWidgetItem(transcript)
                self.audio_table.setItem(row, 0, transcript_item)

                # === Column 2: Aggression (color coded) ===
                aggr_item = QTableWidgetItem(str(round(aggression, 2)))
                if aggression >= 0.7:
                    aggr_item.setBackground(QColor(255, 120, 120))   # 🔴 High
                elif aggression >= 0.4:
                    aggr_item.setBackground(QColor(255, 230, 120))   # 🟡 Medium
                else:
                    aggr_item.setBackground(QColor(200, 255, 200))   # 🟢 Calm
                aggr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_table.setItem(row, 1, aggr_item)

                # === Column 3: Sentiment (colored text) ===
                sent_item = QTableWidgetItem(sentiment)
                if sentiment.lower() == "positive":
                    sent_item.setForeground(QColor(0, 128, 0))
                elif sentiment.lower() == "negative":
                    sent_item.setForeground(QColor(200, 0, 0))
                else:
                    sent_item.setForeground(QColor(90, 90, 90))
                sent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_table.setItem(row, 2, sent_item)

                # === Column 4: Time (smaller text) ===
                time_item = QTableWidgetItem(time_val)
                time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                time_item.setForeground(QColor(120, 120, 120))
                self.audio_table.setItem(row, 3, time_item)

                # === Column 5: Speaker + Language ===
                sp_lang = f"{speaker} ({language})"
                speaker_item = QTableWidgetItem(sp_lang)
                speaker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_table.setItem(row, 4, speaker_item)

                self.audio_table.scrollToBottom()
                self.audio_table.setWordWrap(True)
                self.audio_table.resizeRowsToContents()
                continue

            # === Handle summary updates (partial / final) ===
            content = msg.get("content", "").strip()
            if not content:
                continue

            # Convert markdown-style **bold** and newlines → HTML
            formatted = content.replace("\n", "<br>")
            formatted = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", formatted)
            formatted = formatted.replace("- ", "• ")

            if msg_type == "partial":
                self.partial_summary.append(
                    f'<div style="margin-bottom:10px;"><b>🧩 Partial Summary:</b><br>{formatted}</div>'
                )
                self.partial_summary.verticalScrollBar().setValue(
                    self.partial_summary.verticalScrollBar().maximum()
                )

            elif msg_type == "final":
                self.final_summary.append(
                    f'<div style="margin-bottom:10px;"><b>✅ Final Summary:</b><br>{formatted}</div>'
                )
                self.final_summary.verticalScrollBar().setValue(
                    self.final_summary.verticalScrollBar().maximum()
                )


# class AudioTab(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.ui_queue = Queue()
#         self.controller = MasterController("./config.yaml", ui_queue=self.ui_queue)
#         self._build_ui()

#         # Recording state
#         self.audio_running = False
#         self.audio_stopped = True
#         self.audio_counter = 0

#         self.update_timer = QTimer()
#         self.update_timer.timeout.connect(self._process_ui_queue)
#         self.update_timer.start(500)

#     def _build_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(12, 12, 12, 12)
#         layout.setSpacing(12)

#         title = QLabel("💡 Live Audio Meeting")
#         title.setObjectName("HeroTitle")
#         layout.addWidget(title)

#         # --- Meeting Details ---
#         details_frame = QFrame()
#         details_frame.setProperty("card", True)
#         details_layout = QVBoxLayout(details_frame)
#         details_layout.setContentsMargins(16, 16, 16, 16)

#         label = QLabel("Step 1: Meeting Details")
#         label.setObjectName("H3")
#         details_layout.addWidget(label)

#         row = QHBoxLayout()
#         lbl_purpose = QLabel("Purpose")
#         lbl_purpose.setMinimumWidth(120)
#         self.audio_purpose = QLineEdit()
#         self.audio_purpose.setPlaceholderText("e.g., quarterly planning")

#         lbl_part = QLabel("Participants")
#         lbl_part.setMinimumWidth(120)
#         self.audio_participants = QLineEdit()
#         self.audio_participants.setPlaceholderText("a,b,c or names/emails")

#         row.addWidget(lbl_purpose)
#         row.addWidget(self.audio_purpose)
#         row.addWidget(lbl_part)
#         row.addWidget(self.audio_participants)
#         details_layout.addLayout(row)
#         layout.addWidget(details_frame)

#         # --- Controls ---
#         controls = QFrame()
#         controls.setProperty("card", True)
#         c_layout = QVBoxLayout(controls)
#         c_layout.setContentsMargins(16, 16, 16, 16)
#         btn_row = QHBoxLayout()

#         self.btn_audio_init = QPushButton("Initialize Meeting")
#         self.btn_audio_init.setProperty("secondary", True)
#         self.btn_audio_init.clicked.connect(self._audio_init)
#         btn_row.addWidget(self.btn_audio_init)

#         self.btn_audio_record = QPushButton("Start")
#         self.btn_audio_record.setProperty("primary", True)
#         self.btn_audio_record.clicked.connect(self._audio_start)
#         btn_row.addWidget(self.btn_audio_record)

#         self.btn_audio_pause = QPushButton("Pause")
#         self.btn_audio_pause.setProperty("secondary", True)
#         self.btn_audio_pause.clicked.connect(self._audio_pause_or_resume)
#         self.btn_audio_pause.setEnabled(False)
#         btn_row.addWidget(self.btn_audio_pause)

#         self.btn_audio_stop = QPushButton("Stop")
#         self.btn_audio_stop.setProperty("danger", True)
#         self.btn_audio_stop.clicked.connect(self._audio_stop)
#         self.btn_audio_stop.setEnabled(False)
#         btn_row.addWidget(self.btn_audio_stop)

#         c_layout.addLayout(btn_row)
#         self.audio_status = QLabel("Status: Ready")
#         c_layout.addWidget(self.audio_status)
#         layout.addWidget(controls)

#         # --- Transcript + Summaries ---
#         top = QHBoxLayout()

#         self.audio_table = QTableWidget()
#         self.audio_table.setColumnCount(5)
#         self.audio_table.setHorizontalHeaderLabels(["Transcript", "Aggression", "Sentiment", "Time", "Speaker / Language"])
#         header = self.audio_table.horizontalHeader()
#         header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
#         header.setDefaultSectionSize(150)
#         top.addWidget(self.audio_table, 2)

#         right_side = QVBoxLayout()
#         partial_group = QGroupBox("Partial Summary")
#         p_layout = QVBoxLayout(partial_group)
#         self.partial_summary = QTextEdit()
#         self.partial_summary.setReadOnly(True)
#         p_layout.addWidget(self.partial_summary)
#         right_side.addWidget(partial_group)

#         final_group = QGroupBox("Final Summary")
#         f_layout = QVBoxLayout(final_group)
#         self.final_summary = QTextEdit()
#         self.final_summary.setReadOnly(True)
#         f_layout.addWidget(self.final_summary)
#         right_side.addWidget(final_group)

#         top.addLayout(right_side, 1)
#         layout.addLayout(top)

#     # === Controls ===
#     def _audio_init(self):
#         self.audio_table.setRowCount(0)
#         self.partial_summary.clear()
#         self.final_summary.clear()
#         self.audio_status.setText("Status: Initialized")
#         self.btn_audio_record.setEnabled(True)
#         self.btn_audio_pause.setEnabled(False)
#         self.btn_audio_stop.setEnabled(False)
#         QMessageBox.information(self, "Meeting Initialized", "Meeting Initialized.")

#     def _audio_start(self):
#         self.controller.start_all()
#         self.audio_running = True
#         self.audio_stopped = False
#         self.audio_status.setText("Status: Recording started...")
#         self.btn_audio_record.setEnabled(False)
#         self.btn_audio_pause.setEnabled(True)
#         self.btn_audio_stop.setEnabled(True)

#     def _audio_pause_or_resume(self):
#         if self.audio_running:
#             self._audio_pause()
#         else:
#             self._audio_resume()

#     def _audio_pause(self):
#         self.controller.pause_all()
#         self.audio_running = False
#         self.audio_status.setText("Status: Paused")
#         self.btn_audio_pause.setText("Resume")

#     def _audio_resume(self):
#         self.controller.resume_all()
#         self.audio_running = True
#         self.audio_status.setText("Status: Recording resumed")
#         self.btn_audio_pause.setText("Pause")

#     def _audio_stop(self):
#         self.controller.stop_all()
#         self.audio_running = False
#         self.audio_stopped = True
#         self.audio_status.setText("Status: Stopped")
#         self.btn_audio_record.setEnabled(True)
#         self.btn_audio_pause.setEnabled(False)
#         self.btn_audio_stop.setEnabled(False)
#         QMessageBox.information(self, "Meeting Ended", "All threads stopped, final summary generated.")

#     def _process_ui_queue(self):
#         while not self.ui_queue.empty():
#             msg = self.ui_queue.get()
#             msg_type = msg.get("type")

#             if msg_type == "transcript":
#                 row = self.audio_table.rowCount()
#                 self.audio_table.insertRow(row)
#                 transcript = msg.get("transcript", "")
#                 aggression = msg.get("aggression", 0.0)
#                 sentiment = msg.get("sentiment", "Neutral")
#                 time_val = msg.get("time", "")
#                 speaker = msg.get("speaker", "")
#                 language = msg.get("language", "en")

#                 self.audio_table.setItem(row, 0, QTableWidgetItem(transcript))
#                 aggr_item = QTableWidgetItem(str(round(aggression, 2)))
#                 if aggression >= 0.7:
#                     aggr_item.setBackground(QColor(255, 120, 120))
#                 elif aggression >= 0.4:
#                     aggr_item.setBackground(QColor(255, 230, 120))
#                 else:
#                     aggr_item.setBackground(QColor(200, 255, 200))
#                 aggr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#                 self.audio_table.setItem(row, 1, aggr_item)

#                 sent_item = QTableWidgetItem(sentiment)
#                 if sentiment.lower() == "positive":
#                     sent_item.setForeground(QColor(0, 128, 0))
#                 elif sentiment.lower() == "negative":
#                     sent_item.setForeground(QColor(200, 0, 0))
#                 else:
#                     sent_item.setForeground(QColor(90, 90, 90))
#                 sent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#                 self.audio_table.setItem(row, 2, sent_item)

#                 self.audio_table.setItem(row, 3, QTableWidgetItem(time_val))
#                 self.audio_table.setItem(row, 4, QTableWidgetItem(f"{speaker} ({language})"))
#                 self.audio_table.scrollToBottom()
#                 self.audio_table.resizeRowsToContents()
#                 continue

#             content = msg.get("content", "").strip()
#             if not content:
#                 continue

#             formatted = content.replace("\n", "<br>")
#             formatted = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", formatted)
#             formatted = formatted.replace("- ", "• ")

#             if msg_type == "partial":
#                 self.partial_summary.append(f'<b>🧩 Partial Summary:</b><br>{formatted}<br>')
#             elif msg_type == "final":
#                 self.final_summary.append(f'<b>✅ Final Summary:</b><br>{formatted}<br>')


# class AudioPage(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Anthrobyte Audio Dashboard")
#         self._build_ui()

#         # Dummy audio state
#         self.audio_timer = QTimer()
#         self.audio_timer.timeout.connect(self._generate_dummy_audio_data)
#         self.audio_running = False      # True when generating rows
#         self.audio_stopped = True       # True when fully stopped
#         self.audio_counter = 0

#     def _build_ui(self):
#         self.central = QWidget()
#         outer = QVBoxLayout(self)
#         outer.setContentsMargins(0, 0, 0, 0)
#         outer.addWidget(self.central)
#         root = QVBoxLayout(self.central)
#         root.setContentsMargins(12, 12, 12, 12)
#         root.setSpacing(12)

#         # Title
#         title = QLabel("💡 Live Audio Meeting")
#         title.setObjectName("HeroTitle")
#         root.addWidget(title)

#         # Step 1: Meeting Details
#         step1 = QFrame()
#         step1.setProperty("card", True)
#         s1 = QVBoxLayout(step1)
#         s1.setContentsMargins(16, 16, 16, 16)
#         s1.setSpacing(12)

#         x = QLabel("Step 1: Meeting Details")
#         x.setObjectName("H3")
#         s1.addWidget(x)

#         row = QHBoxLayout()
#         lbl_purp = QLabel("Purpose")
#         lbl_purp.setObjectName("FieldLabel")
#         lbl_purp.setMinimumWidth(120)
#         self.audio_purpose = QLineEdit()
#         self.audio_purpose.setPlaceholderText("e.g., quarterly planning")
#         self.audio_purpose.setMinimumHeight(40)
#         self.audio_purpose.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
#         self.audio_purpose.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
#         self.audio_purpose.setStyleSheet("padding: 6px 12px;")

#         lbl_part = QLabel("Participants")
#         lbl_part.setObjectName("FieldLabel")
#         lbl_part.setMinimumWidth(120)
#         self.audio_participants = QLineEdit()
#         self.audio_participants.setPlaceholderText("a,b,c or names/emails")
#         self.audio_participants.setMinimumHeight(40)
#         self.audio_participants.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

#         row.addWidget(lbl_purp)
#         row.addWidget(self.audio_purpose)
#         row.addWidget(lbl_part)
#         row.addWidget(self.audio_participants)
#         s1.addLayout(row)
#         root.addWidget(step1)

#         # Step 2: Controls
#         step2 = QFrame()
#         step2.setProperty("card", True)
#         s2 = QVBoxLayout(step2)
#         s2.setContentsMargins(16, 16, 16, 16)
#         s2.setSpacing(12)
#         h = QHBoxLayout()
#         h.setSpacing(8)

#         self.btn_audio_init = QPushButton("Initialize Meeting")
#         self.btn_audio_init.setProperty("secondary", True)
#         self.btn_audio_init.clicked.connect(self._audio_init)
#         h.addWidget(self.btn_audio_init)

#         self.btn_audio_record = QPushButton("Start")
#         self.btn_audio_record.setProperty("primary", True)
#         self.btn_audio_record.setToolTip("Start or resume the meeting")
#         self.btn_audio_record.clicked.connect(self._audio_start)
#         h.addWidget(self.btn_audio_record)

#         self.btn_audio_pause = QPushButton("Pause")
#         self.btn_audio_pause.setProperty("secondary", True)
#         self.btn_audio_pause.setToolTip("Pause / Resume the meeting")
#         # Toggle handler: same button handles Pause ↔ Resume
#         self.btn_audio_pause.clicked.connect(self._audio_pause_or_resume)
#         self.btn_audio_pause.setEnabled(False)
#         h.addWidget(self.btn_audio_pause)

#         self.btn_audio_stop = QPushButton("Stop")
#         self.btn_audio_stop.setProperty("danger", True)
#         self.btn_audio_stop.setToolTip("Stop the meeting")
#         self.btn_audio_stop.clicked.connect(self._audio_stop)
#         self.btn_audio_stop.setEnabled(False)
#         h.addWidget(self.btn_audio_stop)

#         s2.addLayout(h)

#         self.audio_status = QLabel("Status: Ready")
#         self.audio_status.setObjectName("Caption")
#         ctrl = QHBoxLayout()
#         ctrl.addWidget(self.audio_status)
#         ctrl.addStretch(1)
#         s2.addLayout(ctrl)
#         root.addWidget(step2)

#         # Step 3: Transcripts + Summaries (table left, summaries right)
#         top = QHBoxLayout()

#         self.audio_table = QTableWidget()
#         self.audio_table.setColumnCount(6)
#         self.audio_table.setHorizontalHeaderLabels(
#             ["Time", "Speaker", "Language", "Aggression", "Sentiment", "Transcripts"]
#         )
#         header = self.audio_table.horizontalHeader()
#         header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
#         header.setDefaultSectionSize(120)
#         self.audio_table.horizontalHeader().setStretchLastSection(True)
#         self.audio_table.setMinimumHeight(260)
#         self.audio_table.setStyleSheet(
#             """
#             QTableWidget { background-color: #ffffff; gridline-color: #ececec; border: 1px solid #dddddd; selection-background-color: #f5f5f5; }
#             QHeaderView::section { background-color: #f9f9f9; border: 1px solid #dddddd; padding: 6px; }
#             """
#         )
#         top.addWidget(self.audio_table, 2)

#         right_side = QVBoxLayout()
#         right_side.setSpacing(12)
#         partial_group = QGroupBox("Partial Summary")
#         partial_layout = QVBoxLayout(partial_group)
#         self.partial_summary = QTextEdit()
#         self.partial_summary.setReadOnly(True)
#         partial_layout.addWidget(self.partial_summary)
#         right_side.addWidget(partial_group)

#         final_group = QGroupBox("Final Summary")
#         final_layout = QVBoxLayout(final_group)
#         self.final_summary = QTextEdit()
#         self.final_summary.setReadOnly(True)
#         final_layout.addWidget(self.final_summary)
#         right_side.addWidget(final_group)

#         top.addLayout(right_side, 1)
#         root.addLayout(top)

#     # === Actions ===

#     def _audio_init(self):
#         """Reset the meeting UI/state and show a popup."""
#         self.audio_table.setRowCount(0)
#         self.partial_summary.clear()
#         self.final_summary.clear()
#         self.audio_counter = 0

#         self.audio_running = False
#         self.audio_stopped = True

#         self.audio_status.setText("Status: Initialized")
#         # Buttons after init
#         self.btn_audio_record.setEnabled(True)        # allow starting
#         self.btn_audio_pause.setEnabled(False)        # can't pause until started
#         self.btn_audio_pause.setText("Pause")
#         self.btn_audio_stop.setEnabled(False)

#         # Popup confirmation
#         QMessageBox.information(self, "Meeting Initialized", "Meeting Initialized.")

#     def _audio_start(self):
#         """Start or resume meeting generation."""
#         # If already running and not stopped, ignore
#         if self.audio_running and not self.audio_stopped:
#             return

#         # Start/resume
#         self.audio_running = True
#         self.audio_stopped = False
#         self.audio_status.setText("Status: Started")

#         # Controls
#         self.btn_audio_record.setEnabled(False)   # Start disabled while running
#         self.btn_audio_pause.setEnabled(True)     # can pause/resume now
#         self.btn_audio_pause.setText("Pause")     # ensure label shows Pause when running
#         self.btn_audio_stop.setEnabled(True)

#         # Start timer ticks
#         self.audio_timer.start(1000)

#     def _audio_pause_or_resume(self):
#         """Toggle Pause/Resume based on current state."""
#         if self.audio_running and not self.audio_stopped:
#             # currently running -> pause
#             self._audio_pause()
#         elif (not self.audio_running) and (not self.audio_stopped):
#             # currently paused -> resume via _audio_start
#             self._audio_start()
#         else:
#             # stopped or not initialized; do nothing
#             return

#     def _audio_pause(self):
#         """Pause the meeting immediately; same button becomes Resume."""
#         if not self.audio_running or self.audio_stopped:
#             return

#         self.audio_timer.stop()
#         self.audio_running = False
#         self.audio_status.setText("Status: Paused")

#         # Keep Start disabled; resume will happen on the same Pause/Resume button
#         self.btn_audio_record.setEnabled(False)
#         self.btn_audio_pause.setEnabled(True)
#         self.btn_audio_pause.setText("Resume")
#         self.btn_audio_stop.setEnabled(True)

#     def _audio_stop(self):
#         """Stop the meeting completely and finalize."""
#         if not self.audio_stopped:
#             self.audio_timer.stop()
#             self.audio_running = False
#             self.audio_stopped = True
#             self.audio_status.setText("Status: Stopped")

#             # Controls reset
#             self.btn_audio_record.setEnabled(True)   # allow a fresh start
#             self.btn_audio_pause.setEnabled(False)
#             self.btn_audio_pause.setText("Pause")    # reset label
#             self.btn_audio_stop.setEnabled(False)

#             # Optional log lines
#             self.partial_summary.append("\n<i>System:</i> Meeting ended.")
#             self.final_summary.append(
#                 "<b>Final summary:</b> Meeting completed successfully with decisions and actions noted."
#             )
#         else:
#             return

#     def _generate_dummy_audio_data(self):
#         """Generate a dummy transcript row every second while running."""
#         if not self.audio_running or self.audio_stopped:
#             return

#         self.audio_counter += 1
#         row = self.audio_table.rowCount()
#         self.audio_table.insertRow(row)

#         current_time = QTime.currentTime().toString("HH:mm:ss")
#         speaker = choice(["Speaker 1", "Speaker 2", "Speaker 3"])
#         language = "en"
#         aggression = round(uniform(0.0, 1.0), 2)
#         sentiment = choice(["Positive", "Neutral", "Negative"])
#         transcript_text = f"{speaker}: Dummy transcript line #{self.audio_counter}"

#         self.audio_table.setItem(row, 0, QTableWidgetItem(current_time))
#         self.audio_table.setItem(row, 1, QTableWidgetItem(speaker))
#         self.audio_table.setItem(row, 2, QTableWidgetItem(language))
#         self.audio_table.setItem(row, 3, QTableWidgetItem(str(aggression)))
#         self.audio_table.setItem(row, 4, QTableWidgetItem(sentiment))
#         self.audio_table.setItem(row, 5, QTableWidgetItem(transcript_text))  # NEW

#         self.partial_summary.append(f"<i>{transcript_text}</i>")
#         self.final_summary.setPlainText(f"Running Summary: {self.audio_counter} lines captured...")


# =====================================================
# === Workshop Setup Tab (reordered + gated sections) ==
# =====================================================

# === Workshop / Facilitator Utilities (single-file, no external deps) ===============================
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import uuid, json, os
import os

from openai import OpenAI

# ---------------- Models ----------------
@dataclass
class Person:
    name: str
    email: str
    role: str

@dataclass
class CompanyIntel:
    latest: Optional[str] = None
    financial: Optional[str] = None
    competitors: Optional[str] = None
    extras: List[str] = field(default_factory=list)

@dataclass
class Company:
    name: str = "Acme Inc."
    company_type: str = "General"
    purpose: str = ""
    key_info: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    intel: CompanyIntel = field(default_factory=CompanyIntel)
    people: List[Person] = field(default_factory=list)

# ---------------- OpenAI thin wrapper with offline fallbacks ----------------
class _WSOpenAIClient:
    def __init__(self):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.enabled = bool(OPENAI_API_KEY and OpenAI is not None)
        self.client = OpenAI(api_key=OPENAI_API_KEY) if self.enabled else None

    def _offline_questions(self) -> str:
        cats = ["Strategy","Operations","Risk","Finance","People","Technology"]
        out = [{"category": cats[i%6], "role": ("CEO" if i%3==0 else None),
                "text": f"What are the top {i+1} priorities we must commit to in the next 12 months?"}
               for i in range(12)]
        return json.dumps(out, ensure_ascii=False)

    def _offline_sim(self, n: int) -> str:
        return json.dumps([{"response":"(offline) Concise answer acknowledging strategy and constraints.",
                            "score":0.6} for _ in range(max(1, n))])

    def complete_text(self, prompt: str, model: Optional[str] = None, temperature: float = 0.5) -> str:
        if not self.enabled:
            # heuristics
            if "Generate 10" in prompt or "Generate 10–" in prompt:
                return self._offline_questions()
            if '"response"' in prompt and '"score"' in prompt and "Questions:" in prompt:
                try:
                    part = prompt.split("Questions:",1)[1]
                    start = part.index("["); end = part.rindex("]")+1
                    n = len(json.loads(part[start:end]))
                except Exception:
                    n = 10
                return self._offline_sim(n)
            return "This is an offline placeholder response generated without calling the OpenAI API."
        resp = self.client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role":"system","content":"You are a concise business analyst."},
                      {"role":"user","content":prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content

    def complete_json(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        txt = self.complete_text(prompt, model=model, temperature=temperature)
        a = txt.find("["); b = txt.rfind("]")+1
        if a!=-1 and b!=-1: return txt[a:b]
        a = txt.find("{"); b = txt.rfind("}")+1
        if a!=-1 and b!=-1: return txt[a:b]
        return txt

# ---------------- Generators ----------------
class _WSQuestionGenerator:
    QUESTION_GEN_PROMPT = """
    You are an expert corporate workshop facilitator. Generate 10–14 questions.
    Return STRICT JSON array where each item has fields:
      {{"category": "Strategy|Operations|Risk|Finance|People|Technology",
        "role": "<role or null>",
        "text": "<question text>"}}

    Context:
    Company: {company_name} ({company_type})
    Purpose: {purpose}

    Key Info (bulleted):
    {key_info}

    Objectives (bulleted):
    {objectives}

    Desired Nature of Questions:
    {nature}
    """

    REGEN_FROM_NOTES_PROMPT = """
    You are improving the existing questions using the facilitator's notes. Return a new JSON array with the same format as before.
    Notes:
    {notes}

    Keep the audience roles and categories balanced. Remove duplicates, ensure clarity.
    """

    def __init__(self):
        self.ai = _WSOpenAIClient()

    def _coerce_items(self, data: Any) -> List[dict]:
        if isinstance(data, dict):
            for k in ("items","questions","data"):
                if isinstance(data.get(k), list):
                    data = data[k]
                    break
        if not isinstance(data, list):
            return []
        out: List[dict] = []
        for it in data:
            if isinstance(it, dict):
                out.append({"category": it.get("category","General"),
                            "role": it.get("role"),
                            "text": (it.get("text","") or "").strip() or "(blank)"})
            elif isinstance(it, str):
                out.append({"category":"General","role":None,"text":it.strip()})
            else:
                out.append({"category":"General","role":None,"text":str(it)})
        return out

    def _loads(self, text: str) -> Any:
        a = text.find("["); b = text.rfind("]")+1
        if a!=-1 and b!=-1: text = text[a:b]
        else:
            a = text.find("{"); b = text.rfind("}")+1
            if a!=-1 and b!=-1: text = text[a:b]
        try:
            return json.loads(text)
        except Exception:
            return ["What are the top priorities for the next 12 months?"]

    def generate(self, company: Company, nature: str) -> List[dict]:
        payload = self.QUESTION_GEN_PROMPT.format(
            company_name=company.name,
            company_type=company.company_type,
            purpose=company.purpose,
            key_info="; ".join(company.key_info) or "-",
            objectives="; ".join(company.objectives) or "-",
            nature=nature.strip() or "Strategic alignment, outcomes, risks, feasibility, and change management.",
        )
        raw = self.ai.complete_json(payload, model=None, temperature=0.3)
        data = self._loads(raw)
        return self._coerce_items(data)

    def regenerate_from_notes(self, notes: List[str]) -> List[dict]:
        payload = self.REGEN_FROM_NOTES_PROMPT.format(notes="\n".join(f"- {n}" for n in notes) or "No notes provided.")
        raw = self.ai.complete_json(payload, model=None, temperature=0.3)
        data = self._loads(raw)
        return self._coerce_items(data)

class _WSConversationSimulator:
    SIM_PROMPT = """
    You are simulating a corporate workshop conversation.

    For each question object in the array, produce:
    - "response": 2–3 sentence realistic answer from that role (or general audience).
    - "score": a float 0.0–1.0 indicating how well the response addresses the question:
      1.0 fully aligned and insightful; 0.5 partially aligned; 0.0 off-topic.

    Return STRICT JSON array, mirroring input order, where each item is:
    {"response":"...", "score":0.0}
    """
    def __init__(self):
        self.ai = _WSOpenAIClient()

    def simulate(self, company: Company, questions: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        prompt = self.SIM_PROMPT + "\\n\\nCompany Context:\\n" + json.dumps(asdict(company), ensure_ascii=False) + \
                 "\\n\\nQuestions:\\n" + json.dumps(questions, ensure_ascii=False)
        raw = self.ai.complete_json(prompt, temperature=0.2)
        a = raw.find("["); b = raw.rfind("]")+1
        if a!=-1 and b!=-1: raw = raw[a:b]
        try:
            return json.loads(raw)
        except Exception:
            return [{"response":"(offline) constructive discussion noted.","score":0.6} for _ in questions]

# === Re-implement WorkshopSetupTab using the utilities above (keeps theme/QSS) =====================
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QFrame, QLabel, QSizePolicy, QMessageBox, QScrollArea
from PyQt6.QtCore import Qt

class CollapsibleQuestion(QWidget):
    """Expandable card for editing question + notes (Streamlit style)."""
    def __init__(self, qid, category, role, text, score=0.0, notes="", parent=None):
        super().__init__(parent)
        self.qid = qid
        self.category = category
        self.role = role
        self.text_value = text
        self.score = score
        self.notes_value = notes

        layout = QVBoxLayout(self)
        self.header_btn = QPushButton(f"[{category}] {role or ''} | Score: {score:.2f}")
        self.header_btn.setCheckable(True)
        self.header_btn.setChecked(False)
        self.header_btn.setStyleSheet("""
        QPushButton {
            text-align: left;
            background-color: #ffffff;      /* white middle */
            color: #111827;                 /* black text */
            border: 2px solid #f97316;      /* theme border (orange) */
            border-radius: 8px;
            padding: 10px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #fff7ed;      /* subtle orange-50 hover */
        }
        QPushButton:checked {
            background-color: #ffffff;      /* keep white when expanded */
            color: #111827;
            border: 2px solid #f97316;
        }
        """)
        layout.addWidget(self.header_btn)

        self.body = QFrame()
        self.body.setVisible(False)
        self.body.setStyleSheet("""
        QFrame {
            background-color: #ffffff;
            border: 2px solid #f97316;      /* theme border */
            border-top: none;               /* visually merges with header */
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            padding: 8px;
        }
        QLabel, QTextEdit {
            color: #111827;                 /* black text */
        }
    """)
        body_layout = QVBoxLayout(self.body)
        body_layout.addWidget(QLabel("Edit Question"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        body_layout.addWidget(self.text_edit)

        body_layout.addWidget(QLabel("Facilitator Notes (optional)"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(notes)
        body_layout.addWidget(self.notes_edit)

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setStyleSheet("background-color:#2563eb;color:white;border-radius:6px;padding:6px 12px;font-weight:600;")
        body_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.body)

        self.header_btn.toggled.connect(lambda checked: self.body.setVisible(checked))
        self.save_btn.clicked.connect(self._on_save)

    def _on_save(self):
        self.text_value = self.text_edit.toPlainText().strip()
        self.notes_value = self.notes_edit.toPlainText().strip()
        QMessageBox.information(self, "Saved", f"✅ Question saved:\n\n{self.text_value}")


class WorkshopSetupTab(QWidget):
    def __init__(self):
        super().__init__()

        self.roles = ["CEO","CFO","CTO","COO","CHRO","CIO","Other"]
        self.qgen = _WSQuestionGenerator()
        self.sim = _WSConversationSimulator()

        root = QVBoxLayout(self)

        # Scoped theme: apply orange to ALL buttons in this tab


        title = QLabel("Workshop Facilitator Agent")
        title.setObjectName("HeroTitle")
        root.addWidget(title)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setSpacing(14)

        # --- Section: Load Sample ---
        s0 = QFrame(); s0.setProperty("card", True); s0l = QHBoxLayout(s0); s0l.setContentsMargins(16,16,16,16)
        btn_sample = QPushButton("Load Sample Data (Rising Pharma)"); btn_sample.setProperty("secondary", True)
        btn_sample.setProperty("secondary", True)
        btn_sample.setMinimumWidth(0)
        btn_sample.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sample.clicked.connect(self._load_sample_and_resize)
        s0l.addWidget(btn_sample); s0l.addStretch(1)
        lay.addWidget(s0)

        # --- Section: Key Info ---
        s1 = QFrame(); s1.setProperty("card", True); s1l = QVBoxLayout(s1); s1l.setContentsMargins(16,16,16,16)
        s1l.addWidget(QLabel("📝 Key Information"))
        g = QHBoxLayout()
        self.in_company = QLineEdit(); self.in_company.setPlaceholderText("Company name")
        self.in_company.setMinimumHeight(34); self.in_company.setMinimumWidth(240)
        self.in_type = QLineEdit(); self.in_type.setPlaceholderText("Type/Industry")
        self.in_type.setMinimumHeight(34); self.in_type.setMinimumWidth(200)
        self.in_purpose = QLineEdit(); self.in_purpose.setPlaceholderText("Purpose")
        self.in_purpose.setMinimumHeight(34); self.in_purpose.setMinimumWidth(240)
        g.addWidget(self.in_company); g.addWidget(self.in_type); g.addWidget(self.in_purpose)
        s1l.addLayout(g)
        g2 = QHBoxLayout(); self.key_input = QLineEdit(); self.key_input.setPlaceholderText("Add a key information item…")
        btn_add_key = QPushButton("Add Key Info"); btn_add_key.clicked.connect(lambda: self._add_to_list(self.key_input, self.key_list))
        btn_add_key.setProperty("secondary", True)
        btn_add_key.setMinimumHeight(28)
        btn_add_key.setCursor(Qt.CursorShape.PointingHandCursor)
        g2.addWidget(self.key_input, 1); g2.addWidget(btn_add_key); s1l.addLayout(g2)
        self.key_list = QTableWidget(0,1); self.key_list.setHorizontalHeaderLabels(["Key Info"]); self.key_list.horizontalHeader().setStretchLastSection(True)
        s1l.addWidget(self.key_list)
        lay.addWidget(s1)

        # --- Section: Objectives ---
        s1b = QFrame(); s1b.setProperty("card", True); s1bl = QVBoxLayout(s1b); s1bl.setContentsMargins(16,16,16,16)
        s1bl.addWidget(QLabel("🎯 Workshop Objectives"))
        g3 = QHBoxLayout(); self.obj_input = QLineEdit(); self.obj_input.setPlaceholderText("Add an objective…")
        btn_add_obj = QPushButton("Add Objective"); btn_add_obj.clicked.connect(lambda: self._add_to_list(self.obj_input, self.obj_list))
        btn_add_obj.setProperty("secondary", True)
        btn_add_obj.setProperty("big", True)
        btn_add_obj.setMinimumHeight(28)
        btn_add_obj.setMinimumWidth(0)
        btn_add_obj.setCursor(Qt.CursorShape.PointingHandCursor)
        g3.addWidget(self.obj_input, 1); g3.addWidget(btn_add_obj); s1bl.addLayout(g3)
        self.obj_list = QTableWidget(0,1); self.obj_list.setHorizontalHeaderLabels(["Objective"]); self.obj_list.horizontalHeader().setStretchLastSection(True)
        s1bl.addWidget(self.obj_list)
        lay.addWidget(s1b)

        # --- Section: Participants ---
        s2 = QFrame(); s2.setProperty("card", True); s2l = QVBoxLayout(s2); s2l.setContentsMargins(16,16,16,16)
        s2l.addWidget(QLabel("👥 Participants"))
        row = QHBoxLayout(); self.p_name = QLineEdit(); self.p_email = QLineEdit(); self.p_role = QComboBox(); self.p_role.addItems(self.roles)
        self.p_name.setMinimumHeight(34);  self.p_name.setMinimumWidth(220)
        self.p_email.setMinimumHeight(34); self.p_email.setMinimumWidth(260)
        self.p_role.setMinimumHeight(34);  self.p_role.setMinimumWidth(160)
        row.addWidget(QLabel("Name")); row.addWidget(self.p_name, 1); row.addWidget(QLabel("Email")); row.addWidget(self.p_email, 1); row.addWidget(QLabel("Role")); row.addWidget(self.p_role, 1)
        btn_add_part = QPushButton("Add Participant"); btn_add_part.clicked.connect(self._add_participant); row.addWidget(btn_add_part)
        btn_add_part.setProperty("secondary", True)
        btn_add_part.setMinimumHeight(28)
        btn_add_part.setCursor(Qt.CursorShape.PointingHandCursor)
        s2l.addLayout(row)
        self.people = QTableWidget(0,3); self.people.setHorizontalHeaderLabels(["Name","Email","Role"]); self.people.horizontalHeader().setStretchLastSection(True)
        s2l.addWidget(self.people)
        # Placeholders (black) that disappear on typing
        self.p_name.setPlaceholderText("John Dee")
        self.p_email.setPlaceholderText("john@company.com")

        # Make Role show a placeholder too (not a pre-selected item)
        self.p_role.setEditable(True)                          # let it show a line-edit
        self.p_role.lineEdit().setPlaceholderText("CEO")       # placeholder text
        self.p_role.setCurrentText("")                         # ensure no item is preselected

        # Scope the placeholder color to just this card
        s2.setStyleSheet("""
        QLineEdit::placeholder { color: #000; }                /* name + email */
        QComboBox QLineEdit::placeholder { color: #000; }      /* role's line-edit */
        """)
        lay.addWidget(s2)

        # --- Section: Additional company info ---
        s3 = QFrame(); s3.setProperty("card", True); s3l = QVBoxLayout(s3); s3l.setContentsMargins(16,16,16,16)
        s3l.addWidget(QLabel("🧰 Additional Company Information"))
        self.notes = QTextEdit(); s3l.addWidget(self.notes)
        btn_add_extra = QPushButton("Add Extra Info"); btn_add_extra.clicked.connect(self._add_extra); s3l.addWidget(btn_add_extra)
        btn_add_extra.setMinimumHeight(28)
        btn_add_extra.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extras = QTableWidget(0,1); self.extras.setHorizontalHeaderLabels(["Notes"]); self.extras.horizontalHeader().setStretchLastSection(True)
        # s3l.addWidget(self.extras)
        # lay.addWidget(s3)

        # --- Section: Web Intelligence ---
        s4 = QFrame(); s4.setProperty("card", True); s4l = QVBoxLayout(s4); s4l.setContentsMargins(16,16,16,16)
        s4l.addWidget(QLabel("🔍 Web intelligence integrations"))
        self.notes = QLabel(); s4l.addWidget(self.notes)
        s4 = QFrame(); s4.setProperty("card", True); 
        s4l = QHBoxLayout(s4); s4l.setContentsMargins(16,16,16,16)
        btn_latest = QPushButton("🌐 Gather Latest Company Info"); btn_fin = QPushButton("💹 Gather Financial Info"); btn_comp = QPushButton("🏢 Gather Competitor Info")
        btn_latest.setProperty("secondary", True)
        btn_fin.setProperty("secondary", True)
        btn_comp.setProperty("secondary", True)

        btn_latest.setMinimumHeight(28); btn_latest.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fin.setMinimumHeight(28);    btn_fin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_comp.setMinimumHeight(28);   btn_comp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_latest.clicked.connect(lambda: self._fetch_intel("latest")); btn_fin.clicked.connect(lambda: self._fetch_intel("financial")); btn_comp.clicked.connect(lambda: self._fetch_intel("competitors"))
        s4l.addWidget(btn_latest); s4l.addWidget(btn_fin); s4l.addWidget(btn_comp)
        lay.addWidget(s4)

        # --- Section: Intelligence Summary ---
        s5 = QFrame(); s5.setProperty("card", True); s5l = QVBoxLayout(s5); s5l.setContentsMargins(16,16,16,16)
        grid = QGridLayout()

        # Create the three output boxes
        self.out_latest = QTextEdit()
        self.out_financial = QTextEdit()
        self.out_comp = QTextEdit()

        # Readability + theme
        for _te in (self.out_latest, self.out_financial, self.out_comp):
            _te.setReadOnly(True)
            _te.setWordWrapMode(QTextOption.WrapMode.WordWrap)
            _te.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            _te.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    color: #F59E0B;                /* theme text color */
                    border: 1px solid #F59E0B;     /* theme border */
                    border-radius: 10px;
                    padding: 10px 12px;
                    font-size: 13px; line-height: 1.28;
                }
            """)

            _te.setMinimumHeight(120)

        # Auto-fit to content
        def _fit_textedit_height(te, min_h=120, max_h=600):
            doc_h = te.document().size().height()
            te.setFixedHeight(int(max(min_h, min(doc_h + 20, max_h))))

        for _te in (self.out_latest, self.out_financial, self.out_comp):
            _te.textChanged.connect(lambda _=None, te=_te: _fit_textedit_height(te))
            _fit_textedit_height(_te)

        # Layout + label alignment
        grid.addWidget(QLabel("Latest:"),      0, 0); grid.addWidget(self.out_latest,    0, 1)
        grid.addWidget(QLabel("Financial:"),   1, 0); grid.addWidget(self.out_financial, 1, 1)
        grid.addWidget(QLabel("Competitors:"), 2, 0); grid.addWidget(self.out_comp,      2, 1)

        # Make labels top-right aligned and stretch the content column
        for _row in range(3):
            lbl = grid.itemAtPosition(_row, 0).widget()
            if isinstance(lbl, QLabel):
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        grid.setColumnMinimumWidth(0, 90)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        s5l.addLayout(grid)


        # Toggle to reveal questions section
        self.btn_toggle_questions = QPushButton("Generate Questions")
        self.btn_toggle_questions.setProperty("secondary", True)
        self.btn_toggle_questions.setMinimumHeight(28)
        self.btn_toggle_questions.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_questions.setCheckable(True)
        self.btn_toggle_questions.setChecked(False)
        self.btn_toggle_questions.clicked.connect(self._toggle_questions_section)
        s5l.addWidget(self.btn_toggle_questions)
        lay.addWidget(s5)

        # --- Section: Generate Questions ---
        s6 = QFrame(); s6.setProperty("card", True); s6l = QVBoxLayout(s6); s6l.setContentsMargins(16,16,16,16)
        s6l.addWidget(QLabel("✏️ Questions & Evaluations"))
        s6l.addWidget(QLabel("Step 1 — Desired Nature of Questions"))

        self.q_nature = QTextEdit()
        self.q_nature.setPlainText("Strategic alignment, outcomes, risks, feasibility, and change management.")
        self.q_nature.setMinimumHeight(60)
        self.q_nature.setStyleSheet("font-size: 14px; padding: 8px; border-radius: 8px;")
        s6l.addWidget(self.q_nature)

        s6l.addWidget(QLabel("✨ Step 2 — Generate Questions (GPT-4o)"))
        # Buttons row
        rows = QHBoxLayout()
        btn_gen = QPushButton("Generate / Refresh Questions")
        btn_clear = QPushButton("Clear Questions")
        btn_gen.setProperty("secondary", True)
        btn_clear.setProperty("secondary", True)
        btn_gen.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_clear.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_gen.clicked.connect(self._generate_questions)
        btn_clear.clicked.connect(self._clear_questions)
        rows.addWidget(btn_gen)
        rows.addWidget(btn_clear)
        s6l.addLayout(rows)

        # --- Step 3: Review & Edit ---
        s6l.addWidget(QLabel("Step 3 — Review & Edit"))

        self.q_table = QTableWidget(0, 5)
        self.q_table.setHorizontalHeaderLabels(["Category", "Role","Question", "Notes", "Save"])
        self.q_table.horizontalHeader().setStretchLastSection(True)

        header = self.q_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.q_table.setWordWrap(True)
        self.q_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.q_table.verticalHeader().setVisible(False)
        self.q_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.q_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e5e7eb;
                border: 1px solid #dddddd;
                selection-background-color: #fef3c7;
                font-size: 13px;
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #e5e7eb;
            }
        """)

        # Let the table determine its own natural height
        self.q_table.setMinimumHeight(120)
        s6l.addWidget(self.q_table)


        # Wrap inside a scroll area for large question sets
        scroll_frame = QFrame()
        scroll_layout = QVBoxLayout(scroll_frame)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(self.q_table)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_frame)
        scroll_area.setMinimumHeight(420)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        s6l.addWidget(scroll_area)


        # s6l.addWidget(self.q_table)

        # Adjust checkboxes
        # self.chk_regen = QCheckBox("Regenerate Questions using Notes")
        self.btn_regen = QPushButton("🔁 Regenerate Questions using Notes")
        self.btn_regen.clicked.connect(self._regenerate_questions)
        s6l.addWidget(self.btn_regen)
        self.chk_approve = QCheckBox("Approve Questions for Evaluation")
        self.chk_approve.toggled.connect(self._update_sim_state)
        self._update_sim_state()
        s6l.addWidget(self.chk_approve)

        # Make the section visible by default
        s6.setVisible(True)
        lay.addWidget(s6)

        
        # --- Step 4: Simulate Conversation & Score ---
        s7 = QFrame(); s7.setProperty("card", True); s7l = QVBoxLayout(s7); s7l.setContentsMargins(16,16,16,16)
        s7l.addWidget(QLabel("Step 4 — Simulate Conversation & Score"))
        row4 = QHBoxLayout()
        self.btn_run_sim = QPushButton("Run Simulation & Scoring (GPT-4o)")
        self.btn_run_sim.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_run_sim.setEnabled(False)
        self.btn_run_sim.clicked.connect(self._simulate)
        row4.addWidget(self.btn_run_sim)
        s7l.addLayout(row4)
        # Info notice below button (matching size/shape)
        self.info_sim_notice = QLabel("Approve questions first to enable simulation.")
        self.info_sim_notice.setProperty("infobox", True)
        self.info_sim_notice.setWordWrap(True)
        self.info_sim_notice.setMinimumHeight(28)
        self.info_sim_notice.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        s7l.addWidget(self.info_sim_notice)
        lay.addWidget(s7)

        # --- Step 5: Download All Data (JSON) ---
        s8 = QFrame(); s8.setProperty("card", True); s8l = QVBoxLayout(s8); s8l.setContentsMargins(16,16,16,16)
        s8l.addWidget(QLabel("Step 5 — Download All Data (JSON)"))
        self.btn_download_all = QPushButton("Download Complete Workshop State (JSON)")
        self.btn_download_all.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_download_all.clicked.connect(self._export_json)
        s8l.addWidget(self.btn_download_all)
        lay.addWidget(s8)
        lay.addStretch(1)
        scroll.setWidget(page)
        root.addWidget(scroll)

        self._apply_initial_table_sizing()
        self.q_table.resizeRowsToContents()
        self.q_table.setMinimumHeight(min(800, self.q_table.verticalHeader().length() + 50))


    def _resize_table_height(self, table: QTableWidget, min_visible_rows: int = 6, max_height: int = 560):
        """Make table tall enough to show most/all content; fall back to smooth scrolling if long."""
        try:
            header_h = table.horizontalHeader().height() if table.horizontalHeader().isVisible() else 0
        except Exception:
            header_h = 0
        row_h = table.verticalHeader().defaultSectionSize()
        rows = table.rowCount()
        desired = header_h + (rows * row_h) + 2 * table.frameWidth() + 12
        lower = header_h + (min_visible_rows * row_h) + 2 * table.frameWidth() + 12
        height = max(lower, min(desired, max_height))
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

    def _apply_initial_table_sizing(self):
        for t in [getattr(self, n) for n in ["key_list","obj_list","people"] if hasattr(self, n)]:
            self._resize_table_height(t)

    def _load_sample_and_resize(self):
        # call original loader
        self._load_sample()
        # then size boxes
        self._apply_initial_table_sizing()


    def _toggle_questions_section(self):
        # Toggle visibility of the questions area (s6)
        # Find the s6 frame by traversing layout children if not stored
        try:
            # We can rely on the kept reference if we store it
            pass
        except Exception:
            pass
        # Locate the s6 frame: last added before stretch (we know it's the previous widget)
        # Safer: walk children and pick the first QFrame that contains "Step 1 — Desired Nature of Questions"
        target = None
        for child in self.findChildren(QFrame):
            if child.property("card") and child.findChild(QLabel, None):
                # crude text check
                labels = child.findChildren(QLabel)
                if any(("Desired Nature of Questions" in (lb.text() or "")) for lb in labels):
                    target = child
                    break
        if target is None:
            return
        vis = target.isVisible()
        target.setVisible(not vis)
        if hasattr(self, "btn_toggle_questions"):
            self.btn_toggle_questions.setText("Hide Questions" if not vis else "Generate Questions")

    
    def _update_sim_state(self):
        ok = self.chk_approve.isChecked() if hasattr(self, "chk_approve") else False
        if hasattr(self, "btn_run_sim"):
            self.btn_run_sim.setEnabled(ok)
        if hasattr(self, "info_sim_notice"):
            self.info_sim_notice.setVisible(not ok)
# ---------------- internal helpers ----------------
    def _add_to_list(self, line: QLineEdit, table: QTableWidget, preset_text: str | None = None):
        t = (preset_text if preset_text is not None else line.text().strip())
        if not t:
            return
        r = table.rowCount(); table.insertRow(r); table.setItem(r,0,QTableWidgetItem(t))
        if preset_text is None:
            line.clear()

    def _add_participant(self):
        name = self.p_name.text().strip(); email = self.p_email.text().strip(); role = self.p_role.currentText()
        if not name or not email:
            QMessageBox.warning(self, "Add Participant", "Name and Email are required."); return
        r = self.people.rowCount(); self.people.insertRow(r)
        self.people.setItem(r,0,QTableWidgetItem(name)); self.people.setItem(r,1,QTableWidgetItem(email)); self.people.setItem(r,2,QTableWidgetItem(role))
        self.p_name.clear(); self.p_email.clear()

    def _add_extra(self):
        t = self.notes.toPlainText().strip()
        if t:
            r = self.extras.rowCount(); self.extras.insertRow(r); self.extras.setItem(r,0,QTableWidgetItem(t)); self.notes.clear()

    def _collect_company(self) -> Company:
        keys = [self.key_list.item(r,0).text() for r in range(self.key_list.rowCount())]
        objs = [self.obj_list.item(r,0).text() for r in range(self.obj_list.rowCount())]
        ppl: List[Person] = []
        for r in range(self.people.rowCount()):
            name = self.people.item(r,0).text() if self.people.item(r,0) else ""
            email = self.people.item(r,1).text() if self.people.item(r,1) else ""
            role = self.people.item(r,2).text() if self.people.item(r,2) else ""
            if name and email: ppl.append(Person(name=name,email=email,role=role))
        extras = [self.extras.item(r,0).text() for r in range(self.extras.rowCount())]
        intel = CompanyIntel(latest=self.out_latest.toPlainText().strip() or None,
                             financial=self.out_financial.toPlainText().strip() or None,
                             competitors=self.out_comp.toPlainText().strip() or None,
                             extras=extras)
        return Company(name=self.in_company.text().strip() or "Acme Inc.",
                       company_type=self.in_type.text().strip() or "General",
                       purpose=self.in_purpose.text().strip(),
                       key_info=keys, objectives=objs, intel=intel, people=ppl)

    def _fetch_intel(self, kind: str):
        ai = _WSOpenAIClient()
        c = self._collect_company()
        if kind == "latest":
            prompt = f"Summarize the most recent public updates (80-140 words) for {c.name} in {c.company_type}. Focus on news, leadership, products, partnerships, strategy."
            self.out_latest.setPlainText(ai.complete_text(prompt))
        elif kind == "financial":
            prompt = f"Provide a financial-style snapshot (80–140 words) for {c.name} ({c.company_type}). Include revenue trend, margins, costs, investments, capital notes."
            self.out_financial.setPlainText(ai.complete_text(prompt))
        else:
            prompt = f"List the 3–5 most relevant competitors for {c.name} ({c.company_type}) and one sentence on differentiation."
            self.out_comp.setPlainText(ai.complete_text(prompt))

    def _save_current_state_to_json(self, filename: str = "workshop_current.json") -> str:
        import json, os

        # --- Collect company info ---
        company = {
            "name": self.in_company.text().strip(),
            "company_type": self.in_type.text().strip(),
            "purpose": self.in_purpose.text().strip(),
            "key_info": [self.key_list.item(r, 0).text() for r in range(self.key_list.rowCount()) if self.key_list.item(r, 0)],
            "objectives": [self.obj_list.item(r, 0).text() for r in range(self.obj_list.rowCount()) if self.obj_list.item(r, 0)]
        }

        # --- Collect participants ---
        people = []
        for r in range(self.people.rowCount()):
            name = self.people.item(r, 0).text() if self.people.item(r, 0) else ""
            email = self.people.item(r, 1).text() if self.people.item(r, 1) else ""
            role = self.people.item(r, 2).text() if self.people.item(r, 2) else ""
            if name or email:
                people.append({"name": name, "email": email, "role": role})

        # --- Collect company intel ---
        intel = {
            "latest": self.out_latest.toPlainText().strip(),
            "financial": self.out_financial.toPlainText().strip(),
            "competitors": self.out_comp.toPlainText().strip(),
            "extras": [self.extras.item(r, 0).text() for r in range(self.extras.rowCount()) if self.extras.item(r, 0)]
        }

        # --- Assemble final structure ---
        data = {
            "company": company,
            "intel": intel,
            "people": people,
            "nature_of_questions": self.q_nature.toPlainText().strip() or "Strategic alignment, outcomes, risks, feasibility, and change management.",
        }

        # --- Write to JSON ---
        out_path = os.path.join(os.getcwd(), filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return out_path

    
    # def _generate_questions(self):
    #     """Generate 5 per role + 5 general_primary + 10 general_backup questions."""
    #     from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

    #     c = self._collect_company()
    #     nature = self.q_nature.toPlainText()
    #     ai = _WSOpenAIClient()

    #     # Save workshop state before generation
    #     data = {
    #         "company": asdict(c),
    #         "nature_of_questions": nature,
    #     }
    #     json_path = os.path.join(os.getcwd(), f"workshop_{c.name.replace(' ', '_')}_session.json")
    #     with open(json_path, "w", encoding="utf-8") as f:
    #         json.dump(data, f, ensure_ascii=False, indent=2)

    #     participants = [p.role for p in c.people if p.role]
    #     if not participants:
    #         QMessageBox.warning(self, "No Roles Found", "Please add participants with roles before generating questions.")
    #         return

    #     grouped_qs = []


    #     general_primary_prompt = f"""
    #     Generate 5 company-wide workshop questions for {c.name}.
    #     Focus on strategy alignment, innovation, compliance, and leadership.
    #     Return JSON with fields: text, category, role (null), score.
    #     """
    #     try:
    #         raw_json = ai.complete_json(general_primary_prompt, model="gpt-4o-mini", temperature=0.4)
    #         gp_qs = json.loads(raw_json)
    #         for q in gp_qs:
    #             q["category"] = "general_primary"
    #             q["role"] = None
    #             q["score"] = 0.0
    #         grouped_qs.append(("General — Primary", gp_qs))
    #     except Exception as e:
    #         print(f"[WARN] General Primary failed: {e}")



    #     # === 1️⃣ Role-specific questions ===
    #     for role in participants:
    #         prompt = f"""
    #         You are an expert corporate workshop facilitator.
    #         Generate exactly 5 strategic, insightful, and distinct questions for the role of {role}
    #         in the following company context:
    #         Company: {c.name} ({c.company_type})
    #         Purpose: {c.purpose}
    #         Key Info: {'; '.join(c.key_info)}
    #         Objectives: {'; '.join(c.objectives)}
    #         Nature of Questions: {nature}
    #         Return only a JSON list of objects with keys: text, category, role, score.
    #         Example: [{{"text": "...", "category": "role", "role": "CEO", "score": 0.0}}, ...]
    #         """

    #         try:
    #             raw_json = ai.complete_json(prompt, model="gpt-4o-mini", temperature=0.4)
    #             role_qs = json.loads(raw_json)
    #             for q in role_qs:
    #                 q["category"] = "role"
    #                 q["role"] = role
    #                 q["score"] = 0.0
    #             grouped_qs.append(("Role-Specific", role_qs))
    #         except Exception as e:
    #             print(f"[WARN] Role generation failed for {role}: {e}")

    #     # === 2️⃣ General — Primary questions ===


    #     # === 3️⃣ General — Backup questions ===
    #     general_backup_prompt = f"""
    #     Generate 10 backup questions for {c.name} that focus on risks, feasibility, change management, and future readiness.
    #     Return JSON with fields: text, category, role (null), score.
    #     """
    #     try:
    #         raw_json = ai.complete_json(general_backup_prompt, model="gpt-4o-mini", temperature=0.2)
    #         gb_qs = json.loads(raw_json)
    #         for q in gb_qs:
    #             q["category"] = "general_backup"
    #             q["role"] = None
    #             q["score"] = 0.0
    #         grouped_qs.append(("General — Backup", gb_qs))
    #     except Exception as e:
    #         print(f"[WARN] General Backup failed: {e}")

    #     # === 🧱 Replace table with grouped tree ===
    #     parent_layout = None
    #     parent = self.q_table.parent()
    #     while parent:
    #         if isinstance(parent.layout(), QVBoxLayout):
    #             parent_layout = parent.layout()
    #             break
    #         parent = parent.parent()
    #     if parent_layout is None:
    #         QMessageBox.warning(self, "Layout Error", "Could not find parent layout for question display.")
    #         return
    #     self.q_table.setParent(None)

    #     self.q_tree = QTreeWidget()
    #     self.q_tree.setHeaderLabels(["Category / Question", "Notes", "Score"])
    #     header = self.q_tree.header()
    #     header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
    #     # Make "Notes" auto-stretch
    #     header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    #     # Keep Score compact
    #     header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    #     header.setStretchLastSection(False)

    #     # Allow in-place editing
    #     self.q_tree.setEditTriggers(QTreeWidget.EditTrigger.DoubleClicked | QTreeWidget.EditTrigger.SelectedClicked)
    #     # self.q_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
    #     # self.q_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    #     # self.q_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    #     self.q_tree.setStyleSheet("""
    #         QTreeWidget {
    #             background-color: #ffffff;
    #             border: 1px solid #dddddd;
    #             font-size: 13px;
    #             color: #111827;                  
    #         }
    #         QHeaderView::section {
    #             background-color: #f9fafb;
    #             font-weight: 600;
    #             padding: 6px;
    #             border: 1px solid #e5e7eb;
    #             color: #111827;
    #         }
    #         QTreeWidget::item { padding: 4px; }
    #     """)

    #     # Populate by category
    #     for category, qset in grouped_qs:
    #         parent_item = QTreeWidgetItem([f"{category} — {len(qset)} Questions", "", ""])
    #         for q in qset:
    #             text = q.get("text", "").strip()
    #             score = f"{float(q.get('score', 0.0)):.2f}"
    #             role = q.get("role") or ""
    #             label = f"[{role}] {text}" if role else text
    #             child = QTreeWidgetItem([label, "", score])
    #             child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
    #             child.setText(1, "Click to add notes…")
    #             parent_item.addChild(child)
    #         self.q_tree.addTopLevelItem(parent_item)

    #     self.q_tree.expandAll()
    #     self.q_tree.setMinimumHeight(min(600, self.q_tree.sizeHint().height() + 100))
    #     parent_layout.addWidget(self.q_tree)
    # def _clear_questions(self):
    #     self.q_table.setRowCount(0); self.chk_approve.setChecked(False)

    def _generate_questions(self):
        """Generate Streamlit-style expandable question editors using OpenAI."""
        import json, os
        from PyQt6.QtWidgets import QLabel

        # --- Collect company context ---
        c = self._collect_company()
        nature = self.q_nature.toPlainText()
        ai = _WSOpenAIClient()

        data = {"company": asdict(c), "nature_of_questions": nature}
        json_path = os.path.join(os.getcwd(), f"workshop_{c.name.replace(' ', '_')}_session.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        participants = [p.role for p in c.people if p.role]
        if not participants:
            QMessageBox.warning(self, "No Roles Found", "Please add participants with roles before generating questions.")
            return

        grouped_qs = []

        # === 1️⃣ General Primary ===
        try:
            gp_prompt = (
                f"You are an expert facilitator. Regenerate 5 company-wide workshop questions for {c.name}. "
                f"Focus on {nature}.\n"
                'Return JSON: [{"text":"...","category":"general_primary","role":null,"score":0.0}]'
            )
            gp_raw = ai.complete_json(gp_prompt, model="gpt-4o-mini", temperature=0.4)
            gp_qs = json.loads(gp_raw)
            for q in gp_qs:
                q["category"] = "general_primary"
                q["role"] = None
                q["score"] = 0.0
            grouped_qs.append(("General — Primary", gp_qs))
        except Exception as e:
            print(f"[WARN] General Primary failed: {e}")

        # === 2️⃣ Role-Specific ===
        for role in participants:
            prompt = f"""
            You are an expert facilitator. Generate 5 strategic questions for the {role} of {c.name}.
            Focus on {nature}.
            Return JSON: [{{"text":"...","category":"role","role":"{role}","score":0.0}}]
            """
            try:
                raw = ai.complete_json(prompt, model="gpt-4o-mini", temperature=0.4)
                role_qs = json.loads(raw)
                for q in role_qs:
                    q["category"] = "role"
                    q["role"] = role
                    q["score"] = 0.0
                grouped_qs.append((f"Role-Specific — {role}", role_qs))
            except Exception as e:
                print(f"[WARN] Role generation failed for {role}: {e}")

        # === 3️⃣ General Backup ===
        try:
            gb_prompt = (
                f"Regenerate 10 backup questions for {c.name}  "
                f"Focus on {nature}\n"
                'Return JSON: [{"text":"...","category":"general_backup","role":null,"score":0.0}]'
            )
            gb_raw = ai.complete_json(gb_prompt, model="gpt-4o-mini", temperature=0.2)
            gb_qs = json.loads(gb_raw)
            for q in gb_qs:
                q["category"] = "general_backup"
                q["role"] = None
                q["score"] = 0.0
            grouped_qs.append(("General — Backup", gb_qs))
        except Exception as e:
            print(f"[WARN] General Backup failed: {e}")

        # --- Remove any previous question area ---
        if hasattr(self, "main_question_scroll"):
            self.main_question_scroll.setParent(None)

        # --- Create Streamlit-like layout ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)

        for group_label, qset in grouped_qs:
            header = QLabel(f"### {group_label}")
            header.setStyleSheet("font-weight:600;font-size:15px;margin-top:10px;")
            container_layout.addWidget(header)

            for i, q in enumerate(qset):
                qid = f"{group_label}_{i}"
                widget = CollapsibleQuestion(
                    qid=qid,
                    category=q.get("category", ""),
                    role=q.get("role", ""),
                    text=q.get("text", ""),
                    score=q.get("score", 0.0),
                    notes=""
                )
                container_layout.addWidget(widget)

        container_layout.addStretch(1)
        scroll.setWidget(container)
        self.main_question_scroll = scroll

        # --- Insert into UI below the "Review & Edit" section ---
        parent_layout = None
        parent = self.q_table.parent()
        while parent:
            if isinstance(parent.layout(), QVBoxLayout):
                parent_layout = parent.layout()
                break
            parent = parent.parent()
        if parent_layout is None:
            QMessageBox.warning(self, "Layout Error", "Could not find parent layout for question display.")
            return

        self.q_table.setParent(None)
        parent_layout.addWidget(scroll)

    def _clear_questions(self):
        """Clear all questions, whether using table or tree view."""
        # Case 1: QTableWidget mode
        if hasattr(self, "q_table") and self.q_table.isVisible():
            self.q_table.setRowCount(0)

        # Case 2: QTreeWidget mode
        if hasattr(self, "q_tree"):
            self.q_tree.clear()

        # Reset approvals
        if hasattr(self, "chk_approve"):
            self.chk_approve.setChecked(False)

        QMessageBox.information(self, "Cleared", "All questions have been cleared.")



    def _add_save_button(self, row: int):
        """Add a Save button to the given row to store edits and notes."""
        btn_save = QPushButton("💾 Save")
        btn_save.setProperty("secondary", True)
        btn_save.clicked.connect(lambda _, r=row: self._save_question_row(r))
        self.q_table.setCellWidget(row, 4, btn_save)

    def _save_question_row(self, row: int):
        """Save question edits and notes for a single row."""
        question = self.q_table.item(row, 2).text().strip() if self.q_table.item(row, 2) else ""
        notes = self.q_table.item(row, 3).text().strip() if self.q_table.item(row, 3) else ""

        # Store it in a temporary in-memory structure
        if not hasattr(self, "_saved_edits"):
            self._saved_edits = []
        self._saved_edits.append({"row": row, "question": question, "notes": notes})

        QMessageBox.information(self, "Saved", f"Row {row+1} saved successfully.")

    def _regenerate_questions(self):
        """Regenerate the questions using facilitator notes and OpenAI."""
        # Collect notes
        #         # Merge saved edits if any
        # if hasattr(self, "_saved_edits") and self._saved_edits:
        #     notes.extend([n["notes"] for n in self._saved_edits if n.get("notes")])

        
        notes = []

        # Case 1: If you are still showing the old table
        if hasattr(self, "q_table") and self.q_table.rowCount() > 0:
            for r in range(self.q_table.rowCount()):
                # Try to get facilitator notes from the text column or a new one
                txt = ""
                if self.q_table.item(r, 2):
                    txt = self.q_table.item(r, 2).text().strip()
                if txt:
                    notes.append(txt)

        # Case 2: If you switched to the QTreeWidget version
        elif hasattr(self, "q_tree"):
            root = self.q_tree.invisibleRootItem()
            for i in range(root.childCount()):
                parent_item = root.child(i)
                for j in range(parent_item.childCount()):
                    child = parent_item.child(j)
                    text = child.text(0).strip()
                    if text:
                        notes.append(text)

        if not notes:
            QMessageBox.warning(self, "No Notes Found", "Please edit or add facilitator notes before regenerating.")
            return

        # Use your question generator (already hooked to OpenAI)
        new_qs = self.qgen.regenerate_from_notes(notes)

        if not new_qs:
            QMessageBox.warning(self, "Regeneration Failed", "No new questions could be generated.")
            return

        # Clear existing questions
        if hasattr(self, "q_table"):
            self.q_table.setRowCount(0)

        # Display new regenerated questions
        self.q_table.setRowCount(len(new_qs))
        self.q_table.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        for i, q in enumerate(new_qs):
            self.q_table.setItem(i, 0, QTableWidgetItem(q.get("category", "")))
            self.q_table.setItem(i, 1, QTableWidgetItem(q.get("role", "")))
            self.q_table.setItem(i, 2, QTableWidgetItem(q.get("text", "")))
            self._add_save_button(i)
        
        for i in range(self.q_table.rowCount()):
            self._add_save_button(i)



        QMessageBox.information(self, "Regeneration Complete", f"{len(new_qs)} new questions have been generated.")


    def _simulate(self):
        if not self.chk_approve.isChecked():
            QMessageBox.information(self, "Approve first", "Approve Questions for Evaluation to enable simulation."); return
        c = self._collect_company()
        payload = []
        for r in range(self.q_table.rowCount()):
            payload.append({
                "category": self.q_table.item(r,0).text() if self.q_table.item(r,0) else "General",
                "role": self.q_table.item(r,1).text() if self.q_table.item(r,1) else None,
                "text": self.q_table.item(r,2).text() if self.q_table.item(r,2) else "",
            })
        res = self.sim.simulate(c, payload)
        for i, r in enumerate(res):
            self.q_table.setItem(i,3,QTableWidgetItem(r.get("response","")))
            self.q_table.setItem(i,4,QTableWidgetItem(f"{float(r.get('score',0.0)):.2f}"))

    def _export_json(self):
        c = self._collect_company()
        questions = []

        # --- Case 1: Using QTableWidget
        if hasattr(self, "q_table") and self.q_table.isVisible() and self.q_table.rowCount() > 0:
            for r in range(self.q_table.rowCount()):
                questions.append({
                    "category": self.q_table.item(r,0).text() if self.q_table.item(r,0) else "",
                    "role": self.q_table.item(r,1).text() if self.q_table.item(r,1) else None,
                    "text": self.q_table.item(r,2).text() if self.q_table.item(r,2) else "",
                    "response": self.q_table.item(r,3).text() if self.q_table.item(r,3) else "",
                    "score": float(self.q_table.item(r,4).text()) if self.q_table.item(r,4) else 0.0
                })

        # --- Case 2: Using Scroll-based CollapsibleQuestion widgets
        elif hasattr(self, "main_question_scroll"):
            scroll_widget = self.main_question_scroll.widget()
            if scroll_widget:
                for cq in scroll_widget.findChildren(CollapsibleQuestion):
                    questions.append({
                        "id": cq.qid,
                        "category": cq.category,
                        "role": cq.role,
                        "text": cq.text_edit.toPlainText().strip(),
                        "notes": cq.notes_edit.toPlainText().strip(),
                        "score": cq.score
                    })

        # --- Assemble final data
        data = {
            "company": asdict(c),
            "question_set": {
                "approved": self.chk_approve.isChecked() if hasattr(self, "chk_approve") else False,
                "questions": questions
            }
        }

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save JSON",
            f"workshop_export_{c.name.replace(' ', '_')}.json",
            "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Export Complete", f"✅ Saved {len(questions)} questions to:\n{path}")

    
    # def _export_json(self):
    #     c = self._collect_company()
    #     questions = []
    #     for r in range(self.q_table.rowCount()):
    #         questions.append({
    #             "category": self.q_table.item(r,0).text() if self.q_table.item(r,0) else "",
    #             "role": self.q_table.item(r,1).text() if self.q_table.item(r,1) else None,
    #             "text": self.q_table.item(r,2).text() if self.q_table.item(r,2) else "",
    #             "response": self.q_table.item(r,3).text() if self.q_table.item(r,3) else "",
    #             "score": float(self.q_table.item(r,4).text()) if self.q_table.item(r,4) else 0.0
    #         })
    #     data = {"company": asdict(c), "question_set":{"approved": self.chk_approve.isChecked(), "questions": questions}}
    #     from PyQt6.QtWidgets import QFileDialog
    #     path, _ = QFileDialog.getSaveFileName(self, "Save JSON", f"workshop_export_{c.name.replace(' ','_')}.json", "JSON (*.json)")
    #     if path:
    #         with open(path, "w", encoding="utf-8") as f:
    #             json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_sample(self):
        """Load workshop data from a JSON file instead of hardcoding."""
        from PyQt6.QtWidgets import QFileDialog
        import json, os

        # Pick file
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Workshop JSON File", "", "JSON Files (*.json)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load JSON: {e}")
            return

        # Extract data safely
        company = data.get("company", {})
        self.in_company.setText(company.get("name", ""))
        self.in_type.setText(company.get("company_type", ""))
        self.in_purpose.setText(company.get("purpose", ""))

        # Clear any old data
        for table in [self.key_list, self.obj_list, self.people]:
            table.setRowCount(0)

        # Fill key info
        for item in company.get("key_info", []):
            self._add_to_list(self.key_input, self.key_list, item)

        # Fill objectives
        for obj in company.get("objectives", []):
            self._add_to_list(self.obj_input, self.obj_list, obj)

        # Fill participants
        # participants = company.get("people") or company.get("participants") or []
        # for p in participants:
        #     r = self.people.rowCount()
        #     self.people.insertRow(r)
        #     self.people.setItem(r, 0, QTableWidgetItem(p.get("name", "")))
        #     self.people.setItem(r, 1, QTableWidgetItem(p.get("email", "")))
        #     self.people.setItem(r, 2, QTableWidgetItem(p.get("role", "")))

        for p in data.get("people", []):
            r = self.people.rowCount()
            self.people.insertRow(r)
            self.people.setItem(r, 0, QTableWidgetItem(p.get("name", "")))
            self.people.setItem(r, 1, QTableWidgetItem(p.get("email", "")))
            self.people.setItem(r, 2, QTableWidgetItem(p.get("role", "")))

        # Resize tables for good display
        self._apply_initial_table_sizing()

        QMessageBox.information(self, "Data Loaded", f"Loaded data for {company.get('name','Unknown Company')}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio & Workshop Setup Dashboard")
        self.setGeometry(100, 100, 1200, 800)

        # Create and style tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)

        # Apply custom tab bar styling for consistent color + height
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #FFF8F3;
                color: #111827;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #E5E7EB;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 30px;      /* increase height + width */
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #F59E0B;     /* Anthrobyte orange */
                color: white;
            }
            QTabBar::tab:hover {
                background: #FFD9A8;
                color: #111;
            }
            QTabWidget::pane {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                top: -1px;
                background: #FFFFFF;
            }
        """)

        self.setCentralWidget(self.tabs)

        # === Audio tab ===
        self.audio_tab = AudioTab()
        self.tabs.addTab(self.audio_tab, "Audio")

        # === Workshop Setup tab ===
        self.workshop_tab = WorkshopSetupTab()
        self.tabs.addTab(self.workshop_tab, "Workshop Setup")


def _login_flow(app: QApplication, logger: logging.Logger) -> bool:
    """Run the login dialog; authenticate up to 3 attempts. Returns True if authenticated."""
    for attempt in range(3):
        dlg = LoginDialog()
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            username, password = dlg.get_credentials()
            if authenticate(username, password):
                logger.info("User '%s' authenticated.", username)
                return True
            else:
                QMessageBox.critical(None, "Login Failed", "Invalid credentials. Try again.")
        else:
            return False
    return False


def main():
    logger = setup_logging()
    app = QApplication(sys.argv)
    apply_theme(app, dark=False)
        # --- Global app-wide button & input styling (consistent across all tabs) ---
    THEME_COLOR = "#F59E0B"   # Anthrobyte orange
    DANGER_COLOR = "#DC2626"  # Red for destructive actions

    app.setStyleSheet(f"""
    /* Base button: white box + theme-colored text */
    QPushButton, QToolButton {{
        background: #FFFFFF;
        color: {THEME_COLOR};
        border: 1px solid {THEME_COLOR};
        border-radius: 10px;
        padding: 6px 12px;
        font-weight: 600;
        min-height: 28px;
    }}
    QPushButton:hover, QToolButton:hover {{ background: #FFF4E5; }}
    QPushButton:pressed, QToolButton:pressed {{ background: #FFE8CC; }}

    
    /* Inputs - rounded, dynamic boxes */
    QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {{
        background: #FFFFFF;
        color: #111827;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 6px 10px;
        min-height: 28px;
    }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border-color: {THEME_COLOR};
        outline: none;
    }}
    /* ComboBox dropdown cleanup */
    QComboBox::drop-down {{ border: 0; width: 26px; }}
    QComboBox::down-arrow {{ width: 12px; height: 12px; }}
/* Filled CTA for emphasis (used in Audio tab 'Start', etc.) */
    QPushButton[primary="true"], QToolButton[primary="true"] {{
        background: {THEME_COLOR};
        color: #FFFFFF;
        border-color: {THEME_COLOR};
    }}
    QPushButton[primary="true"]:hover, QToolButton[primary="true"]:hover {{
        background: #DD8A07;
    }}

    /* Explicit outline style (used in Workshop Setup per your request) */
    QPushButton[secondary="true"], QToolButton[secondary="true"] {{
        background: #FFFFFF;
        color: {THEME_COLOR};
        border-color: {THEME_COLOR};
    }}

    /* Destructive actions */
    QPushButton[danger="true"], QToolButton[danger="true"] {{
        background: #FFFFFF;
        color: {DANGER_COLOR};
        border: 1px solid {DANGER_COLOR};
    }}
    QPushButton[danger="true"]:hover, QToolButton[danger="true"]:{{
        background: #FEE2E2;
    }}

    /* Inputs (kept clean and consistent) */
    QLineEdit, QComboBox {{
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 28px;
    }}
    
 
    
""")
    


    # --- Login ---
    if not _login_flow(app, logger):
        return  # user cancelled or failed

    # --- Main UI ---
    window = MainWindow()
    window.show()

    # --- Run ---
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("Unhandled exception: %s", e)
        QMessageBox.critical(None, "Application Error", str(e))
        sys.exit(1)
