import uuid
from datetime import datetime, timezone
from src.vigiati.config import ESTADOS_VALIDOS, TECNICOS, EQUIPE_ID_DEMO
from src.vigiati import cassandra_repo, cache

def gerar_timeuuid():
    # uuid1 represents timeuuid in python uuid module
    return uuid.uuid1()

def abrir_chamado(titulo, descricao, solicitante, tecnico, equipe_id=EQUIPE_ID_DEMO):
    if not titulo or not titulo.strip():
        raise ValueError("Erro: Título é obrigatório para abrir um chamado.")
    if not descricao or not descricao.strip():
        raise ValueError("Erro: Descrição é obrigatória para abrir um chamado.")
    if not solicitante or not solicitante.strip():
        raise ValueError("Erro: Solicitante é obrigatório.")
    
    if tecnico not in TECNICOS:
        raise ValueError(f"Erro: Técnico inválido '{tecnico}'. Técnicos válidos: {TECNICOS}")

    chamado_id = uuid.uuid4()
    evento_id = gerar_timeuuid()
    criado_em = datetime.now(timezone.utc)
    estado_inicial = "ABERTO"

    # Ordem de escrita:
    # 1. Gravar evento em eventos_por_chamado
    cassandra_repo.inserir_evento(
        chamado_id=chamado_id,
        evento_id=evento_id,
        tipo="ABERTURA",
        descricao=f"Chamado aberto: {titulo}",
        autor=solicitante
    )

    # 2. Gravar linha em chamados_por_equipe
    cassandra_repo.salvar_chamado(
        equipe_id=equipe_id,
        chamado_id=chamado_id,
        criado_em=criado_em,
        titulo=titulo.strip(),
        descricao=descricao.strip(),
        solicitante=solicitante.strip(),
        tecnico=tecnico,
        estado=estado_inicial
    )

    # 3. Invalidar / inicializar cache
    cache.invalidate_chamado_cache(equipe_id, chamado_id)

    return {
        "chamado_id": str(chamado_id),
        "equipe_id": str(equipe_id),
        "titulo": titulo.strip(),
        "estado": estado_inicial,
        "tecnico": tecnico,
        "criado_em": criado_em.isoformat()
    }

def listar_chamados(equipe_id=EQUIPE_ID_DEMO):
    rows = cassandra_repo.listar_chamados_por_equipe(equipe_id)
    # Convert rows to dicts for clean presentation
    chamados = []
    for r in rows:
        r_dict = r._asdict() if hasattr(r, '_asdict') else dict(zip(r._fields, r)) if hasattr(r, '_fields') else r
        ch_id = str(r_dict['chamado_id'])
        cached = cache.get_chamado_cache(equipe_id, ch_id)
        if cached:
            chamados.append({
                "chamado_id": ch_id,
                "titulo": cached.get("titulo", r_dict.get('titulo')),
                "descricao": cached.get("descricao", r_dict.get('descricao')),
                "solicitante": cached.get("solicitante", r_dict.get('solicitante')),
                "tecnico": cached.get("tecnico", r_dict.get('tecnico')),
                "estado": cached.get("estado", r_dict.get('estado')),
                "criado_em": str(cached.get("criado_em", r_dict.get('criado_em')))
            })
        else:
            item = {
                "chamado_id": ch_id,
                "titulo": r_dict.get('titulo'),
                "descricao": r_dict.get('descricao'),
                "solicitante": r_dict.get('solicitante'),
                "tecnico": r_dict.get('tecnico'),
                "estado": r_dict.get('estado'),
                "criado_em": str(r_dict.get('criado_em'))
            }
            cache.set_chamado_cache(equipe_id, ch_id, item)
            chamados.append(item)
    return chamados

def obter_chamado(chamado_id, equipe_id=EQUIPE_ID_DEMO):
    cached = cache.get_chamado_cache(equipe_id, chamado_id)
    if cached:
        return cached
    
    row = cassandra_repo.buscar_chamado(equipe_id, chamado_id)
    if not row:
        return None
    
    r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(row._fields, row)) if hasattr(row, '_fields') else row
    item = {
        "chamado_id": str(r_dict.get('chamado_id')),
        "titulo": r_dict.get('titulo'),
        "descricao": r_dict.get('descricao'),
        "solicitante": r_dict.get('solicitante'),
        "tecnico": r_dict.get('tecnico'),
        "estado": r_dict.get('estado'),
        "criado_em": str(r_dict.get('criado_em'))
    }
    cache.set_chamado_cache(equipe_id, chamado_id, item)
    return item

def atualizar_chamado(chamado_id, novo_estado, autor, descricao_evento, equipe_id=EQUIPE_ID_DEMO):
    if novo_estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Erro: Estado inválido '{novo_estado}'. Estados permitidos: {ESTADOS_VALIDOS}")

    # Fetch current chamado
    chamado = obter_chamado(chamado_id, equipe_id)
    if not chamado:
        raise ValueError(f"Erro: Chamado '{chamado_id}' não encontrado para a equipe '{equipe_id}'.")

    estado_atual = chamado["estado"]
    if estado_atual == "RESOLVIDO":
        raise ValueError(f"Erro: O chamado '{chamado_id}' já está RESOLVIDO e não pode ser alterado.")

    if not autor or not autor.strip():
        raise ValueError("Erro: Autor da atualização é obrigatório.")

    if not descricao_evento or not descricao_evento.strip():
        raise ValueError("Erro: Descrição do evento de atualização é obrigatória.")

    evento_id = gerar_timeuuid()

    # Ordem de escrita:
    # 1. Gravar evento em eventos_por_chamado
    cassandra_repo.inserir_evento(
        chamado_id=chamado_id,
        evento_id=evento_id,
        tipo=novo_estado,
        descricao=descricao_evento.strip(),
        autor=autor.strip()
    )

    # 2. Atualizar linha em chamados_por_equipe
    # Keep original criado_em, titulo, descricao, solicitante, tecnico
    criado_em = chamado["criado_em"]
    if isinstance(criado_em, str):
        try:
            criado_em = datetime.fromisoformat(criado_em)
        except Exception:
            criado_em = datetime.now(timezone.utc)

    cassandra_repo.salvar_chamado(
        equipe_id=equipe_id,
        chamado_id=chamado_id,
        criado_em=criado_em,
        titulo=chamado["titulo"],
        descricao=chamado["descricao"],
        solicitante=chamado["solicitante"],
        tecnico=chamado["tecnico"],
        estado=novo_estado
    )

    # 3. Invalidar cache no Redis
    cache.invalidate_chamado_cache(equipe_id, chamado_id)

    return {
        "chamado_id": str(chamado_id),
        "estado_anterior": estado_atual,
        "novo_estado": novo_estado,
        "autor": autor.strip()
    }

def _row_to_dict(row):
    """Converte Row do Cassandra ou dict do mock para dict."""
    if row is None:
        return None
    if hasattr(row, '_asdict'):
        return row._asdict()
    if hasattr(row, '_fields'):
        return dict(zip(row._fields, row))
    if isinstance(row, dict):
        return row
    # Fallback: try to access attributes
    return {attr: getattr(row, attr) for attr in dir(row) if not attr.startswith('_')}


def consultar_historico(chamado_id):
    eventos = cassandra_repo.listar_eventos_por_chamado(chamado_id)
    resultado = []
    for ev in eventos:
        ev_dict = _row_to_dict(ev)
        resultado.append({
            "evento_id": str(ev_dict.get('evento_id')),
            "tipo": ev_dict.get('tipo'),
            "descricao": ev_dict.get('descricao'),
            "autor": ev_dict.get('autor')
        })
    return resultado

def reconciliar_chamado(chamado_id, equipe_id=EQUIPE_ID_DEMO):
    eventos = cassandra_repo.listar_eventos_por_chamado(chamado_id)
    if not eventos:
        raise ValueError(f"Erro: Nenhum evento encontrado para o chamado '{chamado_id}'.")

    # eventos_por_chamado has CLUSTERING ORDER BY (evento_id DESC)
    # The first event in the list is the most recent event.
    mais_recente = _row_to_dict(eventos[0])
    tipo_recente = mais_recente.get('tipo')

    # Determine state from latest event type (if type is ABERTURA, state is ABERTO, else type is state)
    estado_calculado = "ABERTO" if tipo_recente == "ABERTURA" else tipo_recente
    if estado_calculado not in ESTADOS_VALIDOS:
        estado_calculado = "ABERTO"

    # Fetch base info (title, solicitante, etc.) from existing row
    chamado_atual = cassandra_repo.buscar_chamado(equipe_id, chamado_id)
    if not chamado_atual:
        raise ValueError(f"Erro: Linha principal do chamado '{chamado_id}' não encontrada em chamados_por_equipe.")

    ch_dict = _row_to_dict(chamado_atual)
    criado_em = ch_dict.get('criado_em')
    titulo = ch_dict.get('titulo')
    descricao = ch_dict.get('descricao')
    solicitante = ch_dict.get('solicitante')
    tecnico = ch_dict.get('tecnico')

    # Update row with reconciled state
    cassandra_repo.salvar_chamado(
        equipe_id=equipe_id,
        chamado_id=chamado_id,
        criado_em=criado_em,
        titulo=titulo,
        descricao=descricao,
        solicitante=solicitante,
        tecnico=tecnico,
        estado=estado_calculado
    )

    cache.invalidate_chamado_cache(equipe_id, chamado_id)
    return {
        "chamado_id": str(chamado_id),
        "estado_reconciliado": estado_calculado
    }
