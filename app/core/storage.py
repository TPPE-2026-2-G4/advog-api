import contextlib
import uuid
from typing import BinaryIO

from botocore.exceptions import ClientError

from app.config.storage import MINIO_BUCKET, MINIO_PUBLIC_URL, s3_client


def garantir_bucket() -> None:
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as exc:
        codigo = exc.response.get("Error", {}).get("Code", "")
        if codigo in ("404", "NoSuchBucket"):
            s3_client.create_bucket(Bucket=MINIO_BUCKET)
        else:
            raise


def salvar_arquivo(conteudo: BinaryIO, extensao: str, content_type: str, pasta: str = "") -> str:
    nome_arquivo = f"{uuid.uuid4().hex}.{extensao.lstrip('.')}"
    chave = f"{pasta.strip('/')}/{nome_arquivo}" if pasta else nome_arquivo

    s3_client.upload_fileobj(
        conteudo,
        MINIO_BUCKET,
        chave,
        ExtraArgs={"ContentType": content_type},
    )
    return chave


def remover_arquivo(chave: str) -> None:
    if not chave:
        return
    with contextlib.suppress(ClientError):
        s3_client.delete_object(Bucket=MINIO_BUCKET, Key=chave)


def obter_url_publica(chave: str | None, expiracao_segundos: int = 3600) -> str | None:
    if not chave:
        return None
    
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": MINIO_BUCKET, "Key": chave.lstrip("/")},
            ExpiresIn=expiracao_segundos,
        )

        if MINIO_PUBLIC_URL:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            parsed_public = urlparse(MINIO_PUBLIC_URL)

            url = parsed_url._replace(
                scheme=parsed_public.scheme, 
                netloc=parsed_public.netloc
            ).geturl()

        return url
    except Exception:
        return None
