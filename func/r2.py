import asyncio
import aioboto3
from os import getenv
from dotenv import load_dotenv
from uuid import uuid4
load_dotenv()

BUCKET_NAME = getenv("R2_BUCKET_NAME")
ENDPOINT_URL = getenv("R2_ENDPOINT_URL")

async def upload_fileobj(file, expires: int = 3600):
    async with aioboto3.Session().client("s3", endpoint_url=ENDPOINT_URL) as s3:
        object_name = str(uuid4())
        await s3.upload_fileobj(file, BUCKET_NAME, object_name)
        url = await s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": object_name
            },
            ExpiresIn=expires
        )
        return url
