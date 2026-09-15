import contextlib
import os
import uuid
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def _obter_variavel_obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente '{nome}' não definida. Configure-a no .env .")
    return valor


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "institucional")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

MINIO_ROOT_USER = _obter_variavel_obrigatoria("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = _obter_variavel_obrigatoria("MINIO_ROOT_PASSWORD")


s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4"),
    use_ssl=MINIO_USE_SSL,
    region_name="us-east-1",
)


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


def obter_url_publica(chave: str | None) -> str | None:
    if not chave:
        return None
    return f"{MINIO_PUBLIC_URL.rstrip('/')}/{MINIO_BUCKET}/{chave.lstrip('/')}"
