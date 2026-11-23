import uuid
import time
import logging
from datetime import datetime, timezone
from src.vigiati.config import CASSANDRA_CONTACT_POINTS, CASSANDRA_PORT, CASSANDRA_KEYSPACE

logger = logging.getLogger("vigiati.cassandra")

_cluster = None
_session = None
_mock_mode = False
_mock_storage = {
    "chamados": {}, # key: (equipe_id, chamado_id) -> dict
    "eventos": {}   # key: chamado_id -> list of dicts
}

def get_cluster():
    global _cluster, _mock_mode
    if _cluster is not None:
        return _cluster
    try:
        from cassandra.cluster import Cluster
        cluster = Cluster(CASSANDRA_CONTACT_POINTS, port=CASSANDRA_PORT)
        # Quick test connection
        _cluster = cluster
        _mock_mode = False
        return cluster
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao Cassandra real ({e}). Ativando modo Mock em memória para Cassandra.")
        _mock_mode = True
        return None

def get_session(keyspace=CASSANDRA_KEYSPACE):
    global _session, _mock_mode
    if _mock_mode:
        return None
    if _session is not None:
        return _session
    try:
        cluster = get_cluster()
        if cluster is None:
            return None
        session = cluster.connect()
        # Create keyspace if not exists
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
        """)
        session.set_keyspace(keyspace)
        _session = session
        return session
    except Exception as e:
        logger.warning(f"Falha ao obter sessão do Cassandra ({e}). Ativando modo Mock em memória.")
        _mock_mode = True
        return None

def is_mock_mode():
    return _mock_mode

def init_schema():
    session = get_session()
    if is_mock_mode():
        print("[MOCK] Schema do Cassandra inicializado em memória.")
        return True
    
    session.execute("""
        CREATE TABLE IF NOT EXISTS chamados_por_equipe (
          equipe_id uuid,
          chamado_id uuid,
          criado_em timestamp,
          titulo text,
          descricao text,
          solicitante text,
          tecnico text,
          estado text,
          PRIMARY KEY ((equipe_id), chamado_id)
        );
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS eventos_por_chamado (
          chamado_id uuid,
          evento_id timeuuid,
          tipo text,
          descricao text,
          autor text,
          PRIMARY KEY ((chamado_id), evento_id)
        ) WITH CLUSTERING ORDER BY (evento_id DESC);
    """)
    print("[Cassandra] Schema inicializado com sucesso.")
    return True

def limpar_dados():
    if is_mock_mode():
        _mock_storage["chamados"].clear()
        _mock_storage["eventos"].clear()
        print("[MOCK] Dados limpos.")
        return
    session = get_session()
    if session:
        session.execute("TRUNCATE TABLE chamados_por_equipe;")
        session.execute("TRUNCATE TABLE eventos_por_chamado;")
        print("[Cassandra] Dados limpos (TRUNCATE).")

def inserir_evento(chamado_id, evento_id, tipo, descricao, autor):
    if is_mock_mode():
        ch_id = str(chamado_id)
        if ch_id not in _mock_storage["eventos"]:
            _mock_storage["eventos"][ch_id] = []
        _mock_storage["eventos"][ch_id].append({
            "chamado_id": uuid.UUID(str(chamado_id)),
            "evento_id": evento_id,
            "tipo": tipo,
            "descricao": descricao,
            "autor": autor
        })
        # sort descending by evento_id (timeuuid or timestamp representation)
        _mock_storage["eventos"][ch_id].sort(key=lambda x: str(x["evento_id"]), reverse=True)
        return

    session = get_session()
    query = """
        INSERT INTO eventos_por_chamado (chamado_id, evento_id, tipo, descricao, autor)
        VALUES (?, ?, ?, ?, ?)
    """
    prepared = session.prepare(query)
    session.execute(prepared, (uuid.UUID(str(chamado_id)), evento_id, tipo, descricao, autor))

def salvar_chamado(equipe_id, chamado_id, criado_em, titulo, descricao, solicitante, tecnico, estado):
    if is_mock_mode():
        eq_id = str(equipe_id)
        ch_id = str(chamado_id)
        key = (eq_id, ch_id)
        _mock_storage["chamados"][key] = {
            "equipe_id": uuid.UUID(str(equipe_id)),
            "chamado_id": uuid.UUID(str(chamado_id)),
            "criado_em": criado_em if isinstance(criado_em, datetime) else datetime.now(timezone.utc),
            "titulo": titulo,
            "descricao": descricao,
            "solicitante": solicitante,
            "tecnico": tecnico,
            "estado": estado
        }
        return

    session = get_session()
    query = """
        INSERT INTO chamados_por_equipe (equipe_id, chamado_id, criado_em, titulo, descricao, solicitante, tecnico, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    prepared = session.prepare(query)
    session.execute(prepared, (
        uuid.UUID(str(equipe_id)),
        uuid.UUID(str(chamado_id)),
        criado_em,
        titulo,
        descricao,
        solicitante,
        tecnico,
        estado
    ))

def listar_chamados_por_equipe(equipe_id):
    if is_mock_mode():
        eq_id = str(equipe_id)
        results = []
        for (eq, ch), data in _mock_storage["chamados"].items():
            if eq == eq_id:
                results.append(data)
        # Sort by criado_em descending or ascending as needed (application sorting)
        results.sort(key=lambda x: x["criado_em"], reverse=True)
        return results

    session = get_session()
    query = """
        SELECT equipe_id, chamado_id, criado_em, titulo, descricao, solicitante, tecnico, estado
        FROM chamados_por_equipe
        WHERE equipe_id = ?
    """
    prepared = session.prepare(query)
    rows = session.execute(prepared, (uuid.UUID(str(equipe_id)),))
    return list(rows)

def buscar_chamado(equipe_id, chamado_id):
    if is_mock_mode():
        key = (str(equipe_id), str(chamado_id))
        return _mock_storage["chamados"].get(key)

    session = get_session()
    query = """
        SELECT equipe_id, chamado_id, criado_em, titulo, descricao, solicitante, tecnico, estado
        FROM chamados_por_equipe
        WHERE equipe_id = ? AND chamado_id = ?
    """
    prepared = session.prepare(query)
    row = session.execute(prepared, (uuid.UUID(str(equipe_id)), uuid.UUID(str(chamado_id)))).one()
    return row

def listar_eventos_por_chamado(chamado_id):
    if is_mock_mode():
        ch_id = str(chamado_id)
        events = _mock_storage["eventos"].get(ch_id, [])
        return events

    session = get_session()
    query = """
        SELECT chamado_id, evento_id, tipo, descricao, autor
        FROM eventos_por_chamado
        WHERE chamado_id = ?
    """
    prepared = session.prepare(query)
    rows = session.execute(prepared, (uuid.UUID(str(chamado_id)),))
    return list(rows)
