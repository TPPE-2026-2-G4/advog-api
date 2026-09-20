import os

import boto3
from botocore.client import Config


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
