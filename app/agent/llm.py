from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from app.config import get_settings

settings = get_settings()


def get_llm(structured_output_schema=None):
    if settings.llm_provider == "ollama":
        llm = ChatOllama(model=settings.ollama_model, temperature=0)
    else:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.google_api_key,
            temperature=0,
        )

    if structured_output_schema:
        llm = llm.with_structured_output(structured_output_schema)

    return llm