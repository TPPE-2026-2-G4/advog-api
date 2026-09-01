help:
	@echo "Comandos disponíveis:"
	@echo " make setup                            # Configura o ambiente de desenvolvimento"
	@echo " make test                             # Roda os testes com checagem de cobertura (>95%)"

setup:
	@echo "\n\n ⚙️ Configurando o ambiente de desenvolvimento... \n"
	uv sync
	uv run pre-commit install --hook-type commit-msg --hook-type pre-push
	install -m 755 scripts/hooks/prepare-commit-msg.sh "$$(git rev-parse --git-path hooks/prepare-commit-msg)"
	@echo "\n\n✅ Ambiente de desenvolvimento configurado com sucesso! \n"

test:
	@echo "\n\n🧪 Rodando testes com cobertura... \n"
	uv run pytest
	@echo "\n\n✅ Testes concluídos com sucesso! \n"
