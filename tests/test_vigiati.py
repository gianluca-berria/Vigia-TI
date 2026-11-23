import pytest
from datetime import datetime, timezone
from src.vigiati import cassandra_repo, cache, service
from src.vigiati.config import EQUIPE_ID_DEMO

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Initialize mock or real schema and clean before each test
    cassandra_repo.init_schema()
    cassandra_repo.limpar_dados()
    cache._mock_redis_storage.clear()
    yield
    cassandra_repo.limpar_dados()
    cache._mock_redis_storage.clear()

def test_abrir_chamado_sucesso():
    res = service.abrir_chamado(
        titulo="Falha na rede",
        descricao="Cabo desconectado",
        solicitante="Ana Silva",
        tecnico="Tec01",
        equipe_id=EQUIPE_ID_DEMO
    )
    assert res["estado"] == "ABERTO"
    assert res["titulo"] == "Falha na rede"
    assert res["tecnico"] == "Tec01"
    
    # Check listing
    chamados = service.listar_chamados(EQUIPE_ID_DEMO)
    assert len(chamados) == 1
    assert chamados[0]["estado"] == "ABERTO"

def test_abrir_chamado_sem_titulo_ou_descricao():
    with pytest.raises(ValueError, match="Título é obrigatório"):
        service.abrir_chamado("", "Desc", "Ana", "Tec01", EQUIPE_ID_DEMO)

    with pytest.raises(ValueError, match="Descrição é obrigatória"):
        service.abrir_chamado("Titulo", "", "Ana", "Tec01", EQUIPE_ID_DEMO)

def test_atualizar_chamado_sucesso():
    res_abertura = service.abrir_chamado(
        titulo="Impressora travada",
        descricao="Sem papel",
        solicitante="Carlos",
        tecnico="Tec02",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res_abertura["chamado_id"]

    res_att = service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="EM_ATENDIMENTO",
        autor="Tec02",
        descricao_evento="Iniciado atendimento no local",
        equipe_id=EQUIPE_ID_DEMO
    )
    assert res_att["novo_estado"] == "EM_ATENDIMENTO"
    assert res_att["estado_anterior"] == "ABERTO"

    # Verify listing shows updated state
    chamados = service.listar_chamados(EQUIPE_ID_DEMO)
    assert chamados[0]["estado"] == "EM_ATENDIMENTO"

def test_estado_invalido_rejeitado():
    res = service.abrir_chamado(
        titulo="Teste",
        descricao="Desc",
        solicitante="Ana",
        tecnico="Tec01",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res["chamado_id"]

    with pytest.raises(ValueError, match="Estado inválido"):
        service.atualizar_chamado(
            chamado_id=chamado_id,
            novo_estado="ESTADO_MALUCO",
            autor="Tec01",
            descricao_evento="Tentativa inválida",
            equipe_id=EQUIPE_ID_DEMO
        )

def test_atualizar_chamado_resolvido_rejeitado():
    res = service.abrir_chamado(
        titulo="Erro ERP",
        descricao="Tela azul",
        solicitante="Mariana",
        tecnico="Tec03",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res["chamado_id"]

    # Resolve
    service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="RESOLVIDO",
        autor="Tec03",
        descricao_evento="Erro resolvido com reboot",
        equipe_id=EQUIPE_ID_DEMO
    )

    # Try to update again
    with pytest.raises(ValueError, match="já está RESOLVIDO"):
        service.atualizar_chamado(
            chamado_id=chamado_id,
            novo_estado="EM_ATENDIMENTO",
            autor="Tec03",
            descricao_evento="Tentativa em chamado resolvido",
            equipe_id=EQUIPE_ID_DEMO
        )

def test_historico_eventos():
    res = service.abrir_chamado(
        titulo="VPN lenta",
        descricao="Conexão oscilando",
        solicitante="Roberto",
        tecnico="Tec01",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res["chamado_id"]

    service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="EM_ATENDIMENTO",
        autor="Tec01",
        descricao_evento="Testando rotas de rede",
        equipe_id=EQUIPE_ID_DEMO
    )

    service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="RESOLVIDO",
        autor="Tec01",
        descricao_evento="Rota corrigida",
        equipe_id=EQUIPE_ID_DEMO
    )

    historico = service.consultar_historico(chamado_id)
    # Should have 3 events (ABERTURA, EM_ATENDIMENTO, RESOLVIDO) ordered DESC by timeuuid
    assert len(historico) == 3
    assert historico[0]["tipo"] == "RESOLVIDO"
    assert historico[1]["tipo"] == "EM_ATENDIMENTO"
    assert historico[2]["tipo"] == "ABERTURA"

def test_cache_aside_e_invalidação():
    res = service.abrir_chamado(
        titulo="Cache Test",
        descricao="Testando cache",
        solicitante="Ana",
        tecnico="Tec02",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res["chamado_id"]

    # First read (miss -> populates cache)
    chamado_lido_1 = service.obter_chamado(chamado_id, EQUIPE_ID_DEMO)
    assert chamado_lido_1["titulo"] == "Cache Test"

    # Verify cache has item
    cached_raw = cache.get_chamado_cache(EQUIPE_ID_DEMO, chamado_id)
    assert cached_raw is not None

    # Update (should invalidate cache)
    service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="EM_ATENDIMENTO",
        autor="Tec02",
        descricao_evento="Atualizando para invalidar cache",
        equipe_id=EQUIPE_ID_DEMO
    )

    # Cache should be invalidated (None in mock storage)
    cached_after_update = cache.get_chamado_cache(EQUIPE_ID_DEMO, chamado_id)
    assert cached_after_update is None

def test_reconciliacao():
    res = service.abrir_chamado(
        titulo="Reconciliação Test",
        descricao="Teste de recálculo",
        solicitante="Lucas",
        tecnico="Tec01",
        equipe_id=EQUIPE_ID_DEMO
    )
    chamado_id = res["chamado_id"]

    service.atualizar_chamado(
        chamado_id=chamado_id,
        novo_estado="EM_ATENDIMENTO",
        autor="Tec01",
        descricao_evento="Em atendimento",
        equipe_id=EQUIPE_ID_DEMO
    )

    # Force manual corruption of state in table (simulate divergence)
    cassandra_repo.salvar_chamado(
        equipe_id=EQUIPE_ID_DEMO,
        chamado_id=service.uuid.UUID(chamado_id),
        criado_em=datetime.now(timezone.utc),
        titulo="Reconciliação Test",
        descricao="Teste de recálculo",
        solicitante="Lucas",
        tecnico="Tec01",
        estado="ABERTO" # Divergent state
    )

    # Reconcile
    rec = service.reconciliar_chamado(chamado_id, EQUIPE_ID_DEMO)
    assert rec["estado_reconciliado"] == "EM_ATENDIMENTO"

    # Verify fixed in table
    chamado_corrigido = service.obter_chamado(chamado_id, EQUIPE_ID_DEMO)
    assert chamado_corrigido["estado"] == "EM_ATENDIMENTO"
