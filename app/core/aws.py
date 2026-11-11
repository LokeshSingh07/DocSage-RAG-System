import boto3
from botocore.config import Config
from functools import lru_cache
from app.core.config import get_settings as settings
import uuid
from app.core.observability import trace

_BOTO_CONFIG = Config(
    max_pool_connections=20,
    connect_timeout=5,
    read_timeout=30,
    retries={"max_attempts": 2, "mode": "standard"},
)


@lru_cache()
def client(service:str):
    s = settings()
    return boto3.client(
        service,
        region_name=s.aws_region,
        aws_access_key_id=s.aws_access_key_id,
        aws_secret_access_key=s.aws_secret_access_key,
        config=_BOTO_CONFIG,
    )




def build_key(filename:str):
    ext = filename.split(".")[-1]
    return f"{uuid.uuid4().hex[:10]}.{ext}"


@trace('upload_to_S3')
def upload_to_S3(data:bytes, filename:str):
    key = build_key(filename)

    client("s3").put_object(
        Bucket=settings().aws_s3_bucket_name, 
        Key=key, 
        Body=data
    )

    return {"key": key}


@trace('download_from_s3')
def download_from_s3(key: str) -> bytes:
    response = client("s3").get_object(Bucket=settings().aws_s3_bucket_name, Key=key)
    return response["Body"].read() 