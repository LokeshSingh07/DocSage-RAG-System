from app.core.config import get_settings as settings
from app.core.aws import client
from app.llm.prompt import SYSTEM_PROMPT



MAX_MEMORY_TURN = settings().memory_turns


# ===================================
# chat
# ===================================
def bedrock_chat_model(question: str, chunks: list[str], history: list = []):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    context = "\n\n".join(
        f"<passage id={id}>{cont}</passage>" for id, cont in enumerate(chunks, 1)
    )
    user_msg = f"<context>{context}</context> \n\nQuestion: {question}"

    # memory -> last N messages of history, keep only user/assistant
    recent = history[-MAX_MEMORY_TURN:]
    messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]} for m in recent if m["role"] in ("user", "assistant")
    ]

    # first message is always user
    while(messages and messages[0]["role"] != "user"):
        messages.pop(0)


    messages.append({"role": "user", "content": [{"text": user_msg}]})

    response = client("bedrock-runtime").converse(
        modelId=settings().bedrock_chat_model,
        system=[{'text': SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 1024, "temperature": 0.4},
    )
    
    # print(f"RESPONSE =>\n\n {response}")
    return response['output']['message']['content'][0]['text']

