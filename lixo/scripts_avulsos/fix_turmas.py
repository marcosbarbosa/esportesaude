# ==============================================================================
# 📄 Arquivo: fix_turmas.py
# ⚙️ Função: Diagnosticar e reparar alunos presos em turmas com nomes antigos.
# ==============================================================================
import pandas as pd
from database import supabase

def iniciar_diagnostico():
    print("\n" + "="*50)
    print("🔍 INICIANDO AUDITORIA DE TURMAS...")
    print("="*50)

    # 1. Descobrir os Nomes Oficiais (Atuais) das Turmas
    res_t = supabase.table('turmas').select('nome').execute()
    turmas_oficiais = [t['nome'] for t in res_t.data]
    print(f"\n✅ Nomes Oficiais Encontrados: {turmas_oficiais}")

    # 2. Descobrir onde os Alunos e Diários estão matriculados
    res_a = supabase.table('alunos').select('id, nome, turma').execute()
    df_alunos = pd.DataFrame(res_a.data)

    if df_alunos.empty:
        print("Nenhum aluno encontrado.")
        return

    turmas_dos_alunos = df_alunos['turma'].unique()
    print(f"👥 Nomes de Turmas presentes na ficha dos alunos: {turmas_dos_alunos}")

    # 3. Cruzar os dados para achar as "Turmas Fantasmas"
    turmas_fantasmas = [t for t in turmas_dos_alunos if t not in turmas_oficiais]

    if not turmas_fantasmas:
        print("\n🎉 EXCELENTE! Não existem alunos perdidos em turmas antigas.")
        return

    print(f"\n⚠️ ALERTA: Encontrámos as seguintes Turmas Fantasmas (Nomes antigos): {turmas_fantasmas}")
    print("-" * 50)
    print("🛠️ MODO DE CORREÇÃO INTERATIVA")
    print("-" * 50)

    # 4. Assistente de Reparação
    for fantasma in turmas_fantasmas:
        qtd_afetados = len(df_alunos[df_alunos['turma'] == fantasma])
        print(f"\nA turma antiga '{fantasma}' tem {qtd_afetados} aluno(s) refém(ns).")

        # Pedimos ao operador para qual nome atual eles devem ser movidos
        novo_nome = input(f"👉 Digite o NOME OFICIAL EXATO para onde eles devem ir: ")

        if novo_nome in turmas_oficiais:
            # Força a atualização na base de dados dos Alunos
            supabase.table('alunos').update({'turma': novo_nome}).eq('turma', fantasma).execute()

            # Força a atualização nos Diários de Aula (para não perder o histórico)
            supabase.table('diario_aulas').update({'turma': novo_nome}).eq('turma', fantasma).execute()

            print(f"✅ SUCESSO! Todos os registos de '{fantasma}' foram movidos para '{novo_nome}'.")
        else:
            print("❌ Nome inválido ou não digitado exatamente como nas Turmas Oficiais. A ignorar...")

if __name__ == "__main__":
    iniciar_diagnostico()