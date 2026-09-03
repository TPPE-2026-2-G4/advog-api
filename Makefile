help:
	@echo "Comandos disponíveis:"
	@echo " make setup                            # Configura o ambiente de desenvolvimento"
	@echo " make up                               # Sobe os containers do Docker"
	@echo " make test                             # Roda os testes com checagem de cobertura (>95%)"

setup:
	@echo "\n\n ⚙️ Configurando o ambiente de desenvolvimento... \n"
	uv sync
	uv run pre-commit install --hook-type commit-msg --hook-type pre-push
	install -m 755 scripts/hooks/prepare-commit-msg.sh "$$(git rev-parse --git-path hooks/prepare-commit-msg)"
	docker compose --profile dev up -d --build
	@echo "\n✅ Ambiente de desenvolvimento configurado com sucesso!"
	@echo "🔗 Portas disponíveis:"
	@echo " - pgAdmin: http://localhost:8080 \n"

up:
	@echo "\n\n⚙️ Subindo containers do Docker... \n"
	docker compose --profile dev up -d --build
	@echo "\n✅ Containers do Docker executados com sucesso! \n"
	@echo "🔗 Portas disponíveis:"
	@echo " - pgAdmin: http://localhost:8080 \n"

test:
	@echo "\n\n🧪 Rodando testes com cobertura... \n"
	uv run pytest
	@echo "\n\n✅ Testes concluídos com sucesso! \n"
