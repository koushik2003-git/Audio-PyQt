import threading
import queue
import time
import traceback


from utils.pipeline import (
    RecorderThread,
    ConverterThread,
    TranscriberThread,
    SummarizerThread,
)
from utils.logger import get_logger


class MasterController:
    """Manages the full audio processing pipeline (Recorder → Converter → Transcriber → Summarizer)."""

    def __init__(self, config_path: str = "./config.yaml", ui_queue = None):
        # Initialize logger
        self.logger = get_logger(config_path)
        self.config_path = config_path
        self.ui_queue = ui_queue
        self.logger.info("🧩 MasterController initialized with configuration.")

        # Thread synchronization events
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # start unpaused

        # Queues for inter-thread communication
        self.record_q = queue.Queue(maxsize=50)
        self.convert_q = queue.Queue(maxsize=50)
        self.transcribe_q = queue.Queue(maxsize=50)

        # Thread handles
        self.threads = []

    # ======================================================
    # 🟢 Pipeline Lifecycle Methods
    # ======================================================

    def start_all(self):
        """Start all threads in the audio processing pipeline."""
        self.logger.info("🚀 Starting all threads...")
        try:
            self.stop_event.clear()
            self.pause_event.set()

            # Instantiate threads
            self.threads = [
                RecorderThread(self.record_q, self.stop_event, self.pause_event, self.config_path),
                ConverterThread(self.record_q, self.convert_q, self.stop_event, self.config_path),
                TranscriberThread(self.convert_q, self.transcribe_q, self.stop_event, self.config_path, ui_queue= self.ui_queue),
                SummarizerThread(self.transcribe_q, self.stop_event, self.config_path, ui_queue = self.ui_queue),
            ]

            for t in self.threads:
                t.start()
                self.logger.info(f"✅ {t.name} started successfully.")

        except Exception as e:
            self.logger.error(f"❌ Failed to start threads: {e}", exc_info=True)
            self.stop_all()

    def pause_all(self):
        """Temporarily pause audio recording."""
        if not self.pause_event.is_set():
            self.logger.warning("⚠️ Pause requested, but recording is already paused.")
            return
        self.logger.info("⏸️ Pausing recording...")
        self.pause_event.clear()

    def resume_all(self):
        """Resume audio recording."""
        if self.pause_event.is_set():
            self.logger.warning("⚠️ Resume requested, but recording is already active.")
            return
        self.logger.info("▶️ Resuming recording...")
        self.pause_event.set()

    def stop_all(self):
        """Stop all threads and clean up pipeline."""
        self.logger.info("🛑 Stopping all threads...")
        try:
            self.stop_event.set()
            self.pause_event.set()  # unpause in case paused

            # Push None to queues to release waiting threads
            for q in [self.record_q, self.convert_q, self.transcribe_q]:
                q.put(None)

            # Join threads safely
            for t in self.threads:
                if t.is_alive():
                    t.join(timeout=3)
                    self.logger.info(f"🧵 {t.name} stopped successfully.")

            summarizer_thread = next(
                (t for t in self.threads if isinstance(t, SummarizerThread)), None
            )

            if summarizer_thread:
                if summarizer_thread.is_alive():
                    time.sleep(2)
                summarizer_thread.generate_final_summary() 
            else:
                self.logger.warning("No SummarizerThread instance found during shutdown")

            self.threads.clear()
            self.logger.info("✅ All threads stopped cleanly.")
                # ✅ Generate final summary once all threads have finished
            

        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}", exc_info=True)

    # ======================================================
    # 🔍 Status Helpers
    # ======================================================

    def is_running(self) -> bool:
        """Check if any worker thread is currently active."""
        return any(t.is_alive() for t in self.threads)

    def thread_status(self):
        """Return dictionary of current thread states."""
        status = {t.name: t.is_alive() for t in self.threads}
        self.logger.debug(f"[Status] Thread states: {status}")
        return status

    # ======================================================
    # 🧹 Safe Cleanup (for GUI integration)
    # ======================================================

    def safe_shutdown(self):
        """Ensure complete cleanup on application exit."""
        self.logger.info("🔻 Initiating safe shutdown sequence...")
        try:
            self.stop_all()
        except Exception as e:
            self.logger.error(f"Error during safe shutdown: {e}", exc_info=True)
        finally:
            self.logger.info("🧹 MasterController shutdown complete.")


# if __name__ == "__main__":
#     controller = MasterController("./config.yaml")

#     controller.start_all()
#     time.sleep(300)

#     controller.pause_all()
#     time.sleep(3)

#     controller.resume_all()
#     time.sleep(20)

#     controller.stop_all()

    # if __name__ == "__main__":
    #     import sys


    #     controller = MasterController("./config.yaml")

    #     print("\n🎙️ Voice Recording Controller (Interactive Mode)")
    #     print("--------------------------------------------------")
    #     print("Commands:")
    #     print("  ▶️  start  → Start recording")
    #     print("  ⏸️  pause  → Pause recording")
    #     print("  🔁  resume  → Resume recording")
    #     print("  🛑  stop  → Stop and exit")
    #     print("--------------------------------------------------\n")

    #     running = True
    #     while running:
    #         try:
    #             cmd = input("Enter command (s/p/r/x): ").strip().lower()

    #             if cmd == "start":
    #                 controller.start_all()
    #                 print("✅ Recording started.")

    #             elif cmd == "pause":
    #                 controller.pause_all()
    #                 print("⏸️ Recording paused.")

    #             elif cmd == "resume":
    #                 controller.resume_all()
    #                 print("▶️ Recording resumed.")

    #             elif cmd == "stop":
    #                 print("🛑 Stopping all threads...")
    #                 controller.stop_all()
    #                 print("✅ All threads stopped cleanly.")
    #                 running = False

    #             elif cmd == "":
    #                 continue  # Ignore blank input

    #             else:
    #                 print("⚠️ Invalid command. Use s/p/r/x.")

    #         except KeyboardInterrupt:
    #             print("\n🧹 Keyboard interrupt received. Stopping safely...")
    #             controller.stop_all()
    #             running = False
    #         except Exception as e:
    #             print(f"❌ Error: {e}")
    #             controller.stop_all()
    #             running = False

    #     print("👋 Exiting gracefully.")

