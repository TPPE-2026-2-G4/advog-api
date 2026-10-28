import os

import boto3
from botocore.client import Config


def _obter_variavel_obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente '{nome}' não definida. Configure-a no .env .")
    return valor


MINIO_ENDPOINT = _obter_variavel_obrigatoria("MINIO_ENDPOINT")
MINIO_BUCKET = _obter_variavel_obrigatoria("MINIO_BUCKET")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
MINIO_PUBLIC_URL = _obter_variavel_obrigatoria("MINIO_PUBLIC_URL")

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

s3_public_client = boto3.client(
    "s3",
    endpoint_url=MINIO_PUBLIC_URL,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4"),
    use_ssl=MINIO_USE_SSL,
    region_name="us-east-1",
)
