import pandas as pd
from supabase import create_client
import streamlit as st

# Conecta ao Supabase usando os segredos do seu Replit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)


def arrumar_data(data_suja):
    """Tenta transformar os formatos do Excel em data limpa (YYYY-MM-DD)"""
    try:
        data_str = str(data_suja).strip()
        if len(data_str) == 8 and data_str.isdigit():  # Ex: 09031962
            return f"{data_str[4:8]}-{data_str[2:4]}-{data_str[0:2]}"
        else:
            dt = pd.to_datetime(data_str, format="%d/%m/%Y", errors="coerce")
            if pd.notna(dt):
                return dt.strftime("%Y-%m-%d")
            dt = pd.to_datetime(data_str, errors="coerce")
            return dt.strftime("%Y-%m-%d") if pd.notna(dt) else None
    except:
        return None


print("⏳ Lendo CSV...")
df = pd.read_csv("dados.csv", sep=";", encoding="latin-1")

df_validos = df.dropna(subset=["Nome completo ", "Data de nascimento"])

print("🚀 Iniciando envio seguro para o Supabase...")
for _, row in df_validos.iterrows():
    # Limpa e padroniza o nome do Excel para ficar idêntico ao Banco de Dados
    nome = str(row["Nome completo "]).strip().upper()
    data_nasc = arrumar_data(row["Data de nascimento"])

    if data_nasc:
        # 🚀 MUDANÇA SENIOR: Trocado 'ilike' por 'eq' (Busca Exata) para evitar sobrescrever alunos com nomes parecidos
        res = (
            supabase.table("alunos")
            .update({"data_nascimento": data_nasc})
            .eq("nome", nome)
            .execute()
        )

        # Verifica se realmente encontrou e atualizou alguém
        if res.data:
            print(f"✅ {nome} atualizado! Niver: {data_nasc}")
        else:
            print(f"⚠️ {nome} não encontrado no banco de dados (verifique a grafia).")

print("🏁 Importação Concluída com Sucesso!")
