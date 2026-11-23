#!/usr/bin/env python3
from src.vigiati import cassandra_repo

if __name__ == "__main__":
    print("Inicializando schema do VigiaTI...")
    cassandra_repo.init_schema()
    print("Concluído.")
