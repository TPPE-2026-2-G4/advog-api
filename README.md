# Backend | API de Gestão Jurídica

Bem-vindo ao repositório de backend da equipe 4 (TPPE-2026-2)!

Este repositório contém a **API de Gestão Jurídica**, responsável pelo acesso aos dados de processos da plataforma. A API é construída com [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) e [Pydantic](https://docs.pydantic.dev/), com suporte a SQLite no desenvolvimento e PostgreSQL no ambiente Docker.

## Como acessar a API

Após iniciar o projeto localmente, a API estará disponível em `http://localhost:8000/`.

O FastAPI também disponibiliza a documentação interativa em:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Como rodar o projeto localmente

### Pré-requisitos

- [Python](https://www.python.org/) 3.11 ou superior.
- [uv](https://docs.astral.sh/uv/) para gerenciamento do ambiente e das dependências.
- [Docker](https://www.docker.com/) e Docker Compose para executar os serviços de banco de dados e armazenamento de arquivos (MinIO).

### Configuração e execução

1. **Clone este repositório:**

    ```bash
    git clone https://github.com/TPPE-2026-2-G4/advog-api.git
    cd advog-api
    ```

2. **Configure as variáveis de ambiente:**

    ```bash
    cp .env.example .env
    ```

    Preencha no `.env` os valores de `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`. As variáveis `PGADMIN_DEFAULT_EMAIL` e `PGADMIN_DEFAULT_PASSWORD` controlam o acesso ao pgAdmin, enquanto `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD` controlam as credenciais de acesso ao MinIO.

3. **Configure o ambiente completo de desenvolvimento:**

    ```bash
    make setup
    ```

    Esse comando sincroniza as dependências com o `uv.lock`, instala os hooks do pre-commit e sobe os containers. A API fica em `http://localhost:8000/`, o pgAdmin em `http://localhost:8080/` e o console do MinIO em `http://localhost:9001/` (com API S3 em `http://localhost:9000/`).

### Execução manual

Para instalar somente as dependências e iniciar a API localmente:

```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Sem uma variável `DATABASE_URL`, a aplicação usa o banco SQLite `advog_db.sqlite` no diretório do projeto. No Docker Compose, a API usa automaticamente o PostgreSQL do serviço `advog-db`.

### Execução com Docker Compose

Para subir a API, o PostgreSQL e o MinIO:

```bash
make up
```

O comando equivale a `docker compose --profile dev up -d --build`. Para interromper os serviços:

```bash
docker compose down
```

Os volumes `db-data` e `minio-data` preservam os dados do PostgreSQL e os arquivos do MinIO entre reinicializações. Para removê-los também, use `docker compose down -v`.

## Endpoints disponíveis

### Verificação da API

```http
GET /
```

Retorna uma mensagem indicando que a API está disponível.

### Processos

```http
POST /processos/
GET /processos/
```

Para criar um processo, envie um JSON com os campos `id`, `titulo`, `cliente`, `status`, `tribunal`, `area`, `responsavel` e `prazo`. O campo `diasRestantes` é opcional e assume o valor `15` quando não informado.

```bash
curl -X POST http://localhost:8000/processos/ \
	-H "Content-Type: application/json" \
	-d '{
		"id": "0001",
		"titulo": "Caso de exemplo",
		"cliente": "Maria",
		"status": "ativo",
		"tribunal": "tjsp",
		"area": "civil",
		"responsavel": "ana",
		"prazo": "20/10/2026",
		"diasRestantes": 10
	}'
```

Os processos podem ser filtrados pelos parâmetros `id`, `tribunal`, `titulo`, `cliente`, `area`, `responsavel`, `status` e `prazo`:

```bash
curl "http://localhost:8000/processos/?status=ativo&area=civil"
```

Os filtros são aplicados por correspondência parcial e não diferenciam maiúsculas de minúsculas. Para `status`, o valor `todos` não aplica esse filtro.

## Testes

Execute a suíte de testes com a checagem de cobertura configurada para, no mínimo, 95%:

```bash
make test
```

O comando executa `uv run pytest`. Para executar diretamente:

```bash
uv run pytest
```

## Comandos disponíveis

- `make setup` — Configura o ambiente, instala os hooks e sobe os containers de desenvolvimento.
- `make up` — Sobe os containers da API, PostgreSQL, pgAdmin e MinIO.
- `make test` — Executa os testes com relatório de cobertura.
- `uv sync` — Instala ou sincroniza as dependências do projeto.
- `uv run uvicorn main:app --reload` — Inicia a API em modo de desenvolvimento.
- `uv run cz commit` — Abre o assistente para mensagens de commit no padrão Conventional Commits.

## Estrutura do Repositório

- `main.py`: Ponto de entrada da aplicação FastAPI, criação das tabelas e registro das rotas.
- `app/`: Código-fonte da API.
  - `config/database.py`: Configuração do SQLAlchemy, conexão e sessões do banco.
  - `controllers/`: Rotas e controladores HTTP, incluindo os endpoints de processos.
  - `models/`: Modelos de dados do SQLAlchemy.
  - `repositories/`: Operações de persistência e consultas ao banco.
  - `schemas/`: Schemas de entrada, resposta e filtros com Pydantic.
  - `services/`: Regras de serviço da aplicação.
- `tests/`: Testes automatizados da API.
- `scripts/hooks/`: Hooks de commit e pre-push.
- `pyproject.toml`: Metadados, dependências, configurações do Pytest, cobertura e Commitizen.
- `uv.lock`: Versões fixadas das dependências.
- `Dockerfile`: Imagem da API em produção.
- `compose.yml`: Configuração dos serviços da API, PostgreSQL, pgAdmin e MinIO.
- `Makefile`: Atalhos para configuração, execução dos containers e testes.
- `.env.example`: Modelo das variáveis de ambiente necessárias.
- `.pre-commit-config.yaml`: Configuração dos hooks de commit e pre-push.
- `.python-version`: Versão padrão do Python utilizada pelo projeto.

## Fluxo de Contribuição

As contribuições devem ser feitas em uma branch própria e enviadas por Pull Request para a branch `main`.

Antes de abrir o Pull Request:

1. Execute `make test`.
2. Confirme que os hooks de pre-commit estão instalados.
3. Utilize mensagens de commit no padrão Conventional Commits com `uv run cz commit`.
