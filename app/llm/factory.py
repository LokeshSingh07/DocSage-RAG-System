from app.core.config import get_settings as settings
from app.llm.bedrock import bedrock_chat_model

LLM_PROVIDERS = {
    "bedrock": bedrock_chat_model,
    # "groq": groq_chat_model,
    # "openai": openai_chat_model,
}




def _get_provider(provider:str | None = None):
    
    provider = (provider or settings().llm_provider).lower()
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: {provider}, available providers: {list(LLM_PROVIDERS.keys())}")

    return LLM_PROVIDERS[provider]


# TODO : add history
def ask_llm(question: str, passages: list[str], history: list = [], provider: str | None = None) -> str:
    return _get_provider(provider)(question, passages, history)

