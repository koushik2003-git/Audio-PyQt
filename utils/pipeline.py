import threading
import queue
import time
import pyaudio
import wave
import json
import yaml
import copy
import os
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from utils.logger import get_logger  # Import your dynamic logger
from utils.transcription_assemblyai import transcribe_chunk, summarize_text
from utils.transcription_assemblyai import get_global_state
from utils.evaluator import evaluate_objectives

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
# ============================================================
#  Logger Setup
# ============================================================

# Use the same dynamic config file (edit path as needed)
logger = get_logger("../config.yaml")
logger.info("🔧 Audio processing pipeline initialized.")


# ============================================================
#  Recorder Thread
# ============================================================





# class RecorderThread(threading.Thread):
#     def __init__(self, record_q, stop_event, pause_event, config_path="config.yaml"):
#         super().__init__(daemon=True, name="RecorderThread")
#         self.record_q = record_q
#         self.stop_event = stop_event
#         self.pause_event = pause_event
#         self.config_path = config_path
#         self.logger = get_logger(config_path)

#         # --- Load config dynamically ---
#         import yaml, os
#         with open(config_path, "r") as f:
#             cfg = yaml.safe_load(f) or {}
#         audio_cfg = cfg.get("audio", {})

#         self.rate = int(audio_cfg.get("rate", 16000))
#         self.chunk_size = int(audio_cfg.get("chunk_size", 1024))
#         # ✅ Duration no longer used — recorder runs continuously
#         self.duration = None  

#         self.pa = pyaudio.PyAudio()
#         self.logger.info(
#             f"🎙️ Recorder initialized | rate={self.rate}, chunk_size={self.chunk_size}, duration=dynamic"
#         )

#         self.frames = []  # buffer to hold entire ongoing recording

#     def run(self):
#         """Continuously capture microphone audio until stopped. Flush on pause or stop."""
#         self.logger.info("🎙️ Recorder started.")
#         stream = None
#         try:
#             stream = self.pa.open(
#                 format=pyaudio.paInt16,
#                 channels=1,
#                 rate=self.rate,
#                 input=True,
#                 frames_per_buffer=self.chunk_size,
#             )

#             while not self.stop_event.is_set():
#                 # Wait if paused
#                 if not self.pause_event.is_set():
#                     time.sleep(0.1)
#                     continue

#                 try:
#                     data = stream.read(self.chunk_size, exception_on_overflow=False)
#                     self.frames.append(data)
#                 except IOError as e:
#                     self.logger.warning(f"[Recorder] Buffer overflow: {e}", exc_info=True)

#             # When stop is triggered → flush the final chunk
#             if self.frames:
#                 pcm_data = b"".join(self.frames)
#                 self.record_q.put(pcm_data)
#                 self.logger.info(
#                     f"[Recorder] Captured {len(self.frames)} frames ({len(self.frames) * self.chunk_size / self.rate:.2f}s of audio)."
#                 )

#             self.record_q.put(None)  # signal end

#         except Exception as e:
#             self.logger.error(f"[Recorder] Failed: {e}", exc_info=True)
#         finally:
#             try:
#                 if stream:
#                     stream.stop_stream()
#                     stream.close()
#             except Exception:
#                 pass
#             self.pa.terminate()
#             self.logger.info("🎧 Recorder stopped gracefully.")



class RecorderThread(threading.Thread):
    def __init__(self, record_q, stop_event, pause_event, config_path="config.yaml"):
        super().__init__(daemon=True, name="RecorderThread")
        self.record_q = record_q
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.config_path = config_path
        self.logger = get_logger(config_path)

        # --- Load config dynamically ---
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        audio_cfg = cfg.get("audio", {})

        self.rate = int(audio_cfg.get("rate", 16000))
        self.chunk_size = int(audio_cfg.get("chunk_size", 1024))
        self.duration = float(audio_cfg.get("duration", 5.0))

        self.pa = pyaudio.PyAudio()
        self.logger.info(
            f"🎙️ Recorder initialized | rate={self.rate}, chunk_size={self.chunk_size}, duration={self.duration}s"
        )

    def run(self):
        """Capture microphone audio for fixed-duration chunks and push to record_q."""
        self.logger.info("🎙️ Recorder started.")
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            frames_per_clip = int(self.rate / self.chunk_size * self.duration)
            self.logger.debug(f"[Recorder] Frames per clip: {frames_per_clip}")

            while not self.stop_event.is_set():
                self.pause_event.wait()
                frames = []
                start_time = time.time()

                for _ in range(frames_per_clip):
                    if self.stop_event.is_set():
                        break
                    try:
                        data = stream.read(self.chunk_size, exception_on_overflow=False)
                        frames.append(data)
                    except IOError as e:
                        self.logger.warning(
                            f"[Recorder] Audio buffer overflow: {e}", exc_info=True
                        )

                # Combine frames into one PCM chunk
                if frames:
                    pcm_data = b"".join(frames)
                    self.record_q.put(pcm_data)
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"[Recorder] Captured {len(frames)} frames ({elapsed:.2f}s of audio)."
                    )

            self.record_q.put(None)

        except Exception as e:
            self.logger.error(f"[Recorder] Failed: {e}", exc_info=True)
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            self.pa.terminate()
            self.logger.info("🎧 Recorder stopped gracefully.")



# ============================================================
#  Converter Thread
# ============================================================

class ConverterThread(threading.Thread):
    def __init__(self, record_q, convert_q, stop_event, config_path="config.yaml"):
        super().__init__(daemon=True, name="ConverterThread")
        self.record_q = record_q
        self.convert_q = convert_q
        self.stop_event = stop_event
        self.logger = logger

        # Load audio config
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        audio_cfg = cfg.get("audio", {})
        self.output_dir = audio_cfg.get("output_dir", "temp_audio")
        self.chunk_format = audio_cfg.get("chunk_format", "wav")

        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"[Converter] Output directory set to: {self.output_dir}")

    def _write_wav_file(self, pcm_data: bytes, sample_rate=16000, channels=1, sampwidth=2) -> str:
        """Convert PCM bytes into a WAV file and return its path."""
        timestamp = int(time.time() * 1000)
        file_path = os.path.join(self.output_dir, f"chunk_{timestamp}.{self.chunk_format}")

        try:
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sampwidth)  # 16-bit PCM = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_data)
            self.logger.debug(f"[Converter] Wrote {len(pcm_data)} bytes to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"[Converter] Failed to write WAV file: {e}", exc_info=True)
            return None

    def run(self):
        self.logger.info("🔄 Converter started.")
        try:
            while True:
                chunk = self.record_q.get()
                if chunk is None:
                    self.convert_q.put(None)
                    break

                # Convert PCM bytes → WAV file
                wav_path = self._write_wav_file(chunk)

                if wav_path:
                    self.convert_q.put(wav_path)
        except Exception as e:
            self.logger.error(f"[Converter] Error: {e}", exc_info=True)
        finally:
            self.logger.info("🔚 Converter stopped gracefully.")


def analyze_text_with_openai(text):
    """Analyze sentiment and aggression for a transcript line using OpenAI."""
    if not text.strip():
        return "Neutral", 0.0

    prompt = f"""
    Analyze the emotional tone and aggression level of this meeting line:
    "{text}"

    Return ONLY JSON like:
    {{
      "sentiment": "Positive | Neutral | Negative",
      "aggression_score": 0.0–1.0
    }}
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise language tone analyzer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=100,
        )

        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
            sentiment = data.get("sentiment", "Neutral").capitalize()
            aggression = float(data.get("aggression_score", 0.0))
            aggression = max(0.0, min(1.0, aggression))
            return sentiment, aggression
        except json.JSONDecodeError:
            print("⚠️ Could not parse JSON, raw:", raw)
            return "Neutral", 0.0

    except Exception as e:
        print(f"❌ [OpenAI Sentiment Error]: {e}")
        return "Neutral", 0.0


class TranscriberThread(threading.Thread):
    def __init__(self, convert_q, transcribe_q, stop_event, config_path="config.yaml", ui_queue=None):
        super().__init__(daemon=True, name="TranscriberThread")
        self.convert_q = convert_q
        self.transcribe_q = transcribe_q
        self.stop_event = stop_event
        self.logger = logger
        self.combined_transcript = None
        self.total_offset = 0.0
        self.ui_queue = ui_queue  # ✅ send updates to UI if available

    def run(self):
        self.logger.info("🗣️ Transcriber started.")
        try:
            while True:
                file_path = self.convert_q.get()
                if file_path is None:
                    self.transcribe_q.put(None)
                    break

                # --- Transcribe each chunk ---
                self.total_offset, self.combined_transcript = transcribe_chunk(
                    file_path,
                    total_offset=self.total_offset,
                    combined_transcript=self.combined_transcript
                )

                # --- Send the transcript to summarizer (full dict copy) ---
                if self.combined_transcript:
                    self.transcribe_q.put(copy.deepcopy(self.combined_transcript))

                    # --- Extract last spoken segment (for UI display) ---
                    # --- Extract and push *all* new segments for UI display ---
                try:
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    for speaker, texts in self.combined_transcript.items():
                        # Get last few lines spoken by this speaker (limit to recent 1–2 to avoid flooding)
                        for text in texts[-2:]:
                            if not text.strip():
                                continue

                            # Analyze each line separately
                            sentiment_label, aggression_score = analyze_text_with_openai(text)

                            if self.ui_queue:
                                self.ui_queue.put({
                                    "type": "transcript",
                                    "time": timestamp,
                                    "speaker": speaker,
                                    "language": "en",
                                    "aggression": round(aggression_score, 2),
                                    "sentiment": sentiment_label,
                                    "transcript": text.strip()
                                })

                            self.logger.info(
                                f"[Transcript] {speaker} ({sentiment_label}, {aggression_score:.2f}) → {text}"
                            )

                except Exception as inner_e:
                    self.logger.warning(f"[Transcriber UI update failed]: {inner_e}")

                    # try:
                    #     latest_speaker = list(self.combined_transcript.keys())[-1]
                    #     latest_texts = self.combined_transcript[latest_speaker]
                    #     last_line = latest_texts[-1] if latest_texts else ""
                    #     timestamp = datetime.now().strftime("%H:%M:%S")

                    #     # --- Analyze sentiment/aggression ---
                    #     sentiment_label, aggression_score = analyze_text_with_openai(last_line)

                    #     # --- Push to UI queue ---
                    #     if self.ui_queue:
                    #         self.ui_queue.put({
                    #             "type": "transcript",
                    #             "time": timestamp,
                    #             "speaker": latest_speaker,
                    #             "language": "en",
                    #             "aggression": round(aggression_score, 2),
                    #             "sentiment": sentiment_label,
                    #             "transcript": last_line
                    #         })

                    #     self.logger.info(
                    #         f"[Transcript] {latest_speaker} ({sentiment_label}, {aggression_score:.2f}) → {last_line}"
                    #     )

                    # except Exception as inner_e:
                    #     self.logger.warning(f"[Transcriber UI update failed]: {inner_e}")

        except Exception as e:
            self.logger.error(f"[Transcriber] Error: {e}", exc_info=True)
        finally:
            self.logger.info("📜 Transcriber stopped gracefully.")



# class TranscriberThread(threading.Thread):
#     def __init__(self, convert_q, transcribe_q, stop_event, config_path="config.yaml",ui_queue = None):
#         super().__init__(daemon=True, name="TranscriberThread")
#         self.convert_q = convert_q
#         self.transcribe_q = transcribe_q
#         self.stop_event = stop_event
#         self.logger = logger
#         self.combined_transcript = None   
#         self.total_offset = 0.0
#         self.ui_queue = ui_queue

#     def run(self):
#         self.logger.info("🗣️ Transcriber started.")
#         try:
#             while True:
#                 file_path = self.convert_q.get()
#                 if file_path is None:
#                     # Signal summarizer to finish
#                     self.transcribe_q.put(None)
#                     break

#                 # ✅ Keep accumulating in same transcript dict
#                 self.total_offset, self.combined_transcript = transcribe_chunk(
#                     file_path,
#                     total_offset=self.total_offset,
#                     combined_transcript=self.combined_transcript
#                 )

#                 if self.combined_transcript:
#                     # Push a COPY to summarizer (so summarizer gets full state)
#                     import copy
#                     self.transcribe_q.put(copy.deepcopy(self.combined_transcript))

#         except Exception as e:
#             self.logger.error(f"[Transcriber] Error: {e}", exc_info=True)
#         finally:
#             self.logger.info("📜 Transcriber stopped gracefully.")

            


# ============================================================
#  Summarizer Thread
# ============================================================

class SummarizerThread(threading.Thread):
    def __init__(self, transcribe_q, stop_event, config_path="config.yaml", ui_queue = None):
        super().__init__(daemon=True, name="SummarizerThread")
        self.transcribe_q = transcribe_q
        self.stop_event = stop_event
        self.text_chunks = []
        self.partial_summaries = []  
        self.logger = logger
        self.ui_queue = ui_queue
        # --- Load config dynamically ---
        import yaml, os
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                summarize_cfg = cfg.get("summarizer", {})
                self.partial_interval = int(summarize_cfg.get("partial_interval", 2))
                self.partial_window = int(summarize_cfg.get("partial_window", 2))
            else:
                self.partial_interval = 2
                self.partial_window = 2
        except Exception as e:
            self.logger.warning(f"[Summarizer] Failed to load config: {e}. Using defaults.")
            self.partial_interval = 2
            self.partial_window = 2

                 
        self.logger.info(
            f"[Summarizer] Config loaded | interval={self.partial_interval}, window={self.partial_window}"
        )

    def run(self):
        self.logger.info("🧠 Summarizer started.")
        try:
            while True:
                text = self.transcribe_q.get()
                if text is None:
                    break

                self.text_chunks.append(text)
                self.logger.debug(
                    f"[Summarizer] Added text chunk #{len(self.text_chunks)}"
                )

               
                if len(self.text_chunks) % self.partial_interval == 0:
                    latest_window = self.text_chunks[-self.partial_window:]
                    try:
                       
                        import collections
                        combined_text = ""
                        for chunk in latest_window:
                            if isinstance(chunk, (dict, collections.defaultdict)):
                                for speaker, texts in chunk.items():
                                    combined_text += f"{speaker}: {' '.join(texts)}\n"
                            elif isinstance(chunk, str):
                                combined_text += chunk + "\n"

                        partial_summary = summarize_text(combined_text)
                        self.partial_summaries.append(partial_summary)
                        print(f"\n🟩 [Partial Summary – last {self.partial_window} chunks]\n{partial_summary}\n")

                        if self.ui_queue:
                            print(f"[DEBUG] UI Queue is active: {self.ui_queue is not None}")
                            self.ui_queue.put({
                                "type": "partial",
                                "content": partial_summary
                            })
                        

                        

                        

                        # self.logger.info(
                        #     f"\n🧩 [Partial Summary — last {self.partial_window} chunks]\n{partial_summary}\n"
                        # )

                        


                        objectives = {
                            "Clarify household role-sharing": "Discuss division of household chores and responsibilities.",
                            "Improve communication": "Encourage partners to express their needs.",
                            "Stock market analysis": "Discuss financial trends.",
                            "Space exploration": "Talk about NASA missions."
                
                        }

                        # Run evaluator after each partial summary
                        evaluation_results = evaluate_objectives(objectives, partial_summary)

                        # Print nicely formatted JSON to terminal
                        print("\n📊 Objective Evaluation (current partial summary):")
                        print(json.dumps(evaluation_results, indent=2))


                      
                        # if len(self.partial_summaries) > 1:
                        #     combined_partials = "\n\n".join(self.partial_summaries)
                        #     final_running_summary = summarize_text(combined_partials)
                        #     print(f"\n [Final Summary]{final_running_summary}\n")

                            # try:
                            #     # full_summary_so_far = "\n".join(self.partial_summaries)
                            #     results = evaluate_objectives(self.objectives, final_running_summary)

                            #     if results:
                            #         self.logger.info("\n🎯 [Objective Evaluation]")
                            #         self.logger.info(json.dumps(results, indent=2))
                            # except Exception as e:
                            #     self.logger.error(f"[Objective Evaluation] Failed: {e}", exc_info=True)
                            # self.logger.info(
                            #     f"\n🧭 [Running Combined Summary — {len(self.partial_summaries)} partials]\n{final_running_summary}\n"
                            # )

                            # self.logger.info(
                            #     f"\n🧭 [Final Summary]\n\n"
                            # )

                    except Exception as e:
                        self.logger.error(f"[Summarizer] Partial summary error: {e}", exc_info=True)


                # if len(self.partial_summaries) > 1:
                #     combined_partials = "\n\n".join(self.partial_summaries)
                #     final_running_summary = summarize_text(combined_partials)
                #     print(f"\n [Final Summary]{final_running_summary}\n")

        except Exception as e:
            self.logger.error(f"[Summarizer] Error: {e}", exc_info=True)
        # finally:
         
        #     try:
        #         if len(self.partial_summaries) > 1:
        #             combined_all = "\n\n".join(self.partial_summaries)
        #             final_summary = summarize_text(combined_all)
        #             # self.logger.info(f"\n✅ FINAL COMBINED SUMMARY:\n")

        #             # print("\n==============================")
        #             # print("🧭 FINAL COMBINED SUMMARY")
        #             # print("==============================\n")
        #             # print(final_summary)
        #             # print("\n✅ Session completed successfully.\n")
        #         else:
        #             self.logger.warning("⚠️ No partial summaries to combine.")
            # except Exception as e:
            #     self.logger.error(f"[Summarizer] Final combined summary error: {e}", exc_info=True)

        #     self.logger.info("🧩 Summarizer stopped gracefully.")

    # ==============================================================
    # ✅ Manual Final Summary Trigger
    # ==============================================================
    def generate_final_summary(self):
        """Manually trigger final summary after all partials are complete."""
        try:
            if not self.partial_summaries:     
                print("⚠️ No partial summaries to combine.")
                return

            combined_partials = "\n\n".join(self.partial_summaries)
            final_summary = summarize_text(combined_partials)

            print("\n==============================")
            print("🧭 FINAL COMBINED SUMMARY")
            print("==============================\n")
            print(final_summary)
            
            if self.ui_queue:
                self.ui_queue.put({
                    "type": "final",
                    "content": final_summary
                    })
            print("\n✅ Session completed successfully.\n")

                # Optional: log to file
                # self.logger.info(f"✅ Final Combined Summary:\n{final_summary}\n")

        except Exception as e:
            self.logger.error(f"[Summarizer] Error generating final summary: {e}", exc_info=True)



# ============================================================
#  Pipeline Runner (Optional for testing)
# ============================================================
# if __name__ == "__main__":
#     record_q = queue.Queue()
#     convert_q = queue.Queue()
#     transcribe_q = queue.Queue()

#     stop_event = threading.Event()
#     pause_event = threading.Event()
#     pause_event.set()  # start unpaused

#     threads = [
#         RecorderThread(record_q, stop_event, pause_event),
#         ConverterThread(record_q, convert_q, stop_event),
#         TranscriberThread(convert_q, transcribe_q, stop_event),
#         SummarizerThread(transcribe_q, stop_event),
#     ]

#     for t in threads:
#         t.start()

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         stop_event.set()
#         logger.info("🛑 Graceful shutdown requested by user.")
#         for t in threads:
#             t.join()
#         logger.info("✅ All threads stopped successfully.")
