import sys
import argparse
from tabulate import tabulate
from src.vigiati import cassandra_repo, service, seed, cache
from src.vigiati.config import EQUIPE_ID_DEMO, TECNICOS, ESTADOS_VALIDOS

def cmd_init(args):
    try:
        cassandra_repo.init_schema()
        print("Schema inicializado com sucesso.")
    except Exception as e:
        print(f"Erro ao inicializar schema: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_seed(args):
    try:
        seed.popular_dados(qtd_chamados=args.quantidade, equipe_id=args.equipe)
        print(f"{args.quantidade} chamados populados com sucesso.")
    except Exception as e:
        print(f"Erro ao popular dados: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_abrir(args):
    try:
        resultado = service.abrir_chamado(
            titulo=args.titulo,
            descricao=args.descricao,
            solicitante=args.solicitante,
            tecnico=args.tecnico,
            equipe_id=args.equipe
        )
        print("\n[Sucesso] Chamado aberto:")
        print(tabulate([resultado], headers="keys", tablefmt="fancy_grid"))
    except ValueError as ve:
        print(f"{ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado ao abrir chamado: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_listar(args):
    try:
        chamados = service.listar_chamados(equipe_id=args.equipe)
        if not chamados:
            print("Nenhum chamado encontrado para esta equipe.")
            return

        # Aplicar limite se fornecido
        if args.limite and args.limite > 0:
            chamados = chamados[:args.limite]

        tabela = []
        for c in chamados:
            tabela.append([
                c["chamado_id"][:8] + "...",
                c["titulo"],
                c["estado"],
                c["tecnico"],
                c["solicitante"],
                c["criado_em"]
            ])
        print(f"\nChamados da Equipe ({len(chamados)} exibidos):")
        print(tabulate(tabela, headers=["ID (curto)", "Título", "Estado", "Técnico", "Solicitante", "Criado em"], tablefmt="fancy_grid"))
    except Exception as e:
        print(f"Erro ao listar chamados: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_atualizar(args):
    try:
        resultado = service.atualizar_chamado(
            chamado_id=args.chamado_id,
            novo_estado=args.estado,
            autor=args.autor,
            descricao_evento=args.descricao,
            equipe_id=args.equipe
        )
        print("\n[Sucesso] Chamado atualizado:")
        print(tabulate([resultado], headers="keys", tablefmt="fancy_grid"))
    except ValueError as ve:
        print(f"{ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado ao atualizar chamado: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_historico(args):
    try:
        eventos = service.consultar_historico(chamado_id=args.chamado_id)
        if not eventos:
            print(f"Nenhum evento encontrado para o chamado {args.chamado_id}.")
            return

        tabela = []
        for ev in eventos:
            tabela.append([
                ev["evento_id"],
                ev["tipo"],
                ev["autor"],
                ev["descricao"]
            ])
        print(f"\nHistórico de Eventos para o chamado {args.chamado_id} (Mais recente ao mais antigo):")
        print(tabulate(tabela, headers=["ID Evento (TimeUUID)", "Tipo / Estado", "Autor", "Descrição"], tablefmt="fancy_grid"))
    except Exception as e:
        print(f"Erro ao consultar histórico: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_reconciliar(args):
    try:
        resultado = service.reconciliar_chamado(
            chamado_id=args.chamado_id,
            equipe_id=args.equipe
        )
        print("\n[Sucesso] Chamado reconciliado:")
        print(tabulate([resultado], headers="keys", tablefmt="fancy_grid"))
    except ValueError as ve:
        print(f"{ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado ao reconciliar chamado: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_limpar(args):
    try:
        cassandra_repo.limpar_dados()
        print("Dados limpos com sucesso.")
    except Exception as e:
        print(f"Erro ao limpar dados: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="VigiaTI - Monitor de Chamados de TI (Marco 2)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Inicializa o keyspace e as tabelas no Cassandra")

    # seed
    p_seed = subparsers.add_parser("seed", help="Popula dados de demonstração (~1000 chamados)")
    p_seed.add_argument("--quantidade", type=int, default=1000, help="Quantidade de chamados a gerar")
    p_seed.add_argument("--equipe", type=str, default=EQUIPE_ID_DEMO, help="UUID da equipe")

    # abrir
    p_abrir = subparsers.add_parser("abrir", help="Abre um novo chamado (RF01)")
    p_abrir.add_argument("--titulo", required=True, help="Título do chamado")
    p_abrir.add_argument("--descricao", required=True, help="Descrição do chamado")
    p_abrir.add_argument("--solicitante", required=True, help="Nome do solicitante")
    p_abrir.add_argument("--tecnico", required=True, choices=TECNICOS, help=f"Técnico responsável ({TECNICOS})")
    p_abrir.add_argument("--equipe", type=str, default=EQUIPE_ID_DEMO, help="UUID da equipe")

    # listar
    p_listar = subparsers.add_parser("listar", help="Lista chamados de uma equipe (RF02)")
    p_listar.add_argument("--equipe", type=str, default=EQUIPE_ID_DEMO, help="UUID da equipe")
    p_listar.add_argument("--limite", type=int, default=20, help="Limite de chamados exibidos")

    # atualizar
    p_atualizar = subparsers.add_parser("atualizar", help="Atualiza o estado de um chamado (RF03)")
    p_atualizar.add_argument("--chamado-id", required=True, help="UUID do chamado")
    p_atualizar.add_argument("--estado", required=True, choices=list(ESTADOS_VALIDOS), help=f"Novo estado ({list(ESTADOS_VALIDOS)})")
    p_atualizar.add_argument("--autor", required=True, help="Autor da atualização")
    p_atualizar.add_argument("--descricao", required=True, help="Descrição da ação realizada")
    p_atualizar.add_argument("--equipe", type=str, default=EQUIPE_ID_DEMO, help="UUID da equipe")

    # historico
    p_historico = subparsers.add_parser("historico", help="Mostra o histórico de eventos de um chamado (RF04)")
    p_historico.add_argument("--chamado-id", required=True, help="UUID do chamado")

    # reconciliar
    p_reconciliar = subparsers.add_parser("reconciliar", help="Recalcula o estado do chamado a partir do evento mais recente")
    p_reconciliar.add_argument("--chamado-id", required=True, help="UUID do chamado")
    p_reconciliar.add_argument("--equipe", type=str, default=EQUIPE_ID_DEMO, help="UUID da equipe")

    # limpar
    subparsers.add_parser("limpar", help="Limpa todos os dados das tabelas")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "seed":
        cmd_seed(args)
    elif args.command == "abrir":
        cmd_abrir(args)
    elif args.command == "listar":
        cmd_listar(args)
    elif args.command == "atualizar":
        cmd_atualizar(args)
    elif args.command == "historico":
        cmd_historico(args)
    elif args.command == "reconciliar":
        cmd_reconciliar(args)
    elif args.command == "limpar":
        cmd_limpar(args)

if __name__ == "__main__":
    main()
