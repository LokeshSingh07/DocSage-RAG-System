import boto3
from functools import lru_cache
from app.core.config import get_settings as settings



@lru_cache()
def client(service:str):
    s = settings()
    return boto3.client(
        service,
        region_name=s.aws_region,
        aws_access_key_id=s.aws_access_key_id,
        aws_secret_access_key=s.aws_secret_access_key
    )



def upload_to_S3():
    pass


def download_from_s3(key: str) -> bytes:
    response = client("s3").get_object(Bucket=settings().s3_bucket, Key=key)
    return response["Body"].read() 