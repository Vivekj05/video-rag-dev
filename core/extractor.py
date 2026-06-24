from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import os 

def get_llm():
    _key = os.getenv("MISTRAL_API_KEY")
    api_key = SecretStr(_key) if _key is not None else None
    return ChatMistralAI(model_name = "mistral-small-latest", api_key = api_key, temperature=0.2)

def build_chain(system_prompt : str):
    llm = get_llm()
    return (
        RunnablePassthrough() | RunnableLambda(lambda x : {"text" : x}) |ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human","{text}"),
    ]) | llm |StrOutputParser()
    )

def extract_action_items(transcript:str)->str:
    chain = build_chain(
        "You are an expert analyst. From the transcript (video, audio, or recording), extract all action items (tasks assigned or clearly implied).\n\n"
        "For EACH action item return the following EXACTLY in this format:\n"
        "[TASK]: <concise imperative task description>\n"
        "[OWNER]: <person or 'Not specified'>\n"
        "[DEADLINE]: <explicit date or relative deadline e.g. 'By EOD', or 'Not specified'>\n"
        "[TIMESTAMP]: <MM:SS if present in transcript, else 'Not specified'>\n"
        "[PRIORITY]: CRITICAL | HIGH | MEDIUM | LOW\n"
        "[CONFIDENCE]: <0-100 percent confidence that this is an actionable item>\n\n"
        "DEDUPE: If the same task is mentioned multiple times, merge into one entry.\n"
        "Return a numbered list of these entries. If none found, output exactly: No action items found."
    )

    return chain.invoke(transcript)


def extract_key_decisions(transcript: str) -> str:
    chain = build_chain(
        "You are an expert analyst. From the transcript (video, audio, or recording), extract all key decisions, agreements, consensus points, conclusions, or choices reached by the speakers (such as technological choices, next steps, finalized opinions, or resolved issues).\n\n"
        "For EACH decision return the following EXACTLY in this format:\n"
        "[DECISION]: <concise decision statement>\n"
        "[RATIONALE]: <1-2 sentence reason or context>\n"
        "[STAKEHOLDERS]: <names of approver(s), person proposing, or 'Not specified'>\n"
        "[TIMESTAMP]: <MM:SS if present in transcript, else 'Not specified'>\n"
        "[IMPACT]: STRATEGIC | TACTICAL\n"
        "[CONFIDENCE]: <0-100 percent confidence>\n\n"
        "Return a numbered list. If none found, output exactly: No key decisions found."
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the transcript (video, audio, or recording), extract key questions asked or significant topics raised that required discussion, focusing especially on unresolved questions or topics needing follow-up (you may also include key questions that were discussed and answered if they were central to the topic, but note their resolution status in the context).\n\n"
        "For EACH question return the following EXACTLY in this format:\n"
        "[QUESTION]: <the exact question or topic>\n"
        "[ASKED_BY]: <person or 'Not specified'>\n"
        "[TIMESTAMP]: <MM:SS if present in transcript, else 'Not specified'>\n"
        "[CONTEXT]: <1-2 sentence context, noting whether it was answered or remains unresolved>\n"
        "[PRIORITY]: HIGH | MEDIUM | LOW\n"
        "[CONFIDENCE]: <0-100 percent confidence>\n\n"
        "Return a numbered list. If none found, output exactly: No open questions found."
    )
    return chain.invoke(transcript)