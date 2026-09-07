# Backend | API de Gestão Jurídica

Bem-vindo ao repositório de backend da equipe 4 (TPPE-2026-2)!

Este repositório contém a **API de Gestão Jurídica**, responsável pelo acesso aos dados de processos e funcionários da plataforma. A API é construída com [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) e [Pydantic](https://docs.pydantic.dev/), com suporte a SQLite no desenvolvimento e PostgreSQL no ambiente Docker.

## Como acessar a API

Após iniciar o projeto localmente, a API estará disponível em `http://localhost:8000/`.

O FastAPI também disponibiliza a documentação interativa em:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Como rodar o projeto localmente

### Pré-requisitos

- [Python](https://www.python.org/) 3.11 ou superior.
- [uv](https://docs.astral.sh/uv/) para gerenciamento do ambiente e das dependências.
- [Docker](https://www.docker.com/) e Docker Compose para executar os serviços de banco de dados, e-mail (Mailpit) e armazenamento de arquivos (MinIO).

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

    Preencha no `.env` os valores de `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`. As variáveis `PGADMIN_DEFAULT_EMAIL` e `PGADMIN_DEFAULT_PASSWORD` controlam o acesso ao pgAdmin, `SMTP_*` controla a conexão com o Mailpit (servidor de e-mail de testes), `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD` controlam as credenciais de acesso ao MinIO, e `FRONTEND_URL` define quais origens têm permissão de CORS para consumir a API (aceita múltiplas URLs separadas por vírgula).

3. **Configure o ambiente completo de desenvolvimento:**

    ```bash
    make setup
    ```

    Esse comando sincroniza as dependências com o `uv.lock`, instala os hooks do pre-commit, cria o `.env.local` (ver seção abaixo) e sobe os containers. A API fica em `http://localhost:8000/`, o pgAdmin em `http://localhost:8080/`, o console do Mailpit em `http://localhost:8025/` e o console do MinIO em `http://localhost:9001/` (com API S3 em `http://localhost:9000/`).

### Execução manual

Para instalar somente as dependências e iniciar a API localmente:

```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Sem uma variável `DATABASE_URL`, a aplicação usa o banco SQLite `advog_db.sqlite` no diretório do projeto. No Docker Compose, a API usa automaticamente o PostgreSQL do serviço `advog-db`.

### Rodando a API localmente com as dependências em Docker (`.env.local`)

O `.env` é pensado para quando **toda a stack** roda em Docker Compose — por isso `DATABASE_URL` e `SMTP_HOST` apontam para os hostnames internos da rede do Compose (`advog-db`, `advog-mailpit`). Esses nomes não resolvem fora da rede do Docker, então rodar a API diretamente no seu terminal (fora de um container) com esse `.env` falha ao tentar conectar no banco/e-mail.

Para esse cenário, existe o `.env.local`: um arquivo **git-ignorado**, carregado por `main.py` (com `override=True`) depois do `.env`, sobrescrevendo apenas `DATABASE_URL` e `SMTP_HOST` para `localhost`. Ele nunca é copiado para dentro da imagem Docker (ver `.dockerignore`), então não interfere quando a API roda via `docker compose`.

Fluxo recomendado:

```bash
make local
```

Esse comando sobe só `advog-db` e `advog-mailpit` via Docker (com as portas publicadas em `localhost`), copia `.env.local.example` para `.env.local` e roda a API localmente com `uv run fastapi dev`. Use esse modo quando quiser hot-reload rápido sem rebuildar a imagem da API a cada mudança.

### Execução com Docker Compose

Para subir a API, o PostgreSQL, o pgAdmin, o Mailpit e o MinIO:

```bash
make up
```

O comando equivale a `docker compose --profile dev up -d --build`. Para interromper os serviços:

```bash
docker compose down
```

Serviços e portas disponíveis:

| Serviço          | URL / Porta                              | Descrição                                  |
| ---------------- | ----------------------------------------- | ------------------------------------------- |
| `advog-api`       | `http://localhost:8000`                   | API FastAPI                                 |
| `advog-db`        | `localhost:5432`                          | PostgreSQL                                  |
| `advog-pgadmin`   | `http://localhost:8080`                   | Administração do PostgreSQL (perfil `dev`)  |
| `advog-mailpit`   | `http://localhost:8025` (UI) / `1025` (SMTP) | Captura os e-mails enviados pela API (perfil `dev`) |
| `advog-minio`     | `http://localhost:9001` (console) / `9000` (S3) | Armazenamento de arquivos                   |

Os volumes `db-data` e `minio-data` preservam os dados do PostgreSQL e os arquivos do MinIO entre reinicializações. Para removê-los também, use `docker compose down -v`.

## Endpoints disponíveis

Com a API rodando, consulte o Swagger UI (`http://localhost:8000/docs`) para a documentação completa e sempre atualizada de cada rota (payloads, respostas e erros). Resumo dos endpoints existentes:

| Método   | Rota                                              | Recurso     |
| -------- | -------------------------------------------------- | ----------- |
| `GET`    | `/`                                                 | Health check |
| `POST`   | `/processos/`                                       | Processos   |
| `GET`    | `/processos/`                                       | Processos   |
| `POST`   | `/funcionarios`                                     | Funcionários |
| `GET`    | `/funcionarios`                                     | Funcionários |
| `PATCH`  | `/funcionarios/{funcionario_id}/primeiro-acesso`    | Funcionários |
| `PATCH`  | `/funcionarios/{funcionario_id}/mudar-acesso`       | Funcionários |
| `DELETE` | `/funcionarios/{funcionario_id}`                    | Funcionários |
| `POST`   | `/auth/login`                                       | Autenticação |

## CORS

A API libera CORS apenas para as origens definidas em `FRONTEND_URL` no `.env` (múltiplas origens podem ser separadas por vírgula, ex: `http://localhost:3000,https://app.escritorio.com`). Por padrão, sem essa variável, libera `http://localhost:3000`.

## Testes

Execute a suíte de testes com a checagem de cobertura configurada para, no mínimo, 95%:

```bash
make test
```

O comando executa `uv run pytest --cov-report=html --cov-report=term-missing` e gera um relatório navegável em `htmlcov/index.html`, além do resumo no terminal. Para executar sem o relatório HTML:

```bash
uv run pytest
```

Os testes (`tests/`) rodam de forma isolada: `tests/conftest.py` substitui a conexão real do banco por SQLite em memória (nunca toca no PostgreSQL de desenvolvimento) e faz mock do envio de e-mail, então nenhum teste depende de serviços externos disponíveis.

### Integração Contínua

Todo Pull Request para `main` dispara o workflow [`test.yml`](.github/workflows/test.yml) no GitHub Actions, que instala as dependências e roda `uv run pytest`, falhando caso a cobertura fique abaixo de 95%.

## Comandos disponíveis

- `make setup` — Configura o ambiente, instala os hooks, cria `.env`/`.env.local` e sobe os containers de desenvolvimento.
- `make up` — Sobe os containers da API, PostgreSQL, pgAdmin, Mailpit e MinIO.
- `make local` — Sobe só o PostgreSQL e o Mailpit em Docker e roda a API localmente com hot-reload (`uv run fastapi dev`).
- `make test` — Executa os testes com relatório de cobertura (terminal + HTML).
- `uv sync` — Instala ou sincroniza as dependências do projeto.
- `uv run uvicorn main:app --reload` — Inicia a API em modo de desenvolvimento.
- `uv run cz commit` — Abre o assistente para mensagens de commit no padrão Conventional Commits.

## Estrutura do Repositório

- `main.py`: Ponto de entrada da aplicação FastAPI — carrega `.env`/`.env.local`, cria as tabelas, configura CORS e registra as rotas.
- `app/`: Código-fonte da API.
  - `config/database.py`: Configuração do SQLAlchemy, conexão e sessões do banco.
  - `controllers/`: Rotas e controladores HTTP (`processo_controller.py`, `funcionario.py`, `auth.py`).
  - `models/`: Modelos de dados do SQLAlchemy (`processo_model.py`, `funcionario.py`).
  - `repositories/`: Operações de persistência e consultas ao banco.
  - `schemas/`: Schemas de entrada, resposta e filtros com Pydantic (`auth.py`, `funcionario.py`, `processo_schema.py`).
  - `services/`: Regras de negócio da aplicação (`auth.py`, `funcionario.py`, `processo_service.py`).
  - `utils/`: Utilitários — hash de senha (`seguranca.py`) e envio de e-mail (`email.py`).
- `tests/`: Testes automatizados — `unit/` (services, repositories, utils) e `integration/` (controllers via `TestClient`).
- `scripts/hooks/`: Hooks de commit e pre-push.
- `pyproject.toml`: Metadados, dependências, configurações do Pytest, cobertura e Commitizen.
- `uv.lock`: Versões fixadas das dependências.
- `Dockerfile`: Imagem da API em produção.
- `compose.yml`: Configuração dos serviços da API, PostgreSQL, pgAdmin, Mailpit e MinIO.
- `Makefile`: Atalhos para configuração, execução dos containers e testes.
- `.env.example`: Modelo das variáveis de ambiente necessárias (para rodar via Docker Compose).
- `.env.local.example`: Modelo de overrides para rodar a API localmente fora do Docker (ver seção acima).
- `.dockerignore`: Garante que `.env`, `.env.local` e outros arquivos locais não vão para a imagem Docker.
- `.github/workflows/test.yml`: Pipeline de CI que roda a suíte de testes em cada Pull Request.
- `.pre-commit-config.yaml`: Configuração dos hooks de commit e pre-push.
- `.python-version`: Versão padrão do Python utilizada pelo projeto.

## Fluxo de Contribuição

As contribuições devem ser feitas em uma branch própria e enviadas por Pull Request para a branch `main`.

Antes de abrir o Pull Request:

1. Execute `make test` e confirme que a cobertura está acima de 95%.
2. Confirme que os hooks de pre-commit estão instalados.
3. Utilize mensagens de commit no padrão Conventional Commits com `git commit`.
4. O workflow de CI (`test.yml`) roda automaticamente no PR — garanta que ele passa antes de pedir revisão.
