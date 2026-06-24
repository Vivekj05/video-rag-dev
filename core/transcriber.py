import os
from pydub import AudioSegment
from typing import List, Dict, Any, Union

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
# SARVAM_PIECE_SECONDS = 25

# SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
# SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")
# SARVAM_MAX_RETRIES = int(os.getenv("SARVAM_MAX_RETRIES", "5"))
# SARVAM_RETRY_BASE_DELAY_SECONDS = float(os.getenv("SARVAM_RETRY_BASE_DELAY_SECONDS", "2"))
# SARVAM_REQUEST_SPACING_SECONDS = float(os.getenv("SARVAM_REQUEST_SPACING_SECONDS", "1"))

from faster_whisper import WhisperModel

_model = None

def load_model():
    global _model
    if _model is None:
        print(f"Loading Whisper model: {WHISPER_MODEL}...")
        _model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16")
        print(f"Model loaded on: cuda")  # add this
    return _model

# def transcribe_chunk_whisper(chunk_path: str, translate_to_english: bool = False) -> Dict[str, Any]:
#     model = load_model()
#     task = "translate" if translate_to_english else "transcribe"
#     result = model.transcribe(chunk_path, task=task)
#     return result
def transcribe_chunk_whisper(chunk_path: str, translate_to_english: bool = False) -> Dict[str, Any]:
    model = load_model()
    task = "translate" if translate_to_english else "transcribe"
    segments, _ = model.transcribe(chunk_path, task=task, beam_size=2, vad_filter=True)
    return {"segments": [{"start": s.start, "text": s.text} for s in segments]}



# def _send_to_sarvam(piece_path: str) -> str:
#     """Send one ≤30s WAV file to Sarvam and return the English transcript."""
#     if not SARVAM_API_KEY:
#         raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

#     headers = {"api-subscription-key": SARVAM_API_KEY}

#     last_error: Exception | None = None
#     for attempt in range(1, SARVAM_MAX_RETRIES + 1):
#         with open(piece_path, "rb") as f:
#             files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
#             data = {"model": SARVAM_MODEL, "with_diarization": "false"}
#             response = requests.post(
#                 SARVAM_STT_TRANSLATE_URL,
#                 headers=headers,
#                 files=files,
#                 data=data,
#                 timeout=120,
#             )

#         if response.ok:
#             return response.json().get("transcript", "")

#         if response.status_code != 429:
#             print(f"\n❌ Sarvam returned {response.status_code}")
#             print(f"Response body: {response.text}\n")
#             response.raise_for_status()

#         retry_after = response.headers.get("Retry-After")
#         if retry_after:
#             try:
#                 delay_seconds = float(retry_after)
#             except ValueError:
#                 delay_seconds = SARVAM_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
#         else:
#             delay_seconds = SARVAM_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))

#         last_error = requests.HTTPError(
#             f"429 Client Error: Too Many Requests for url: {SARVAM_STT_TRANSLATE_URL}"
#         )

#         if attempt < SARVAM_MAX_RETRIES:
#             print(
#                 f"\n⚠️ Sarvam rate limited piece {os.path.basename(piece_path)}; "
#                 f"retrying in {delay_seconds:.1f}s (attempt {attempt}/{SARVAM_MAX_RETRIES})"
#             )
#             time.sleep(delay_seconds)

#     print(f"\n❌ Sarvam kept rate limiting after {SARVAM_MAX_RETRIES} attempts")
#     raise last_error if last_error is not None else requests.HTTPError(
#         f"429 Client Error: Too Many Requests for url: {SARVAM_STT_TRANSLATE_URL}"
#     )

# def transcribe_chunk_sarvam(chunk_path: str) -> str:
#     """
#     Sarvam sync API only accepts ≤30s audio. We split this chunk into
#     25-second pieces, send each separately, and join the transcripts.
#     """
#     if not SARVAM_API_KEY:
#         raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

#     audio = AudioSegment.from_wav(chunk_path)
#     piece_ms = SARVAM_PIECE_SECONDS * 1000

#     full_text = ""
#     total_pieces = (len(audio) + piece_ms - 1) // piece_ms

#     for i, start in enumerate(range(0, len(audio), piece_ms)):
#         piece = audio[start: start + piece_ms]
#         piece_path = f"{chunk_path}_sv_{i}.wav"
#         piece.export(piece_path, format="wav")

#         try:
#             print(f"  → Sarvam piece {i + 1}/{total_pieces} ...")
#             full_text += _send_to_sarvam(piece_path) + " "
#         finally:
#             if os.path.exists(piece_path):
#                 os.remove(piece_path)

#         if SARVAM_REQUEST_SPACING_SECONDS > 0 and i + 1 < total_pieces:
#             time.sleep(SARVAM_REQUEST_SPACING_SECONDS)

#     return full_text.strip()

def transcribe_chunk(chunk_path: str, language: str = "english") -> Union[Dict[str, Any], str]:
    if language.lower() == "hinglish":
        return transcribe_chunk_whisper(chunk_path, translate_to_english=True)
    return transcribe_chunk_whisper(chunk_path)


def _format_ms_to_mmss(ms: int) -> str:
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def transcribe_all(chunks: list, language: str = "english") -> str:

    full_transcript = ""

    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    current_offset_ms = 0

    for i, chunk_path in enumerate(chunks):

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        # measure chunk duration so we can offset segment start/end times
        try:
            audio = AudioSegment.from_file(chunk_path)
            chunk_duration_ms = len(audio)
        except Exception:
            chunk_duration_ms = 0

        result = transcribe_chunk(chunk_path, language=language)

        # Whisper returns a dict with segments; Sarvam returns a plain string.
        if isinstance(result, dict) and "segments" in result:
            for seg in result.get("segments", []):
                # Whisper segments report times in seconds; convert and offset
                seg_start_ms = int(seg.get("start", 0) * 1000) + current_offset_ms
                seg_text = seg.get("text", "").strip()
                timestamp = _format_ms_to_mmss(seg_start_ms)
                full_transcript += f"[{timestamp}] {seg_text} "
        else:
            # Fallback: prefix the chunk's entire text with the chunk start timestamp
            timestamp = _format_ms_to_mmss(current_offset_ms)
            text = result if isinstance(result, str) else str(result)
            full_transcript += f"[{timestamp}] {text} "

        current_offset_ms += chunk_duration_ms

    print("Transcription complete.")

    return full_transcript.strip()
        
