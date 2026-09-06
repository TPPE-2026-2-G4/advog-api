help:
	@echo "Comandos disponíveis:"
	@echo " make setup                            # Configura o ambiente de desenvolvimento"
	@echo " make up                               # Sobe os containers do Docker"
	@echo " make local                            # Roda a aplicação localmente"
	@echo " make test                             # Roda os testes com checagem de cobertura (>95%)"
	@echo " make lint                             # Roda o Ruff (lint + format) e o Mypy"

setup:
	@echo "\n\n ⚙️ Configurando o ambiente de desenvolvimento... \n"
	uv sync
	cp .env.local.example .env.local
	cp .env.example .env
	uv run pre-commit install --hook-type commit-msg --hook-type pre-push --hook-type pre-commit
	install -m 755 scripts/hooks/prepare-commit-msg.sh "$$(git rev-parse --git-path hooks/prepare-commit-msg)"
	docker compose --profile dev up -d --build
	@echo "\n✅ Ambiente de desenvolvimento configurado com sucesso!"
	@echo "🔗 Portas disponíveis:"
	@echo " - pgAdmin: http://localhost:8080"
	@echo " - FastAPI: http://localhost:8000"
	@echo " - Swagger: http://localhost:8000/docs"
	@echo " - MailPit Console: http://localhost:8025"
	@echo " - MailPit API: http://localhost:1025"
	@echo " - MinIO Console: http://localhost:9001"
	@echo " - MinIO API: http://localhost:9000 \n"

up:
	@echo "\n\n⚙️ Subindo containers do Docker... \n"
	docker compose --profile dev up -d --build
	@echo "\n✅ Containers do Docker executados com sucesso! \n"
	@echo "🔗 Portas disponíveis:"
	@echo " - pgAdmin: http://localhost:8080"
	@echo " - FastAPI: http://localhost:8000"
	@echo " - Swagger: http://localhost:8000/docs"
	@echo " - MailPit Console: http://localhost:8025"
	@echo " - MailPit API: http://localhost:1025"
	@echo " - MinIO Console: http://localhost:9001"
	@echo " - MinIO API: http://localhost:9000 \n"

local:
	@echo "\n\n⚙️ Rodando aplicação localmente... \n"
	docker compose down advog-api
	docker compose --profile dev up -d --build advog-db advog-mailpit
	cp .env.local.example .env.local
	uv run fastapi dev

test:
	@echo "\n\n🧪 Rodando testes com cobertura... \n"
	uv run pytest --cov-report=html --cov-report=term-missing
	@echo "\n\n✅ Testes concluídos com sucesso! \n"

lint:
	@echo "\n\n🔍 Rodando lint e checagem de tipos... \n"
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	@echo "\n\n✅ Lint concluído com sucesso! \n"
