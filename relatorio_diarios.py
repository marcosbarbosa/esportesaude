# ==============================================================================
# 📄 ARQUIVO: relatorio_diarios.py
# 🎯 FUNÇÃO: Extrair um relatório de todas as turmas e os dias registados no diário.
# ==============================================================================

import pandas as pd
# Importamos a nossa conexão oficial com o banco de dados que já criamos
from database import supabase 

def gerar_relatorio():
    print("\n" + "="*60)
    print("📊 GERANDO RELATÓRIO DE DIÁRIOS DE AULA...")
    print("="*60)

    try:
        # 1. FAZER A PERGUNTA AO BANCO DE DADOS
        # Pedimos apenas as colunas "turma" e "data_aula" da tabela "diario_aulas"
        resposta = supabase.table("diario_aulas").select("turma, data_aula").execute()

        # 2. VERIFICAR SE EXISTEM DADOS
        dados = resposta.data
        if not dados:
            print("❌ Nenhum diário de aula foi encontrado no banco de dados.")
            return

        # 3. ORGANIZAR COM O PANDAS
        # Transformamos a resposta num DataFrame (uma tabela virtual inteligente)
        df = pd.DataFrame(dados)

        # Convertendo a coluna de datas para o formato oficial de data
        # Isso ajuda a ordenar cronologicamente
        df['data_aula'] = pd.to_datetime(df['data_aula']).dt.strftime('%d/%m/%Y')

        # 4. AGRUPAR OS DADOS (O MÁGICO DO PANDAS)
        # Juntamos todas as datas que pertencem à mesma turma numa lista única
        relatorio = df.groupby('turma')['data_aula'].apply(list).reset_index()

        # 5. MOSTRAR O RESULTADO NO ECRÃ
        print("\n✅ Relatório concluído! Veja os resultados abaixo:\n")

        # Iteramos sobre cada turma encontrada
        for index, linha in relatorio.iterrows():
            nome_da_turma = linha['turma']
            datas_registadas = linha['data_aula']
            quantidade_dias = len(datas_registadas)

            # Ordenamos as datas para ficar mais bonito de ler
            datas_registadas.sort()

            # Imprimimos de forma estilizada
            print(f"🏫 TURMA: {nome_da_turma}")
            print(f"   📅 Dias registados ({quantidade_dias} aulas): {', '.join(datas_registadas)}")
            print("-" * 60)

    except Exception as e:
        print(f"\n❌ Ocorreu um erro ao gerar o relatório: {e}")

# Esta linha garante que o script só roda se o executarmos diretamente
if __name__ == "__main__":
    gerar_relatorio()