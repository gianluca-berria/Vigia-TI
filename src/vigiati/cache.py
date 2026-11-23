import logging
from src.vigiati.config import REDIS_HOST, REDIS_PORT, REDIS_DB

logger = logging.getLogger("vigiati.cache")

_redis_client = None
_mock_redis_storage = {} # key -> (dict, expire_time)

def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        client.ping()
        _redis_client = client
        return client
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao Redis real ({e}). Ativando modo Mock para Redis.")
        return None

def get_chamado_cache(equipe_id, chamado_id):
    key = f"chamado:{equipe_id}:{chamado_id}"
    client = get_redis_client()
    if client is None:
        # Mock redis storage check
        import time
        item = _mock_redis_storage.get(key)
        if item:
            data, exp = item
            if exp is None or exp > time.time():
                return data
            else:
                del _mock_redis_storage[key]
        return None

    try:
        data = client.hgetall(key)
        if data and len(data) > 0:
            return data
        return None
    except Exception as e:
        logger.warning(f"Erro ao ler cache do Redis ({e}). Continuando sem cache.")
        return None

def set_chamado_cache(equipe_id, chamado_id, dados, ttl=60):
    key = f"chamado:{equipe_id}:{chamado_id}"
    # Convert all values to string for Redis Hash
    str_dados = {k: str(v) for k, v in dados.items() if v is not None}
    
    client = get_redis_client()
    if client is None:
        import time
        exp = time.time() + ttl if ttl else None
        _mock_redis_storage[key] = (str_dados, exp)
        return

    try:
        client.hset(key, mapping=str_dados)
        if ttl:
            client.expire(key, ttl)
    except Exception as e:
        logger.warning(f"Erro ao gravar cache no Redis ({e}). Continuando.")

def invalidate_chamado_cache(equipe_id, chamado_id):
    key = f"chamado:{equipe_id}:{chamado_id}"
    client = get_redis_client()
    if client is None:
        if key in _mock_redis_storage:
            del _mock_redis_storage[key]
        return

    try:
        client.delete(key)
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache no Redis ({e}). Continuando.")
