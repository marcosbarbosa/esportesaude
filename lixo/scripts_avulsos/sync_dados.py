# ==============================================================================
# 📄 Arquivo: sync_dados.py
# 🏷️ VERSÃO: 7.0 (PRO Elite - TITANIUM: Zero Dependências Externas)
# ⚙️ FUNÇÃO: API REST Direta via urllib. Imune a erros do Replit/Pydantic/Pandas.
# ==============================================================================

import csv
import json
import urllib.request
import urllib.error
import unicodedata
import datetime
import re
import os

print("\n==================================================")
print("🚀 INICIANDO MIGRAÇÃO TITANIUM (ZERO DEPENDÊNCIAS)")
print("==================================================\n")
print("🔑 1. A extrair chaves e a montar comunicação REST direta...")

try:
    with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
        conteudo = f.read()
        url_match = re.search(r'SUPABASE_URL\s*=\s*[\'"]([^\'"]+)[\'"]', conteudo)
        key_match = re.search(r'SUPABASE_KEY\s*=\s*[\'"]([^\'"]+)[\'"]', conteudo)

        if not url_match or not key_match:
            print("❌ Falha: Chaves não encontradas no ficheiro secrets.toml.")
            exit()

        SUPABASE_URL = url_match.group(1).rstrip("/")
        SUPABASE_KEY = key_match.group(1)

        HEADERS = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
except Exception as e:
    print(f"❌ Erro fatal ao ler credenciais: {e}")
    exit()


# ==============================================================================
# 🛠️ FUNÇÕES DE TRATAMENTO DE DADOS
# ==============================================================================
def normalizar_nome(nome):
    if not nome or str(nome).strip() == "":
        return ""
    n = str(nome).strip().lower()
    n = "".join(
        c for c in unicodedata.normalize("NFD", n) if unicodedata.category(c) != "Mn"
    )
    return n


def formatar_data(data_br):
    if not data_br or str(data_br).strip() == "":
        return None, None
    try:
        data_limpa = str(data_br).strip().split(" ")[0].replace("-", "/")
        data_formatada = datetime.datetime.strptime(data_limpa, "%d/%m/%Y").strftime(
            "%Y-%m-%d"
        )
        return data_formatada, None
    except Exception:
        return None, str(data_br)


def limpar_numero(num):
    if not num or str(num).strip() == "":
        return None
    limpo = re.sub(r"\D", "", str(num))
    return limpo if limpo else None


# ==============================================================================
# ⚙️ MOTOR DE MIGRAÇÃO VIA REST API (HTTP NATIVO)
# ==============================================================================
print("📥 2. A descarregar a base atual (Via HTTP REST API)...")
try:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/alunos?select=*", headers=HEADERS
    )
    with urllib.request.urlopen(req) as response:
        alunos_db = json.loads(response.read().decode("utf-8"))
    mapa_alunos_db = {normalizar_nome(a["nome"]): a for a in alunos_db if "nome" in a}
except Exception as e:
    print(f"❌ Erro ao ligar à API do Supabase: {e}")
    exit()

nome_arquivo_csv = "imb.csv"
print(f"📂 3. A ler o ficheiro de origem: {nome_arquivo_csv}...\n")

total_lidos = 0
lista_migrados = []
lista_nao_migrados = []

try:
    with open(nome_arquivo_csv, mode="r", encoding="utf-8-sig") as f:
        leitor_csv = csv.DictReader(f)

        for row in leitor_csv:
            nome_csv = str(row.get("Nome completo ", "")).strip()
            if not nome_csv:
                continue

            total_lidos += 1
            nome_norm = normalizar_nome(nome_csv)

            data_raw = row.get("Data de nascimento")
            data_nasc, erro_data = formatar_data(data_raw)

            if erro_data:
                msg_erro = f"[NÃO MIGRADO] {nome_csv.upper()} | ERRO: Data inválida '{erro_data}'"
                print(f"❌ {msg_erro}")
                lista_nao_migrados.append(msg_erro)
                continue

            cpf = limpar_numero(row.get("CPF"))
            rg = limpar_numero(row.get("RG"))
            telefone = limpar_numero(row.get("Celular"))

            email = str(row.get("Endereço de e-mail", "")).strip()
            if not email:
                email = None

            end_parts = []
            if row.get("Endereço"):
                end_parts.append(str(row.get("Endereço")).strip())
            if row.get("Complemento"):
                end_parts.append(str(row.get("Complemento")).strip())
            if row.get("Bairro"):
                end_parts.append(str(row.get("Bairro")).strip())
            endereco_completo = ", ".join(end_parts) if end_parts else None

            dados_linha = f"Data: {data_nasc} | CPF: {cpf or 'Vazio'} | Tel: {telefone or 'Vazio'}"

            if nome_norm in mapa_alunos_db:
                aluno_atual = mapa_alunos_db[nome_norm]
                payload_update = {}

                if data_nasc and str(aluno_atual.get("data_nascimento")) != str(
                    data_nasc
                ):
                    payload_update["data_nascimento"] = data_nasc
                if not aluno_atual.get("cpf") and cpf:
                    payload_update["cpf"] = cpf
                if not aluno_atual.get("rg") and rg:
                    payload_update["rg"] = rg
                if not aluno_atual.get("whatsapp") and telefone:
                    payload_update["whatsapp"] = telefone
                if not aluno_atual.get("email") and email:
                    payload_update["email"] = email.lower()
                if not aluno_atual.get("endereco") and endereco_completo:
                    payload_update["endereco"] = endereco_completo

                if payload_update:
                    try:
                        patch_url = (
                            f"{SUPABASE_URL}/rest/v1/alunos?id=eq.{aluno_atual['id']}"
                        )
                        req_patch = urllib.request.Request(
                            patch_url,
                            data=json.dumps(payload_update).encode("utf-8"),
                            headers=HEADERS,
                            method="PATCH",
                        )
                        with urllib.request.urlopen(req_patch) as res:
                            pass  # Sucesso silenciado
                        msg_suc = f"[ATUALIZADO] {nome_csv.upper()} -> {dados_linha}"
                        print(f"🔄 {msg_suc}")
                        lista_migrados.append(msg_suc)
                    except Exception as e:
                        msg_erro = (
                            f"[NÃO MIGRADO] {nome_csv.upper()} | ERRO API PATCH: {e}"
                        )
                        print(f"❌ {msg_erro}")
                        lista_nao_migrados.append(msg_erro)
            else:
                try:
                    payload_insert = {
                        "nome": nome_csv.upper(),
                        "data_nascimento": data_nasc,
                        "cpf": cpf,
                        "rg": rg,
                        "whatsapp": telefone,
                        "email": email.lower() if email else None,
                        "endereco": endereco_completo,
                        "status": "Ativo",
                        "turma": "Turma Padrão",
                    }
                    insert_url = f"{SUPABASE_URL}/rest/v1/alunos"
                    req_insert = urllib.request.Request(
                        insert_url,
                        data=json.dumps(payload_insert).encode("utf-8"),
                        headers=HEADERS,
                        method="POST",
                    )
                    with urllib.request.urlopen(req_insert) as res:
                        pass  # Sucesso silenciado
                    msg_suc = f"[NOVO ALUNO] {nome_csv.upper()} -> {dados_linha}"
                    print(f"✨ {msg_suc}")
                    lista_migrados.append(msg_suc)
                except Exception as e:
                    msg_erro = (
                        f"[NÃO MIGRADO] {nome_csv.upper()} | ERRO API INSERT: {e}"
                    )
                    print(f"❌ {msg_erro}")
                    lista_nao_migrados.append(msg_erro)

except Exception as e:
    print(f"❌ ERRO CRÍTICO AO LER O CSV: {e}")
    exit()

# ==============================================================================
# 📊 GERAÇÃO DO FICHEIRO DE RELATÓRIO FINAL
# ==============================================================================
print("\n==================================================")
print("✅ PROCESSAMENTO CONCLUÍDO (MODO TITANIUM)!")
print(f"📈 Total Lidos no CSV: {total_lidos}")
print(f"🎯 Total Salvos/Atualizados: {len(lista_migrados)}")
print(f"⚠️ Total Rejeitados/Erros: {len(lista_nao_migrados)}")
print("==================================================\n")

with open("Relatorio_Migracao_Completo.txt", "w", encoding="utf-8") as f:
    f.write("==================================================\n")
    f.write("📋 RELATÓRIO OFICIAL DE MIGRAÇÃO (LINHA A LINHA)\n")
    f.write("==================================================\n\n")

    f.write(
        f"⚠️ DADOS NÃO MIGRADOS (REVISÃO MANUAL NECESSÁRIA: {len(lista_nao_migrados)})\n"
    )
    f.write("-" * 50 + "\n")
    for erro in lista_nao_migrados:
        f.write(f"{erro}\n")

    f.write(f"\n\n✅ DADOS MIGRADOS COM SUCESSO (TOTAL: {len(lista_migrados)})\n")
    f.write("-" * 50 + "\n")
    for suc in lista_migrados:
        f.write(f"{suc}\n")

print(
    "📝 O detalhamento completo foi guardado no ficheiro: 'Relatorio_Migracao_Completo.txt'"
)
