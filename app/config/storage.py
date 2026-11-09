import os

import boto3
from botocore.client import Config


def _obter_variavel_obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente '{nome}' não definida. Configure-a no .env .")
    return valor


S3_ENDPOINT = _obter_variavel_obrigatoria("S3_ENDPOINT")
S3_BUCKET_PUBLICO = _obter_variavel_obrigatoria("S3_BUCKET_PUBLICO")
S3_BUCKET_PRIVADO = _obter_variavel_obrigatoria("S3_BUCKET_PRIVADO")
S3_USE_SSL = os.getenv("S3_USE_SSL", "false").lower() == "true"
S3_PUBLIC_URL = _obter_variavel_obrigatoria("S3_PUBLIC_URL")

S3_REGION = os.getenv("S3_REGION", "").strip() or "us-east-1"

S3_ACCESS_KEY_ID = _obter_variavel_obrigatoria("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = _obter_variavel_obrigatoria("S3_SECRET_ACCESS_KEY")

_S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    connect_timeout=5,
    read_timeout=30,
    retries={"max_attempts": 2},
)

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    config=_S3_CONFIG,
    use_ssl=S3_USE_SSL,
    region_name=S3_REGION,
)

s3_public_client = boto3.client(
    "s3",
    endpoint_url=S3_PUBLIC_URL,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    config=_S3_CONFIG,
    use_ssl=S3_USE_SSL,
    region_name=S3_REGION,
)
