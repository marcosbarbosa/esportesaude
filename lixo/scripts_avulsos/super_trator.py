import pandas as pd
import re
from supabase import create_client
import streamlit as st

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def super_limpeza_data(data_suja):
    """O Aspirador Inteligente de Datas"""
    try:
        if pd.isna(data_suja): return None
        d_str = str(data_suja).strip()

        # 1. Tenta decifrar formatos com barras, hífens ou pontos (Brasil: Dia primeiro)
        dt = pd.to_datetime(d_str, dayfirst=True, errors='coerce')
        if pd.notna(dt) and 1920 <= dt.year <= 2026:
            return dt.strftime('%Y-%m-%d')

        # 2. Se falhou, tira TUDO que não for número (letras, pontos, espaços)
        apenas_numeros = re.sub(r'\D', '', d_str)

        # 3. Se sobraram exatamente 8 números, remonta o DD/MM/YYYY
        if len(apenas_numeros) == 8:
            dia = apenas_numeros[0:2]
            mes = apenas_numeros[2:4]
            ano = apenas_numeros[4:8]
            if 1920 <= int(ano) <= 2026 and 1 <= int(mes) <= 12 and 1 <= int(dia) <= 31:
                return f"{ano}-{mes}-{dia}"

        return None
    except: return None

print("⏳ Ligando o Super Trator 2.0...")
# Lê o seu Excel novamente
df = pd.read_csv("dados.csv", sep=';', encoding='latin-1')
df_validos = df.dropna(subset=['Nome completo ', 'Data de nascimento'])

print("🧹 Iniciando limpeza profunda e envio...")
for _, row in df_validos.iterrows():
    nome = str(row['Nome completo ']).strip().upper()
    data_suja = row['Data de nascimento']
    data_limpa = super_limpeza_data(data_suja)

    if data_limpa:
        res = supabase.table("alunos").update({"data_nascimento": data_limpa}).ilike("nome", f"%{nome}%").execute()
        if res.data:
            print(f"✅ SALVO! {nome}: '{data_suja}' virou -> {data_limpa}")
    else:
        print(f"❌ PERDIDO: {nome} (A data '{data_suja}' é indecifrável)")

print("🏁 Limpeza Concluída!")