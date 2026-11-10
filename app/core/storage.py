import contextlib
import uuid
from typing import BinaryIO

from botocore.exceptions import ClientError

from app.config.storage import (
    S3_BUCKET_PUBLICO,
    s3_client,
    s3_public_client,
)


def garantir_bucket(bucket: str = S3_BUCKET_PUBLICO) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        codigo = exc.response.get("Error", {}).get("Code", "")
        if codigo in ("404", "NoSuchBucket"):
            s3_client.create_bucket(Bucket=bucket)
        else:
            raise


def salvar_arquivo(
    conteudo: BinaryIO,
    extensao: str,
    content_type: str,
    pasta: str = "",
    bucket: str = S3_BUCKET_PUBLICO,
) -> str:
    garantir_bucket(bucket)
    nome_arquivo = f"{uuid.uuid4().hex}.{extensao.lstrip('.')}"
    chave = f"{pasta.strip('/')}/{nome_arquivo}" if pasta else nome_arquivo

    s3_client.upload_fileobj(
        conteudo,
        bucket,
        chave,
        ExtraArgs={"ContentType": content_type},
    )
    return chave


def remover_arquivo(chave: str, bucket: str = S3_BUCKET_PUBLICO) -> None:
    if not chave:
        return
    with contextlib.suppress(ClientError):
        s3_client.delete_object(Bucket=bucket, Key=chave)


def obter_url_publica(
    chave: str | None,
    expiracao_segundos: int = 3600,
    bucket: str = S3_BUCKET_PUBLICO,
) -> str | None:
    if not chave:
        return None

    try:
        return s3_public_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": chave.lstrip("/")},
            ExpiresIn=expiracao_segundos,
        )
    except Exception:
        return None
