import os
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.vector_store import build_vector_store, load_vector_store, get_retriever

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert assistant. Answer the user's question based ONLY on the transcript context provided below.

If the answer is not found in the context, say: "I could not find this information in the transcript."

Always be concise and precise. If quoting someone, mention it clearly.

After your concise answer, include a short 'Sources:' section listing up to 3 citations in the form [MM:SS] <one-line snippet> drawn from the provided context. If no relevant source exists, write 'Sources: None'.

Context from transcript:
{context}""",
    ),
    ("human", "{question}"),
])

def get_llm():
    _key = os.getenv("MISTRAL_API_KEY")
    api_key = SecretStr(_key) if _key is not None else None
    return ChatMistralAI(
        model_name="mistral-small-latest",
        api_key=api_key,
        temperature=0.3,
    )

def format_docs(docs):
    """Format retrieved docs, preferring explicit metadata timestamps when present."""
    parts = []
    ts_re = __import__('re').compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
    for doc in docs:
        ts = None
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            ts = doc.metadata.get('timestamp')
        if not ts:
            m = ts_re.search(doc.page_content or "")
            ts = m.group(1) if m else None
        if ts:
            parts.append(f"[{ts}] {doc.page_content}")
        else:
            parts.append(doc.page_content)
    return "\n\n".join(parts)


def _retrieve_docs(retriever, question: str):
    """Return retrieved documents across LangChain retriever variants."""
    if retriever is None:
        return []

    # Newer retrievers are Runnable-like and expose invoke().
    if hasattr(retriever, "invoke"):
        docs = retriever.invoke(question)
        return docs or []

    # Older retrievers may expose get_relevant_documents().
    if hasattr(retriever, "get_relevant_documents"):
        docs = retriever.get_relevant_documents(question)
        return docs or []

    # Very old/internal API fallback.
    if hasattr(retriever, "_get_relevant_documents"):
        docs = retriever._get_relevant_documents(question)
        return docs or []

    return []

def build_rag_chain(transcript:str):

    vector_store = build_vector_store(transcript)

    retriever = get_retriever(vector_store, k = 4)

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(

        [(
            "system",
            """You are an expert assistant. Answer the user's question based ONLY on the transcript context provided below.

If the answer is not found in the context, say: "I could not find this information in the transcript."

Always be concise and precise. If quoting someone, mention it clearly.

After your concise answer, include a short 'Sources:' section listing up to 3 citations in the form [MM:SS] <one-line snippet> drawn from the provided context. If no relevant source exists, write 'Sources: None'.

Context from transcript:
{context}""",
        ),
        ("human", "{question}"),
    ]
    )

    #full LCEL Rag pipeline 

    rag_chain = (

        {"context" : retriever | RunnableLambda(format_docs),
         "question": RunnablePassthrough()
         }
         |prompt|llm|StrOutputParser()
    )

    # Return both the runnable chain and the retriever so callers can
    # augment retrieved docs with short-term chat history when needed.
    return {"rag_chain": rag_chain, "retriever": retriever}


def load_rag_chain():
    vector_store = load_vector_store()
    retriever = get_retriever(vector_store, k=4)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert assistant. Answer the user's question based ONLY on the transcript context provided below.

If the answer is not found in the context, say: "I could not find this information in the transcript."

Always be concise and precise. If quoting someone, mention it clearly.

After your concise answer, include a short 'Sources:' section listing up to 3 citations in the form [MM:SS] <one-line snippet> drawn from the provided context. If no relevant source exists, write 'Sources: None'.

Context from transcript:
{context}""",
        ),
        ("human", "{question}"),
    ])

    rag_chain = (
        {
            "context":  retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return {"rag_chain": rag_chain, "retriever": retriever}


def ask_question(rag_chain, question: str, extra_context: str | None = None) -> str:
    """Ask a question using the provided RAG chain.

    If `extra_context` is provided it will be passed as the `context` input
    to the runnable to augment retrieved documents (useful for short-term chat history).
    """
    print(f"Question : {question}")

    # Support two shapes for rag_chain: the old-style runnable, or the
    # new dict containing {'rag_chain': runnable, 'retriever': retriever}.
    chain = rag_chain
    retriever = None
    if isinstance(rag_chain, dict) and 'rag_chain' in rag_chain:
        chain = rag_chain['rag_chain']
        retriever = rag_chain.get('retriever')

    # Build an explicit context block so the model sees both transcript evidence
    # and recent chat turns, without passing a dict into the retriever chain.
    if retriever:
        try:
            docs = _retrieve_docs(retriever, question)
            context = format_docs(docs)
            if extra_context:
                context = context + "\n\nChat history:\n" + extra_context

            llm = get_llm()
            answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
            answer = answer_chain.invoke({"context": context, "question": question})
        except Exception as exc:
            print("RAG answer path failed, falling back:", exc)
            try:
                answer = chain.invoke(question)
            except Exception:
                answer = chain.invoke({"question": question})
    else:
        # Fallback for older callers: use the runnable chain directly.
        try:
            answer = chain.invoke(question)
        except Exception:
            answer = chain.invoke({"question": question})

    # If the model appended a Sources: section, print it separately for clarity.
    if isinstance(answer, str) and "Sources:" in answer:
        parts = answer.split('\nSources:', 1)
        ans_text = parts[0].strip()
        sources_text = parts[1].strip()
        print(f"answer : {ans_text}")
        print("\nSources:" + sources_text)
        return ans_text

    print(f"answer :{answer}")
    return answer