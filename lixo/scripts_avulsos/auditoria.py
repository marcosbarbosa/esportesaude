import pandas as pd
from supabase import create_client
import streamlit as st

print("⏳ A ligar ao banco de dados...")
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

print("🔍 A extrair lista completa de alunos...")
# Puxa todos os alunos organizados por ordem alfabética
resposta = supabase.table("alunos").select("nome, turma, data_nascimento").order("nome").execute()
df = pd.DataFrame(resposta.data)

# Renomeia as colunas para ficar elegante
df.rename(columns={'nome': 'Nome do Aluno', 'turma': 'Turma', 'data_nascimento': 'Data de Nascimento'}, inplace=True)

# Gera o ficheiro Excel
nome_ficheiro = "Auditoria_Alunos.xlsx"
df.to_excel(nome_ficheiro, index=False)

print(f"🏁 Concluído! O ficheiro '{nome_ficheiro}' foi gerado com sucesso!")