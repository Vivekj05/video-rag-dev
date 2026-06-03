from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

import os
from dotenv import load_dotenv
load_dotenv()

from concurrent.futures import ThreadPoolExecutor

def get_llm():
    _key = os.getenv("MISTRAL_API_KEY")
    api_key = SecretStr(_key) if _key is not None else None
    return ChatMistralAI(model_name = "mistral-small-latest", api_key = api_key, temperature=0.3)

def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 3000,
        chunk_overlap = 200
    )

    return splitter.split_text(transcript)


def summarize(transcript: str) -> str:
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this portion of a meeting transcript concisely."),
        ("human", "{text}"),
    ])    

    map_chain= prompt | llm | StrOutputParser()

    chunks = split_transcript(transcript)

    with ThreadPoolExecutor(max_workers=6) as executor:
        chunk_summaries = list(executor.map(lambda chunk: map_chain.invoke({"text": chunk}), chunks))

    combined = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages(
        [
        (
            "system",
            "You are an expert meeting summarizer. Combine these partial summaries "
            "into one final professional meeting summary in bullet points.",
        ),
        ("human", "{text}"),
    ]
    )

    combined_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | combined_prompt | llm | StrOutputParser()
    )

    raw = combined_chain.invoke(combined)

    # Post-process the model output to ensure readable paragraphs and simple bullets
    import re

    def tidy(text: str) -> str:
        if not text:
            return ""
        # normalize newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # remove excessive markdown bold markers which often inline text
        text = text.replace('**', '')

        # convert markdown headings into paragraph breaks
        text = re.sub(r"#{1,6}\s*", "\n\n", text)

        # ensure list items start on their own line and use a simple '-' marker
        text = re.sub(r"\n?\s*[-*\u2022]\s+", "\n- ", text)

        # collapse 3+ newlines into two
        text = re.sub(r"\n{3,}", "\n\n", text)

        # trim leading/trailing whitespace
        text = text.strip()

        return text

    return tidy(raw)

def generate_title(transcipt : str) -> str:
    llm = get_llm()

    

    title_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | 
        ChatPromptTemplate.from_messages([
             (
                "system",
                "Based on the meeting transcript, generate a short professional meeting title "
                "(max 8 words). Only return the title, nothing else.",
            ),
            ("human", "{text}"),
        ])
        | llm
        |StrOutputParser()
    )

    return title_chain.invoke(transcipt[:2000])