from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    aws_region:str = 'us-east-1'
    aws_access_key_id:str = ''
    aws_secret_access_key:str = ''
    aws_region:str = 'us-east-1'
    aws_s3_bucket_name:str = ''
    aws_bearer_token_bedrock:str=''
    max_upload_size_bytes:int = 104857600

    bedrock_embed_model:str = 'amazon.titan-embed-text-v2:0'
    bedrock_chat_model:str = 'amazon.nova-micro-v1:0'
    embed_dim:int = 1024
    embed_normalize:bool = True
    
    pinecone_api_key:str = ''
    pinecone_index_name:str = ''
    pinecone_cloud:str = 'aws'
    pinecone_region:str = 'us-east-1'
    pinecone_ready_timeout:int = 180

    database_url:str = ''

    rius_api_key:str = ''
    rius_service_name:str = ''
    rius_disabled:bool = False
    rius_capture_content:bool = False

    min_relevance_score:float = 0.3
    hitl_enabled:bool = True
    memory_turns:int = 6

    llm_provider:str = "bedrock"

    redis_url:str = 'redis://localhost:6379'



@lru_cache()
def get_settings() -> Settings:
    return Settings()