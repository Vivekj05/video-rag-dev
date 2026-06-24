from dotenv import load_dotenv
from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

def run_pipeline(source :str, language :str = "english", session_id: str = None) -> dict:
    print("starting AI Video Assistant")

    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
    collection_name = f"session_{session_id}"

    chunks = process_input(source)

    transcript = transcribe_all(chunks,language)
    print(f"raw transcription (first 300 characters ) {transcript[:300]}")

    with ThreadPoolExecutor(max_workers=6) as executor:
        f_title     = executor.submit(generate_title, transcript)
        f_summary   = executor.submit(summarize, transcript)
        f_actions   = executor.submit(extract_action_items, transcript)
        f_decisions = executor.submit(extract_key_decisions, transcript)
        f_questions = executor.submit(extract_questions, transcript)
        f_rag       = executor.submit(build_rag_chain, transcript, collection_name=collection_name)

        title     = f_title.result()
        summary   = f_summary.result()
        action_item = f_actions.result()
        decisions = f_decisions.result()
        questions = f_questions.result()
        rag_chain = f_rag.result()


    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }

if __name__ == "__main__":
    # CLI entry point
    source = input("Enter YouTube URL or local file path: ").strip()
    language = input("Language (english/hinglish): ").strip() or "english"
    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n📋 Summary:\n{result['summary']}")
    print(f"\n✅ Action Items:\n{result['action_items']}")
    print(f"\n🔑 Key Decisions:\n{result['key_decisions']}")
    print(f"\n❓ Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # Phase 2 — Chat with your meeting via RAG
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")
    rag_chain = result["rag_chain"]
    # Short-term in-memory chat history to improve follow-up coherence.
    chat_history = []  # list of {'role': 'user'|'assistant', 'text': str}
    MAX_HISTORY = 6

    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue

        # append user turn
        chat_history.append({"role": "user", "text": question})

        # build short context from recent turns
        recent = chat_history[-MAX_HISTORY:]
        extra_context = "\n".join(f"{h['role'].capitalize()}: {h['text']}" for h in recent)

        answer = ask_question(rag_chain, question, extra_context=extra_context)

        # append assistant turn
        chat_history.append({"role": "assistant", "text": answer})

        print(f"\n🤖 Assistant: {answer}\n")