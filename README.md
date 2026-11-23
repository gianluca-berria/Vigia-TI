# VigiaTI - Monitor de Chamados de TI (Marco 2)

Protótipo funcional de um sistema de monitoramento de chamados de suporte de TI, desenvolvido como trabalho individual da disciplina **Bancos de Dados NoSQL: Persistência e Distribuição de Big Data** (CEUB, Campus Taguatinga).

Evolução do Marco 1: adiciona persistência em **Cassandra (Wide-Column)**, cache em **Redis (Chave-Valor)**, regras de negócio completas, CLI, testes de integração e documentação arquitetural justificada.

---

## Pré-requisitos

- **Python 3.11+**
- **Docker** e **Docker Compose** (para Cassandra e Redis)
- `make` (opcional, para atalhos)

---

## Subindo a infraestrutura

```bash
docker compose up -d
```

Aguarde o Cassandra ficar saudável (pode levar 30-60s na primeira subida). Verifique com:

```bash
docker compose ps
# Ambos os containers devem estar "healthy" ou "Up"
```

> **Nota:** O Cassandra em nó único demora para iniciar. O comando `init` abaixo já tenta reconectar com timeout.

---

## Instalação do projeto

```bash
# Criar ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Copiar variáveis de ambiente
cp .env.example .env
# Edite .env se necessário (portas, IPs, UUID da equipe demo)
```

---

## Inicialização do schema e dados de demonstração

```bash
# 1. Criar keyspace e tabelas no Cassandra
python -m src.vigiati.cli init

# 2. Popular ~1.000 chamados com ~10 eventos cada (~10.000 eventos totais)
python -m src.vigiati.cli seed --quantidade 1000
```

> **Volume estimado:** 1.000 chamados × ~10 eventos ≈ 10.000 eventos × ~1 kB ≈ **10 MB brutos** (sem índices, metadados e backups).

---

## Exemplos de uso da CLI

### Abrir um chamado (RF01)

```bash
python -m src.vigiati.cli abrir \
  --titulo "Falha na rede Wi-Fi do 3º andar" \
  --descricao "Usuários sem conexão no 3º andar desde 09h" \
  --solicitante "Ana Silva" \
  --tecnico Tec01
```

**Saída esperada:**

```
[Sucesso] Chamado aberto:
╒══════════════════════════════════════╤══════════════════════════════════════╤════════════════╤═══════════╤═══════════╤══════════════════════════════════╕
│ chamado_id                           │ equipe_id                            │ titulo                │ estado   │ tecnico   │ criado_em                        │
╞══════════════════════════════════════╪══════════════════════════════════════╪═══════════════════════╪═══════════╪═══════════╪══════════════════════════════════╡
│ a1b2c3d4-e5f6-7890-abcd-ef1234567890 │ 00000000-0000-0000-0000-000000000001 │ Falha na rede Wi-Fi... │ ABERTO   │ Tec01     │ 2026-11-23T22:38:50.551815+00:00 │
╘══════════════════════════════════════╧══════════════════════════════════════╧═══════════════════════╧═══════════╧═══════════╧══════════════════════════════════╛
```

### Listar chamados da equipe (RF02)

```bash
python -m src.vigiati.cli listar --limite 10
```

**Saída esperada:**

```
Chamados da Equipe (10 exibidos):
╒══════════════╤════════════════════════════════════════════════╤════════════════╤═══════════╤════════════════╤════════════════════════════╕
│ ID (curto)   │ Título                                         │ Estado         │ Técnico   │ Solicitante    │ Criado em                  │
╞══════════════╪═════════════════════════════════════════════════╪════════════════╪═══════════╪════════════════╪════════════════════════════╡
│ a1b2c3d4...  │ Falha na rede Wi-Fi do 3º andar #1             │ ABERTO         │ Tec01     │ Ana Silva      │ 2026-11-23 10:00:00.000000 │
├──────────────┼────────────────────────────────────────────────┼────────────────┼───────────┼────────────────┼────────────────────────────┤
│ ...          │ ...                                            │ ...            │ ...       │ ...            │ ...                        │
╘══════════════╧═════════════════════════════════════════════════╧════════════════╧═══════════╧════════════════╧════════════════════════════╛
```

### Atualizar estado do chamado (RF03)

```bash
python -m src.vigiati.cli atualizar \
  --chamado-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --estado EM_ATENDIMENTO \
  --autor "Tec01" \
  --descricao "Iniciando diagnóstico no switch do 3º andar"
```

**Saída esperada:**

```
[Sucesso] Chamado atualizado:
╒══════════════════════════════════════╤═══════════════════╤════════════════╤═════════╕
│ chamado_id                           │ estado_anterior   │ novo_estado    │ autor   │
╞══════════════════════════════════════╪═══════════════════╪════════════════╪═════════╡
│ a1b2c3d4-e5f6-7890-abcd-ef1234567890 │ ABERTO            │ EM_ATENDIMENTO │ Tec01   │
╘══════════════════════════════════════╧═══════════════════╧════════════════╧═════════╛
```

> **Regras:** Só são aceitos `ABERTO`, `EM_ATENDIMENTO`, `RESOLVIDO`. Chamados `RESOLVIDO` não podem ser alterados.

### Consultar histórico de eventos (RF04)

```bash
python -m src.vigiati.cli historico \
  --chamado-id a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Saída esperada:**

```
Histórico de Eventos para o chamado a1b2c3d4-e5f6-7890-abcd-ef1234567890 (Mais recente ao mais antigo):
╒══════════════════════════════════════╤═════════════════╤════════════╤═══════════════════════════════════════╕
│ ID Evento (TimeUUID)                 │ Tipo / Estado   │ Autor      │ Descrição                             │
╞══════════════════════════════════════╪═════════════════╪════════════╪═══════════════════════════════════════╡
│ b2c3d4e5-f6a7-8901-bcde-f23456789012 │ EM_ATENDIMENTO  │ Tec01      │ Iniciando diagnóstico no switch...    │
├──────────────────────────────────────┼─────────────────┼────────────┼───────────────────────────────────────┤
│ a1b2c3d4-e5f6-7890-abcd-ef1234567890 │ ABERTURA        │ Ana Silva  │ Chamado aberto: Falha na rede...      │
╘══════════════════════════════════════╧═════════════════╧════════════╧═══════════════════════════════════════╛
```

### Reconciliar estado divergente

```bash
python -m src.vigiati.cli reconciliar \
  --chamado-id a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Limpar todos os dados

```bash
python -m src.vigiati.cli limpar
```

---

## Executando os testes

```bash
# Todos os testes (integração com mocks de Cassandra/Redis)
python -m pytest tests/ -v

# Com cobertura
python -m pytest tests/ -v --cov=src/vigiati
```

Os testes validam:
- Abertura com validações (RF01)
- Listagem com paginação (RF02)
- Atualização de estado com invalidação de cache (RF03)
- Histórico ordenado do mais recente ao mais antigo (RF04)
- Cache-aside: hit, miss, expiração (TTL), invalidação
- Redis indisponível: operações continuam via Cassandra
- Reconciliação de estado divergente

> **Resultado dos testes:** Ver `docs/resultados_testes.md`

---

## Estrutura do projeto

```
vigiati/
├── docker-compose.yml          # Cassandra + Redis (nó único, healthcheck)
├── README.md                   # Este arquivo
├── requirements.txt            # Dependências Python
├── .env.example                # Variáveis de ambiente modelo
├── scripts/
│   └── init_schema.py          # Script standalone para init do schema
├── src/vigiati/
│   ├── __init__.py
│   ├── config.py               # Configuração, equipe/tecnicos fictícios, estados válidos
│   ├── cassandra_repo.py       # Acesso ao Cassandra (CQL prepared statements)
│   ├── cache.py                # Redis: cache-aside, TTL 60s, tolerância a falha
│   ├── service.py              # Regras de negócio RF01-RF04 (camada modular)
│   ├── cli.py                  # Interface de linha de comando (argparse)
│   └── seed.py                 # Geração de dados de demonstração (~1000 chamados)
├── tests/
│   └── test_vigiati.py         # Testes de integração (pytest, fixtures com limpeza)
└── docs/
    ├── documentacao_final.md   # Documentação acadêmica completa
    └── resultados_testes.md    # Registro da execução dos testes
```

---

## Solução de problemas

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| `init` falha com timeout | Cassandra ainda subindo | Aguarde `docker compose logs -f cassandra` mostrar "Startup complete" ou "Listening for CQL clients" |
| `Connection refused` porta 9042 | Cassandra não saudável | `docker compose restart cassandra` e aguarde healthcheck |
| `Connection refused` porta 6379 | Redis não subiu | `docker compose restart redis` |
| Erro `ALLOW FILTERING` | Consulta mal formada | Verifique se usa prepared statements e partition key correta |
| Cache não invalida | Redis fora do ar | Log de aviso aparece; sistema continua funcionando via Cassandra |
| `ModuleNotFoundError` | Dependências não instaladas | `pip install -r requirements.txt` dentro do venv |

---

## Variáveis de ambiente (.env)

```ini
CASSANDRA_CONTACT_POINTS=127.0.0.1
CASSANDRA_PORT=9042
CASSANDRA_KEYSPACE=vigiati
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
EQUIPE_ID_DEMO=00000000-0000-0000-0000-000000000001
```

---

## Licença

Uso acadêmico - Disciplina Bancos de Dados NoSQL (CEUB).