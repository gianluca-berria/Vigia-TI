import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.example")

CASSANDRA_CONTACT_POINTS = os.getenv("CASSANDRA_CONTACT_POINTS", "127.0.0.1").split(",")
CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", 9042))
CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "vigiati")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

EQUIPE_ID_DEMO = os.getenv("EQUIPE_ID_DEMO", "00000000-0000-0000-0000-000000000001")

TECNICOS = ["Tec01", "Tec02", "Tec03"]

ESTADOS_VALIDOS = {"ABERTO", "EM_ATENDIMENTO", "RESOLVIDO"}
