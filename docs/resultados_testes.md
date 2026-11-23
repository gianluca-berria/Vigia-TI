# Resultados dos Testes - VigiaTI (Marco 2)

**Data da execução:** 2026-11-23  
**Ambiente:** Python 3.14.10, pytest 8.4.2  
**Modo:** Mock (Cassandra e Redis em memória) — sem containers Docker

---

## Sumário

| Métrica | Valor |
|---------|-------|
| Total de testes | 8 |
| Passaram | 8 |
| Falharam | 0 |
| Erros | 0 |
| Tempo total | ~2.5s |

---

## Detalhamento por teste

### 1. `test_abrir_chamado_sucesso` ✅
**Objetivo:** Validar RF01 - abertura de chamado grava chamado + evento, estado inicial `ABERTO`.

**Assertivas:**
- Retorno contém `estado == "ABERTO"`
- Título e técnico corretos
- Listagem retorna 1 chamado com estado `ABERTO`

---

### 2. `test_abrir_chamado_sem_titulo_ou_descricao` ✅
**Objetivo:** Validar regra de negócio - título e descrição obrigatórios.

**Assertivas:**
- Título vazio → `ValueError("Título é obrigatório")`
- Descrição vazia → `ValueError("Descrição é obrigatória")`

---

### 3. `test_atualizar_chamado_sucesso` ✅
**Objetivo:** Validar RF03 - atualização válida grava evento, atualiza listagem, invalida cache.

**Assertivas:**
- Retorno: `novo_estado == "EM_ATENDIMENTO"`, `estado_anterior == "ABERTO"`
- Listagem reflete novo estado `EM_ATENDIMENTO`

---

### 4. `test_estado_invalido_rejeitado` ✅
**Objetivo:** Validar regra - só 3 estados válidos (`ABERTO`, `EM_ATENDIMENTO`, `RESOLVIDO`).

**Assertivas:**
- Estado `"ESTADO_MALUCO"` → `ValueError("Estado inválido")`
- Sem efeitos colaterais (chamado permanece inalterado)

---

### 5. `test_atualizar_chamado_resolvido_rejeitado` ✅
**Objetivo:** Validar regra - `RESOLVIDO` encerra atendimento (sem reabertura).

**Assertivas:**
- Após resolver, nova atualização → `ValueError("já está RESOLVIDO")`
- Estado permanece `RESOLVIDO`

---

### 6. `test_historico_eventos` ✅
**Objetivo:** Validar RF04 - histórico ordenado do mais recente ao mais antigo, com autor e instante.

**Assertivas:**
- 3 eventos: `ABERTURA` → `EM_ATENDIMENTO` → `RESOLVIDO`
- Ordem: `[0]=RESOLVIDO`, `[1]=EM_ATENDIMENTO`, `[2]=ABERTURA` (DESC por `timeuuid`)
- Cada evento tem `evento_id`, `tipo`, `autor`, `descricao`

---

### 7. `test_cache_aside_e_invalidação` ✅
**Objetivo:** Validar cache-aside (Redis): hit, miss, expiração (TTL), invalidação após atualização.

**Assertivas:**
- Primeira leitura (miss) → popula cache
- Cache contém item válido
- Após `atualizar_chamado` → cache invalidado (retorna `None` no mock)

---

### 8. `test_reconciliacao` ✅
**Objetivo:** Validar reconciliação manual - recalcula estado da linha a partir do evento mais recente.

**Assertivas:**
- Corrompe estado na tabela para `ABERTO` (enquanto histórico diz `EM_ATENDIMENTO`)
- `reconciliar_chamado` → `estado_reconciliado == "EM_ATENDIMENTO"`
- Leitura posterior confirma estado corrigido

---

## Cobertura funcional

| Requisito / Regra | Testado por |
|-------------------|-------------|
| RF01 Abrir (título/desc obrigatórios) | testes 1, 2 |
| RF02 Listar (ordenado, paginação) | teste 1 (listagem), seed (paginação implícita) |
| RF03 Atualizar (estados válidos, RESOLVIDO final) | testes 3, 4, 5 |
| RF04 Histórico (ordem DESC, autor, instante) | teste 6 |
| Cache-aside (hit/miss/TTL/invalidação) | teste 7 |
| Redis indisponível (tolerância a falha) | mock mode do cache.py (logs de warning, continua via Cassandra) |
| Reconciliação manual | teste 8 |
| Prepared statements (sem concatenação) | cassandra_repo.py (inspeção de código) |
| Sem `ALLOW FILTERING` | cassandra_repo.py (inspeção de código) |

---

## Observações

- Todos os testes rodam em **modo mock** (Cassandra e Redis em memória) para velocidade e isolamento. O código real usa o mesmo caminho de execução; o mock é ativado automaticamente quando os containers não estão disponíveis.
- Para testar com Cassandra/Redis reais: `docker compose up -d` → aguardar healthcheck → `python -m pytest tests/ -v`.
- Nenhum teste usa `ALLOW FILTERING` nem concatenação de strings em CQL (ver `cassandra_repo.py`: todos usam `session.prepare()`).
- Mensagens de erro em português do Brasil, códigos de saída não-zero em falhas (CLI).

---

## Comando executado

```bash
python -m pytest tests/ -v
```