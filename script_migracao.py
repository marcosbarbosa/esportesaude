# ==============================================================================
# Arquivo: script_migracao.py
# Função:  Backup Supabase + Migração completa do CSV migraimbra2_2.csv
# Versão:  4.0 — Todos os campos mapeados (23 colunas)
# ==============================================================================

import pandas as pd
import datetime
import os

from database import supabase

ARQUIVO_CSV = "migraimbra2_2.csv"
ARQUIVO_LOG = f"resultado_migracao_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"


# ──────────────────────────────────────────────
# Utilitário: converter data DD/MM/YYYY → YYYY-MM-DD
# ──────────────────────────────────────────────
def converter_data(valor) -> str | None:
    valor = str(valor).strip()
    if not valor or valor.lower() in ("nan", "none", ""):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(valor, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────
# Utilitário: limpar string vazia / nan
# ──────────────────────────────────────────────
def limpar(valor) -> str | None:
    v = str(valor).strip()
    return v if v and v.lower() not in ("nan", "none") else None


# ──────────────────────────────────────────────
# 1. BACKUP
# ──────────────────────────────────────────────
def fazer_backup():
    print("Iniciando backup de segurança do Supabase...")
    resp  = supabase.table("alunos").select("*").execute()
    dados = resp.data
    if not dados:
        print("Aviso: nenhum registro encontrado para backup.")
        return False
    df  = pd.DataFrame(dados)
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    arq = f"backup_alunos_antes_migracao_{ts}.csv"
    df.to_csv(arq, index=False)
    print(f"Backup salvo: {arq}\n")
    return True


# ──────────────────────────────────────────────
# 2. MIGRAÇÃO
# ──────────────────────────────────────────────
def rodar_migracao(log_linhas: list):

    def out(msg):
        print(msg)
        log_linhas.append(msg)

    if not os.path.exists(ARQUIVO_CSV):
        out(f"Erro crítico: arquivo '{ARQUIVO_CSV}' não encontrado.")
        return

    df = pd.read_csv(ARQUIVO_CSV).fillna("")
    df.columns = df.columns.str.strip()
    out(f"Lendo '{ARQUIVO_CSV}' — {len(df)} registros encontrados.\n")

    # ── Mapeamento CSV → banco ──────────────────────────────────────────────
    MAPA = {
        # label display          : (coluna_csv,                                                                        coluna_db,                     tipo)
        "Nome"                   : ("Nome completo",                                                                   "nome",                        "str"),
        "E-mail"                 : ("Endereço de e-mail",                                                              "email",                       "str"),
        "E-mail 2"               : ("E mail",                                                                          "email",                       "str"),
        "Endereço"               : ("Endereço",                                                                        "endereco",                    "str"),
        "Complemento"            : ("Complemento",                                                                     "_complemento",                "str"),
        "Bairro"                 : ("Bairro",                                                                          "bairro",                      "str"),
        "CEP"                    : ("CEP",                                                                             "cep",                         "str"),
        "Celular"                : ("Celular",                                                                         "whatsapp",                    "str"),
        "Nascimento"             : ("Data de nascimento",                                                              "data_nascimento",             "data"),
        "CPF"                    : ("CPF",                                                                             "cpf",                         "str"),
        "RG"                     : ("RG",                                                                              "rg",                          "str"),
        "Ct. Emergência"         : ("Em caso de alguma ocorrência indesejada, a quem podemos comunicar/avisar? Nome e Telefone.", "contato_emergencia", "str"),
        "Medicamentos"           : ("Além das atividades físicas do Imbra.\nQuantas vezes por semana você pratica atividades físicas?\nQuais atividades físicas? \nPor quanto tempo?", "medicamentos", "str"),
        "Grau de instrução"      : ("Grau de instrução",                                                               "grau_instrucao",              "str"),
        "Fonte de renda"         : ("Principal fonte de renda.",                                                        "principal_fonte_renda",       "str"),
        "Faixa de renda"         : ("Qual a renda da sua casa contando todos os moradores?",                           "faixa_renda",                 "str"),
        "Naturalidade"           : ("Naturalidade",                                                                    "naturalidade",                "str"),
        "Sexo"                   : ("Sexo",                                                                            "sexo",                        "str"),
        "Estado civil"           : ("Estado cívil",                                                                    "estado_civil",                "str"),
        "Aposentado"             : ("Aposentado?",                                                                     "aposentado",                  "str"),
        "Nome cônjuge"           : ("Nome do conjuge",                                                                 "nome_conjuge",                "str"),
        "Qtd. moradores"         : ("Quantos residentes em sua moradia?",                                              "qtd_moradores",               "str"),
        "Vol. interesse"         : ("Interesse em trabalho voluntário?",                                               "trabalho_voluntario_interesse","str"),
        "Vol. áreas"             : ("Quais áreas de trabalho voluntário você participaria?",                           "trabalho_voluntario_areas",   "str"),
        "Anamnese incômodo"      : ("Você sente algum incômodo durante ou após a pratica de atividades físicas? Descreva", "anamnese_incomodo_atividade", "str"),
    }

    out("Verificação de colunas no CSV:")
    for label, (col_csv, col_db, _) in MAPA.items():
        if col_db.startswith("_"):
            continue
        presente = col_csv in df.columns
        out(f"  {'OK' if presente else 'FALTA':5s} {label:20s} → '{col_csv[:55]}'")
    out("")

    sucessos = 0
    novos    = 0
    erros    = 0

    for _, row in df.iterrows():
        nome = limpar(row.get("Nome completo", ""))
        if not nome:
            continue
        nome_upper = nome.strip().upper()

        # E-mail: preferir campo "E mail" se preenchido, senão "Endereço de e-mail"
        email = limpar(row.get("E mail", "")) or limpar(row.get("Endereço de e-mail", ""))

        # Endereço: juntar endereço + complemento
        end  = limpar(row.get("Endereço", ""))
        comp = limpar(row.get("Complemento", ""))
        endereco = f"{end}, {comp}" if end and comp else (end or comp)

        payload = {}

        if email:    payload["email"]    = email
        if endereco: payload["endereco"] = endereco

        # Campos diretos
        campos_diretos = [
            ("Bairro",                                                                          "bairro"),
            ("CEP",                                                                             "cep"),
            ("Celular",                                                                         "whatsapp"),
            ("CPF",                                                                             "cpf"),
            ("RG",                                                                              "rg"),
            ("Em caso de alguma ocorrência indesejada, a quem podemos comunicar/avisar? Nome e Telefone.", "contato_emergencia"),
            ("Além das atividades físicas do Imbra.\nQuantas vezes por semana você pratica atividades físicas?\nQuais atividades físicas? \nPor quanto tempo?", "medicamentos"),
            ("Grau de instrução",                                                               "grau_instrucao"),
            ("Principal fonte de renda.",                                                       "principal_fonte_renda"),
            ("Qual a renda da sua casa contando todos os moradores?",                          "faixa_renda"),
            ("Naturalidade",                                                                    "naturalidade"),
            ("Sexo",                                                                            "sexo"),
            ("Estado cívil",                                                                    "estado_civil"),
            ("Aposentado?",                                                                     "aposentado"),
            ("Nome do conjuge",                                                                 "nome_conjuge"),
            ("Quantos residentes em sua moradia?",                                             "qtd_moradores"),
            ("Interesse em trabalho voluntário?",                                               "trabalho_voluntario_interesse"),
            ("Quais áreas de trabalho voluntário você participaria?",                          "trabalho_voluntario_areas"),
            ("Você sente algum incômodo durante ou após a pratica de atividades físicas? Descreva", "anamnese_incomodo_atividade"),
        ]

        for col_csv, col_db in campos_diretos:
            v = limpar(row.get(col_csv, ""))
            if v:
                payload[col_db] = v

        # Data de nascimento (conversão de formato)
        nasc = converter_data(row.get("Data de nascimento", ""))
        if nasc:
            payload["data_nascimento"] = nasc

        if not payload:
            continue

        try:
            busca = (
                supabase.table("alunos")
                .select("id")
                .ilike("nome", f"%{nome_upper}%")
                .execute()
            )

            if busca.data:
                aluno_id = busca.data[0]["id"]
                supabase.table("alunos").update(payload).eq("id", aluno_id).execute()
                out(f"[ATUALIZADO] {nome_upper}")
                sucessos += 1
            else:
                payload["nome"]   = nome_upper
                payload["status"] = "Ativo"
                supabase.table("alunos").insert(payload).execute()
                out(f"[NOVO ALUNO] {nome_upper}")
                novos    += 1
                sucessos += 1

        except Exception as e:
            out(f"[ERRO]       {nome_upper} — {e}")
            erros += 1

    sep = "=" * 56
    out(f"\n{sep}")
    out("RELATÓRIO EXECUTIVO DE MIGRAÇÃO — v4.0")
    out(sep)
    out(f"  Registros no CSV      : {len(df)}")
    out(f"  Processados           : {sucessos + erros}")
    out(f"  Atualizados           : {sucessos - novos}")
    out(f"  Novos inseridos       : {novos}")
    out(f"  Rejeitados (erro)     : {erros}")
    out(sep)


# ──────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ──────────────────────────────────────────────
if __name__ == "__main__":
    log_linhas = []

    backup_ok = fazer_backup()

    if backup_ok:
        rodar_migracao(log_linhas)

        with open(ARQUIVO_LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(log_linhas))
        print(f"\nLog salvo em: {ARQUIVO_LOG}")
