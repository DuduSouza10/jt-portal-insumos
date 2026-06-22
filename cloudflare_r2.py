import os
from io import BytesIO
from typing import BinaryIO


def r2_is_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
    )


def r2_client():
    import boto3
    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        region_name="auto",
    )


def r2_public_url(key: str) -> str | None:
    base = os.getenv("R2_PUBLIC_URL", "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}/{key.lstrip('/')}"


def upload_bytes_to_r2(key: str, data: bytes, content_type: str, metadata: dict[str, str] | None = None) -> str | None:
    """Upload a file to Cloudflare R2 when configured.

    Returns a public/custom-domain URL only if R2_PUBLIC_URL is set.
    If R2 is not configured, the function silently returns None so local usage keeps working.
    """
    if not r2_is_configured():
        return None
    client = r2_client()
    client.put_object(
        Bucket=os.getenv("R2_BUCKET", "").strip(),
        Key=key.lstrip("/"),
        Body=data,
        ContentType=content_type,
        Metadata=metadata or {},
    )
    return r2_public_url(key)


def upload_fileobj_to_r2(key: str, fileobj: BinaryIO, content_type: str, metadata: dict[str, str] | None = None) -> str | None:
    data = fileobj.read()
    return upload_bytes_to_r2(key, data, content_type, metadata)
