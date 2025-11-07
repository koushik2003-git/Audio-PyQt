import os
import threading
import requests
from io import BytesIO
from datetime import timedelta
from collections import defaultdict
from elevenlabs.client import ElevenLabs
from openai import OpenAI
import os
from dotenv import load_dotenv
import elevenlabs

load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
global_state_lock = threading.Lock()

global_state = {
    "total_offset": 0.0
}

def update_global_state(**kwargs):
    """Thread-safe update to the shared state."""
    with global_state_lock:
        global_state.update(kwargs)

def get_global_state():
    """Return a snapshot of the current global state."""
    with global_state_lock:
        return dict(global_state)


def format_timestamp(seconds: float) -> str:
    """Convert seconds into HH:MM:SS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"




def transcribe_chunk(file_path, total_offset=None, combined_transcript=None, language="eng", diarize=True):
    """Transcribe one live/dynamic audio chunk and maintain continuous timestamps."""
    if not os.path.exists(file_path):
        print(f"⚠️ File not found:  {file_path}\n")
        return total_offset, combined_transcript

    if combined_transcript is None:
        combined_transcript = defaultdict(list)

    state = get_global_state()
    if total_offset is None:
        total_offset = state.get("total_offset", 0.0)

    with open(file_path, "rb") as f:
        audio_data = BytesIO(f.read())



    print(f"\n🎧 Processing new chunk: {file_path} ...")
    transcription = elevenlabs.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v1",
        language_code=language,
        diarize=diarize,
        tag_audio_events=True,
        timestamps_granularity="word",
    )

    language_code = transcription.language_code or "unknown"

    
    segments = []
    current_speaker, sentence, start_time = None, [], None
    for word in transcription.words:
        if word.type != "word":
            continue
        if current_speaker is None:
            current_speaker, start_time = word.speaker_id, word.start
        if word.speaker_id != current_speaker:
            if sentence:
                end_time = sentence[-1]["end"]
                segments.append({
                    "speaker": current_speaker,
                    "start": start_time,
                    "end": end_time,
                    "text": " ".join(w["text"] for w in sentence)
                })
            sentence, current_speaker, start_time = [], word.speaker_id, word.start
        sentence.append({"text": word.text, "start": word.start, "end": word.end})

    if sentence:
        end_time = sentence[-1]["end"]
        segments.append({
            "speaker": current_speaker,
            "start": start_time,
            "end": end_time,
            "text": " ".join(w["text"] for w in sentence)
        })

    segments.sort(key=lambda x: x["start"])
    # If there are timestamps, update state with the latest timing
    if segments:
        update_global_state(
            chunk_start=segments[0]["start"] + total_offset,
            chunk_end=segments[-1]["end"] + total_offset,
    )


    
    print("\n🗣️ Formatted Transcript (this chunk):\n")
    for seg in segments:
        adjusted_start = seg["start"] + total_offset
        timestamp = format_timestamp(adjusted_start)
        speaker_name = seg["speaker"].replace("speaker_", "Speaker ")
        text = seg["text"].strip()
        print(f'{speaker_name} ({timestamp}, {language_code}): "{text}"')
        combined_transcript[speaker_name].append(text)
        update_global_state(
        current_speaker=speaker_name,
        latest_text=text
    )

    if transcription.words:
        total_offset += transcription.words[-1].end
        update_global_state(total_offset=total_offset)

    return total_offset, combined_transcript




def print_combined_transcript(combined_transcript):
    """Print the combined transcript per speaker."""
    print("\n==============================")
    print("🧩 COMBINED TRANSCRIPT BY SPEAKER")
    print("==============================\n")

    for speaker, texts in combined_transcript.items():
        combined_text = " ".join(texts)
        print(f"{speaker}:\n\"{combined_text}\"\n")




def summarize_text(text, participant_names=None):
    """Generate a structured meeting summary using OpenAI GPT model with hard debug logging."""
    import random, traceback, json

   
    # if not participant_names:
    #     participant_names = [f"Speaker_{i}" for i in range(1, random.randint(3, 6))]

    import re
    if not participant_names:
        speakers_found = sorted(set(re.findall(r"Speaker\s*\d+", text)))
        if speakers_found:
            participant_names = speakers_found
        else:
            participant_names = [f"Speaker_{i}" for i in range(1, random.int(3,6))]


    formatted_names = sorted(list(set(
        [n.replace("speaker_", "Speaker ") if n.lower().startswith("speaker_") else n
         for n in participant_names]
    )))
    name_string = ", ".join(formatted_names)
    count = len(formatted_names)

    # === Prompt ===
    prompt = f"""
You are an expert meeting summarizer and corporate analyst.
Analyze the following meeting transcript and output these 5 sections **in this exact order**:

1. **Agenda** – Extract or infer agenda topics.
2. **Participants ({count})** – The speakers involved in the meeting were: {name_string}.
3. **Key Takeaways** – Main conclusions and learnings.
4. **Follow Up** – Future actions or checkpoints to be done after the meeting.
5. **Action Points** – All specific tasks or next steps discussed.

Output each section clearly labeled and formatted with bullet points where appropriate.
Do not add extra commentary or invented information.

Meeting Transcript:
{text[:8000]}  # ✅ truncate safely to prevent overload
"""

    try:
        print("\n[DEBUG] Calling OpenAI for final summary...")
        response = openai_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "You are a precise and structured meeting summarizer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=60,
        )

        # Try extracting text from response
        # if hasattr(response, "choices") and len(response.choices) > 0:
        #     choice = response.choices[0]
        #     if hasattr(choice, "message") and hasattr(choice.message, "content"):
        #         content = choice.message.content.strip()
        #         if content:
        #             print("\n[DEBUG] Summary content extracted successfully.")
        #             return content
        #         else:
        #             print("⚠️ [DEBUG] Empty message content returned by API.")
        #             return None
        #     else:
        #         print("⚠️ [DEBUG] Missing .message or .content in response. Raw choice:", choice)
        #         return None
        # else:
        #     print("⚠️ [DEBUG] No .choices field found in response.")
        #     return None

        try:
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Failed to extract content: {e}")
            return None


    except Exception as e:
        print("\n❌ [OpenAI Final Summary Error]:", repr(e))
        traceback.print_exc()
        return f"OpenAI API Error: {e}"



def summarize_meeting(combined_transcript):
    """Generate the full meeting summary including all 5 required sections."""
    if not combined_transcript:
        print("⚠️ No conversation data to summarize yet.")
        return

    print("\n==============================")
    print("🧭 STRUCTURED MEETING SUMMARY")
    print("==============================\n")

    
    all_text = ""
    for speaker, texts in combined_transcript.items():
        speaker_text = " ".join(texts)
        all_text += f"{speaker}: {speaker_text}\n"

    # num_participants = len(combined_transcript)
    # summary = summarize_text(all_text, num_participants)
    participant_names = list(combined_transcript.keys())
    summary = summarize_text(all_text, participant_names)

    print(summary)




if __name__ == "__main__":
    print("🎤 Continuous Transcriber + Combined Transcript + Structured Summary\n")

    total_offset = 0.0
    combined_transcript = defaultdict(list)

    
    chunk_files = sorted([
    f for f in os.listdir(".")
    if f.lower().endswith((".wav", ".mp3"))
])


    if not chunk_files:
        print("⚠️ No .wav audio chunks found in this directory.")
    else:
        print(f"🎧 Found {len(chunk_files)} audio chunk(s): {chunk_files}")

        for f in chunk_files:
            total_offset, combined_transcript = transcribe_chunk(f, total_offset, combined_transcript)

        print_combined_transcript(combined_transcript)
        summarize_meeting(combined_transcript)

    print("\n✅ Session completed successfully.\n")
