import time
import os
from dotenv import load_dotenv
load_dotenv()

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def check_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            log(f"GPU available: {torch.cuda.get_device_name(0)}")
        else:
            log("WARNING: GPU not available, running on CPU")
    except ImportError:
        log("WARNING: torch not installed, cannot verify GPU")

def run_test(source: str, language: str = "english"):
    total_start = time.time()

    # GPU check
    log("Checking GPU...")
    check_gpu()

    # Step 1: Audio processing
    log("Starting audio processing...")
    t = time.time()
    from utils.audio_processor import process_input
    chunks = process_input(source)
    log(f"Audio processing done — {len(chunks)} chunk(s) — took {time.time()-t:.2f}s")

    # Step 2: Transcription
    log("Starting transcription...")
    t = time.time()
    from core.transcriber import transcribe_all, _model, load_model
    # Force model load and confirm device
    load_model()
    try:
        device = _model.model.device
        log(f"Whisper model loaded on device: {device}")
    except Exception:
        log("Could not confirm Whisper device")
    transcript = transcribe_all(chunks, language)
    log(f"Transcription done — {len(transcript)} chars — took {time.time()-t:.2f}s")

    # Step 3: Title
    log("Generating title...")
    t = time.time()
    from core.summarizer import generate_title
    title = generate_title(transcript)
    log(f"Title done — took {time.time()-t:.2f}s — '{title}'")

    # Step 4: Summary
    log("Generating summary...")
    t = time.time()
    from core.summarizer import summarize
    summary = summarize(transcript)
    log(f"Summary done — took {time.time()-t:.2f}s")

    # Step 5: Action items
    log("Extracting action items...")
    t = time.time()
    from core.extractor import extract_action_items
    actions = extract_action_items(transcript)
    log(f"Action items done — took {time.time()-t:.2f}s")

    # Step 6: Key decisions
    log("Extracting key decisions...")
    t = time.time()
    from core.extractor import extract_key_decisions
    decisions = extract_key_decisions(transcript)
    log(f"Key decisions done — took {time.time()-t:.2f}s")

    # Step 7: Open questions
    log("Extracting open questions...")
    t = time.time()
    from core.extractor import extract_questions
    questions = extract_questions(transcript)
    log(f"Open questions done — took {time.time()-t:.2f}s")

    # Step 8: RAG chain
    log("Building RAG chain (embedding + vector store)...")
    t = time.time()
    from core.rag_engine import build_rag_chain
    rag_chain = build_rag_chain(transcript)
    log(f"RAG chain done — took {time.time()-t:.2f}s")

    # Total
    log(f"TOTAL PIPELINE TIME: {time.time()-total_start:.2f}s")

    print("\n" + "="*60)
    print(f"Title: {title}")
    print(f"\nSummary (first 300 chars):\n{summary[:300]}")
    print(f"\nAction Items (first 300 chars):\n{actions[:300]}")
    print("="*60)

if __name__ == "__main__":
    source = input("Enter YouTube URL or local file path: ").strip()
    language = input("Language (english/hinglish) [default: english]: ").strip() or "english"
    run_test(source, language)