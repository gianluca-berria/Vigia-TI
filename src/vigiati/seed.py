import random
from datetime import datetime, timezone, timedelta
from src.vigiati.config import EQUIPE_ID_DEMO, TECNICOS
from src.vigiati import cassandra_repo, cache, service

TITULOS_EXEMPLOS = [
    "Falha na rede Wi-Fi do 3º andar",
    "Impressora travada no financeiro",
    "Erro de acesso ao sistema ERP",
    "Lentidão na VPN corporativa",
    "Troca de toner da impressora laser",
    "Monitor sem sinal de vídeo",
    "Falha ao autenticar no Active Directory",
    "Atualização de software antivírus pendente",
    "Problema com cabo de rede RJ45 danificado",
    "Solicitação de criação de conta de email"
]

SOLICITANTES = [
    "Ana Silva", "Carlos Souza", "Mariana Costa", "Roberto Alves", 
    "Fernanda Lima", "João Pereira", "Beatriz Santos", "Lucas Oliveira"
]

DESCRICOES_ACOES = [
    "Chamado encaminhado para análise técnica.",
    "Verificado cabo de conexão e reconfigurado switch.",
    "Reiniciado serviço de spooler de impressão.",
    "Aplicado patch de correção e liberado acesso.",
    "Realizada limpeza de cache do navegador e reautenticação.",
    "Substituído componente de hardware defeituoso.",
    "Concluídos testes de conectividade com sucesso.",
    "Orientado usuário sobre boas práticas de segurança."
]

def popular_dados(qtd_chamados=1000, equipe_id=EQUIPE_ID_DEMO):
    print(f"[Seed] Iniciando população de {qtd_chamados} chamados para a equipe {equipe_id}...")
    
    # Limpar dados antes de popular se desejado
    cassandra_repo.limpar_dados()

    agora = datetime.now(timezone.utc)

    for i in range(1, qtd_chamados + 1):
        titulo = f"{random.choice(TITULOS_EXEMPLOS)} #{i}"
        descricao = f"Descrição detalhada do chamado {i}: {random.choice(DESCRICOES_ACOES)}"
        solicitante = random.choice(SOLICITANTES)
        tecnico = random.choice(TECNICOS)
        
        # Distribuir criacao nos ultimos 30 dias
        dias_atras = random.randint(0, 30)
        horas_atras = random.randint(0, 23)
        minutos_atras = random.randint(0, 59)
        criado_em = agora - timedelta(days=dias_atras, hours=horas_atras, minutes=minutos_atras)

        chamado_id = service.uuid.uuid4()
        evento_id_abertura = service.gerar_timeuuid()

        # 1. Evento de abertura
        cassandra_repo.inserir_evento(
            chamado_id=chamado_id,
            evento_id=evento_id_abertura,
            tipo="ABERTURA",
            descricao=f"Chamado aberto: {titulo}",
            autor=solicitante
        )

        # Decidir estado final do chamado (80% RESOLVIDO, 15% EM_ATENDIMENTO, 5% ABERTO)
        rand_estado = random.random()
        if rand_estado < 0.80:
            estado_final = "RESOLVIDO"
            num_acoes = random.randint(2, 9) # total ~10 eventos
        elif rand_estado < 0.95:
            estado_final = "EM_ATENDIMENTO"
            num_acoes = random.randint(1, 5)
        else:
            estado_final = "ABERTO"
            num_acoes = 0

        estado_atual = "ABERTO"
        autor_atual = solicitante

        # Gerar eventos intermediários
        tempo_evento = criado_em
        for a in range(num_acoes):
            tempo_evento += timedelta(minutes=random.randint(15, 120))
            evento_id_acao = service.gerar_timeuuid()
            autor_atual = tecnico

            if a == num_acoes - 1 and estado_final == "RESOLVIDO":
                estado_atual = "RESOLVIDO"
                tipo_evento = "RESOLVIDO"
                desc_evento = "Chamado resolvido e fechado com sucesso."
            elif a == 0 and estado_final != "ABERTO":
                estado_atual = "EM_ATENDIMENTO"
                tipo_evento = "EM_ATENDIMENTO"
                desc_evento = "Chamado assumido pelo técnico para atendimento."
            else:
                estado_atual = "EM_ATENDIMENTO"
                tipo_evento = "EM_ATENDIMENTO"
                desc_evento = f"Ação de andamento #{a+1}: {random.choice(DESCRICOES_ACOES)}"

            cassandra_repo.inserir_evento(
                chamado_id=chamado_id,
                evento_id=evento_id_acao,
                tipo=tipo_evento,
                descricao=desc_evento,
                autor=autor_atual
            )

        if estado_final == "RESOLVIDO" and estado_atual != "RESOLVIDO":
            estado_atual = "RESOLVIDO"
            evento_id_res = service.gerar_timeuuid()
            cassandra_repo.inserir_evento(
                chamado_id=chamado_id,
                evento_id=evento_id_res,
                tipo="RESOLVIDO",
                descricao="Chamado finalizado e resolvido.",
                autor=tecnico
            )

        # 2. Salvar linha principal em chamados_por_equipe
        cassandra_repo.salvar_chamado(
            equipe_id=equipe_id,
            chamado_id=chamado_id,
            criado_em=criado_em,
            titulo=titulo,
            descricao=descricao,
            solicitante=solicitante,
            tecnico=tecnico,
            estado=estado_atual
        )

        if i % 100 == 0:
            print(f"[Seed] Progresso: {i}/{qtd_chamados} chamados inseridos...")

    print(f"[Seed] Concluído! {qtd_chamados} chamados populados com sucesso.")
