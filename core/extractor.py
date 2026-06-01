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
        "You are an expert analyst. From the transcript (video, audio, or recording), extract only FIRM key decisions (not proposals or tentative agreements). A key decision is an explicit choice that affects scope, timeline, budget, or responsibilities.\n\n"
        "For EACH decision return the following EXACTLY in this format:\n"
        "[DECISION]: <concise decision statement>\n"
        "[RATIONALE]: <1-2 sentence reason or context>\n"
        "[STAKEHOLDERS]: <names of approver(s) or 'Not specified'>\n"
        "[TIMESTAMP]: <MM:SS if present in transcript, else 'Not specified'>\n"
        "[IMPACT]: STRATEGIC | TACTICAL\n"
        "[CONFIDENCE]: <0-100 percent confidence>\n\n"
        "Return a numbered list. If none found, output exactly: No key decisions found."
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the transcript (video, audio, or recording), extract UNRESOLVED questions or topics that NEED FOLLOW-UP (exclude rhetorical or immediately-answered questions).\n\n"
        "For EACH unresolved question return the following EXACTLY in this format:\n"
        "[QUESTION]: <the exact question or topic>\n"
        "[ASKED_BY]: <person or 'Not specified'>\n"
        "[TIMESTAMP]: <MM:SS if present in transcript, else 'Not specified'>\n"
        "[CONTEXT]: <1-2 sentence context>\n"
        "[PRIORITY]: HIGH | MEDIUM | LOW\n"
        "[CONFIDENCE]: <0-100 percent confidence>\n\n"
        "Return a numbered list. If none found, output exactly: No open questions found."
    )
    return chain.invoke(transcript)