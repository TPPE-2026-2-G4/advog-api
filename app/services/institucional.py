import defusedxml.ElementTree as ET
import filetype
from fastapi import UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.config.storage import obter_url_publica, remover_arquivo, salvar_arquivo
from app.models.institucional import Institucional
from app.repositories.institucional import InstitucionalRepository


class UploadInvalidoError(ValueError):
    pass


class InstitucionalService:
    def __init__(self, db: Session):
        self.repository = InstitucionalRepository(db)

    def obter_configuracoes(self) -> Institucional:
        return self.repository.buscar_configuracoes()

    def atualizar_configuracoes(self, dados: dict) -> Institucional:
        dados_filtrados = {k: v for k, v in dados.items() if v is not None}
        return self.repository.atualizar_configuracoes(dados_filtrados)

    def upload_midia(self, file: UploadFile, tipo: str) -> tuple[str, str | None]:
        if tipo not in ("logo", "banner", "sobre"):
            raise UploadInvalidoError("Tipo de mídia inválido. Use 'logo', 'banner' ou 'sobre'.")

        conteudo = file.file.read()
        file.file.seek(0)
        tamanho_bytes = len(conteudo)

        warning: str | None = None
        extensao: str = ""

        if tipo == "logo":
            if tamanho_bytes > 2 * 1024 * 1024:
                raise UploadInvalidoError("O logotipo deve ter no máximo 2MB.")

            if self._eh_svg(conteudo, file.filename):
                self._validar_svg_seguro(conteudo)
                extensao = "svg"
            else:
                kind = filetype.guess(conteudo)
                if not kind or kind.extension not in ("png", "svg"):
                    raise UploadInvalidoError("O logotipo deve ser um arquivo PNG ou SVG válido.")
                extensao = kind.extension

        elif tipo == "banner":
            if tamanho_bytes > 5 * 1024 * 1024:
                raise UploadInvalidoError("O banner hero deve ter no máximo 5MB.")

            kind = filetype.guess(conteudo)
            if not kind or kind.extension not in ("jpg", "jpeg", "png"):
                raise UploadInvalidoError("O banner hero deve ser uma imagem JPG ou PNG válida.")
            extensao = kind.extension

            try:
                with Image.open(file.file) as img:
                    largura, altura = img.size
                    if largura < 1920 or altura < 600:
                        warning = (
                            f"A resolução da imagem ({largura}x{altura}px) está abaixo da "
                            "recomendada (1920x600px). A imagem pode ficar desfocada."
                        )
            except Exception:
                pass
            finally:
                file.file.seek(0)

        elif tipo == "sobre":
            if tamanho_bytes > 5 * 1024 * 1024:
                raise UploadInvalidoError("A imagem da seção 'Sobre' deve ter no máximo 5MB.")

            kind = filetype.guess(conteudo)
            if not kind or kind.extension not in ("jpg", "jpeg", "png"):
                raise UploadInvalidoError(
                    "A imagem da seção 'Sobre' deve  ser uma imagem JPG ou PNG válida."
                )
            extensao = kind.extension

            try:
                with Image.open(file.file) as img:
                    largura, altura = img.size
                    if largura < 800 or altura < 600:
                        warning = f"A resolução da imagem ({largura}x{altura}px) está abaixo da recomendada (800x600px). A imagem pode ficar desfocada."
            except Exception:
                pass
            finally:
                file.file.seek(0)

        if tipo == "logo":
            pasta = "logotipos"
            campo_banco = "logotipo"
        elif tipo == "banner":
            pasta = "banners"
            campo_banco = "banner_hero"
        else:
            pasta = "sobre"
            campo_banco = "imagem_sobre"

        content_type = file.content_type or f"image/{extensao}"
        if extensao == "svg":
            content_type = "image/svg+xml"

        nova_chave = salvar_arquivo(
            conteudo=file.file,
            extensao=extensao,
            content_type=content_type,
            pasta=pasta,
        )

        config = self.repository.buscar_configuracoes()
        chave_antiga = getattr(config, campo_banco)

        self.repository.atualizar_configuracoes({campo_banco: nova_chave})

        if chave_antiga:
            remover_arquivo(chave_antiga)

        url_completa = obter_url_publica(nova_chave) or ""
        return url_completa, warning

    def _eh_svg(self, conteudo: bytes, filename: str | None) -> bool:
        if filename and filename.lower().endswith(".svg"):
            return True
        trecho = conteudo[:100].decode("utf-8", errors="ignore").lower()
        return "<svg" in trecho or "<?xml" in trecho

    def _validar_svg_seguro(self, conteudo: bytes) -> None:
        try:
            root = ET.fromstring(conteudo)
        except Exception as e:
            raise UploadInvalidoError("Arquivo SVG corrompido ou inválido.") from e

        for elem in root.iter():
            tag_name = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
            if tag_name == "script":
                raise UploadInvalidoError("O arquivo SVG contém scripts e não pode ser enviado.")

            for attr, val in elem.attrib.items():
                attr_name = attr.lower()
                val_str = str(val).lower()
                if attr_name.startswith("on") or "javascript:" in val_str:
                    raise UploadInvalidoError(
                        f"O arquivo SVG contém atributos executáveis inseguros ({attr})."
                    )
