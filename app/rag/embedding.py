import json
from app.core.config import get_settings as settings
from app.core.aws import client
from app.core.observability import trace

# ===================================
# embedding
# ===================================
@trace("bedrock_embedding")
def embed(text):
    body = json.dumps({
        'inputText': text,
        'dimensions': settings().embed_dim,
        'normalize': settings().embed_normalize
    })

    response = client("bedrock-runtime").invoke_model(
        modelId=settings().bedrock_embed_model,
        body=body
    )

    # print("EMBEDDING =>\n", json.loads(response['body'].read()))
    return json.loads(response['body'].read())['embedding']
