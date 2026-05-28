# ==============================================================================
# 📄 ARQUIVO: migracao_clinica.py
# 🏷️ VERSÃO: 1.0 — Migração Clínica IMBRA (CSV → Supabase)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Lê migraimbra2_2.csv e injeta dados clínicos em formato #hashtag
#            no campo problemas_saude da tabela alunos no Supabase.
#            Match por CPF (principal) ou Nome (fallback fonético).
#            Contato de emergência: concatena se diferente do banco.
#
# USO:
#   python3 migracao_clinica.py              → Modo DRY-RUN (apenas mostra)
#   python3 migracao_clinica.py --executar   → Executa as atualizações no BD
# ==============================================================================

import csv
import sys
import json
import datetime
import unicodedata
import re
import urllib.request
import urllib.parse
import tomllib

# ── Configuração ──────────────────────────────────────────────────────────────
CSV_PATH = "migraimbra2_2.csv"
DRY_RUN = "--executar" not in sys.argv

# Mapeamento de colunas do CSV (índices 0-based, verificado em 28/05/2026)
COL_NOME       = 2
COL_CPF        = 14
COL_PATOLOGIAS = 18   # 'Liste seus problemas de saúde.'
COL_INCOMODO1  = 21   # 'Você sente algum incômodo durante ou após...'
COL_INCOMODO2  = 34   # 'Coluna 1' (segundo campo de incômodo, frequentemente vazio)
COL_ALERGIAS   = 17   # 'Você é alérgico a algum medicamento? Quais?'
COL_MEDICAMENT = 16   # 'Você faz uso contínuo de medicamentos? Quais?'
COL_RESTRICOES = 19   # 'Você possui alguma restrição...'
COL_OUTRAS_AT  = 20   # 'Além das atividades físicas do Imbra...'
COL_EMERGENCIA = 22   # 'Em caso de alguma ocorrência...'

VALORES_NULOS = {
    "", "não", "nao", "nao.", "não.", "no", "n", "n/a", "na",
    "nenhum", "nenhuma", "nenhuma.", "nenhum.",
    "nenhuma restrição", "sem restrições", "sem restricoes",
    "não informado", "nao informado", "nd",
}


# ── Normalização ──────────────────────────────────────────────────────────────
def remover_acentos(t: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    ).lower()


def normalizar_nome(t: str) -> str:
    return re.sub(r"\s+", " ", remover_acentos(str(t).strip()))


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", str(cpf).strip())


def limpar_valor(v: str) -> str:
    """Retorna None se o valor for considerado 'sem informação'."""
    v = str(v).strip()
    if remover_acentos(v) in VALORES_NULOS:
        return ""
    # Só números sozinhos (ex: "2", "0") — mantém mas avisa
    return v


def get_val(row: list, idx: int) -> str:
    try:
        return limpar_valor(row[idx])
    except IndexError:
        return ""


# ── Carrega segredos Supabase ─────────────────────────────────────────────────
with open(".streamlit/secrets.toml", "rb") as f:
    _s = tomllib.load(f)
SUPA_URL = _s["SUPABASE_URL"].rstrip("/")
SUPA_KEY = _s["SUPABASE_KEY"]
HEADERS  = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


# ── Helpers REST ──────────────────────────────────────────────────────────────
def supa_get(endpoint: str) -> list:
    req = urllib.request.Request(f"{SUPA_URL}/rest/v1/{endpoint}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def supa_patch(table: str, id_: int, payload: dict) -> bool:
    url  = f"{SUPA_URL}/rest/v1/{table}?id=eq.{id_}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method="PATCH")
    try:
        with urllib.request.urlopen(req):
            return True
    except urllib.error.HTTPError as e:
        print(f"      ❌ PATCH error {e.code}: {e.read().decode()}")
        return False


# ── Carrega todos os alunos do banco ─────────────────────────────────────────
def carregar_alunos_bd() -> list:
    print("📡 Carregando alunos do Supabase…")
    alunos, offset = [], 0
    while True:
        chunk = supa_get(
            f"alunos?select=id,nome,cpf,contato_emergencia,problemas_saude"
            f"&limit=1000&offset={offset}"
        )
        if not chunk:
            break
        alunos.extend(chunk)
        if len(chunk) < 1000:
            break
        offset += 1000
    print(f"   ✅ {len(alunos)} alunos carregados do banco.")
    return alunos


# ── Salva backup CSV ──────────────────────────────────────────────────────────
def salvar_backup(alunos: list):
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"backup_migracao_clinica_{ts}.csv"
    campos = ["id", "nome", "cpf", "contato_emergencia", "problemas_saude"]
    with open(nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for a in alunos:
            w.writerow({k: a.get(k, "") for k in campos})
    print(f"   💾 Backup salvo: {nome}")


# ── Monta o campo problemas_saude em formato #hashtag ─────────────────────────
def montar_problemas_saude(row: list) -> str:
    secoes = []

    def add(titulo: str, valor: str):
        if valor:
            secoes.append(f"#{titulo}:\n{valor.strip()}")

    add("Patologias",               get_val(row, COL_PATOLOGIAS))
    add("Alergias",                 get_val(row, COL_ALERGIAS))
    add("Uso_Contínuo_Medicamentos", get_val(row, COL_MEDICAMENT))
    add("Restrições_Físicas",       get_val(row, COL_RESTRICOES))
    add("Outras_Atividades",        get_val(row, COL_OUTRAS_AT))

    # Incômodos: col 21 e 34 — une se diferentes e não-vazios
    inc1 = get_val(row, COL_INCOMODO1)
    inc2 = get_val(row, COL_INCOMODO2)
    if inc1 and inc2:
        n1, n2 = remover_acentos(inc1), remover_acentos(inc2)
        inc_final = inc1 if n1 == n2 else f"{inc1} / {inc2}"
    else:
        inc_final = inc1 or inc2
    add("Incômodos_Físicos", inc_final)

    return "\n\n".join(secoes)


# ── Mescla contato de emergência ──────────────────────────────────────────────
def mesclar_contato(bd_val: str | None, csv_val: str) -> str | None:
    bd  = str(bd_val or "").strip()
    csv = csv_val.strip() if csv_val else ""
    if not csv:
        return None  # nada a fazer
    if not bd:
        return csv
    if remover_acentos(bd) == remover_acentos(csv):
        return None  # iguais — sem mudança
    return f"{bd} | {csv}"


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 70)
    print(f"  MIGRAÇÃO CLÍNICA IMBRA — {'DRY-RUN (simulação)' if DRY_RUN else '🔴 EXECUÇÃO REAL'}")
    print("=" * 70)
    if DRY_RUN:
        print("  ⚠️  Modo simulação ativo. Use --executar para gravar no banco.")
    print()

    # Carrega alunos do banco
    alunos_bd = carregar_alunos_bd()
    if not DRY_RUN:
        salvar_backup(alunos_bd)

    # Indexa por CPF e por nome
    idx_cpf  : dict[str, dict] = {}
    idx_nome : dict[str, dict] = {}
    for a in alunos_bd:
        cpf_limpo = normalizar_cpf(a.get("cpf") or "")
        if cpf_limpo:
            idx_cpf[cpf_limpo] = a
        nm = normalizar_nome(a.get("nome") or "")
        if nm:
            idx_nome[nm] = a

    # Lê CSV
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    cabecalho, dados = rows[0], rows[1:]
    print(f"📂 CSV carregado: {len(dados)} linhas de alunos.")
    print()

    # Contadores
    cnt_match_cpf  = 0
    cnt_match_nome = 0
    cnt_sem_match  = 0
    cnt_atualizados = 0
    sem_match_lista: list[str] = []

    for i, row in enumerate(dados, 1):
        csv_nome = str(row[COL_NOME]).strip() if len(row) > COL_NOME else ""
        csv_cpf  = normalizar_cpf(row[COL_CPF]) if len(row) > COL_CPF else ""

        # Tenta match
        aluno_bd = None
        via = ""
        if csv_cpf and csv_cpf in idx_cpf:
            aluno_bd = idx_cpf[csv_cpf]
            via = "CPF"
            cnt_match_cpf += 1
        else:
            nm = normalizar_nome(csv_nome)
            if nm in idx_nome:
                aluno_bd = idx_nome[nm]
                via = "Nome"
                cnt_match_nome += 1

        if not aluno_bd:
            cnt_sem_match += 1
            sem_match_lista.append(csv_nome)
            print(f"  ⚠️  [{i:03d}] SEM MATCH: '{csv_nome}' (CPF: '{csv_cpf}')")
            continue

        # Monta dados
        novo_ps  = montar_problemas_saude(row)
        csv_em   = get_val(row, COL_EMERGENCIA)
        novo_ct  = mesclar_contato(aluno_bd.get("contato_emergencia"), csv_em)

        payload: dict = {}
        if novo_ps:
            payload["problemas_saude"] = novo_ps
        if novo_ct is not None:
            payload["contato_emergencia"] = novo_ct

        status = "✅ MATCH" if payload else "➖ SEM DADOS"
        via_tag = f"[{via}]"
        print(f"  {status} [{i:03d}] {via_tag:6s} {aluno_bd['nome'][:40]}")
        if novo_ps:
            preview = novo_ps[:80].replace("\n", " ↵ ")
            print(f"           problemas_saude → {preview}…")
        if novo_ct:
            print(f"           contato_emergencia → {novo_ct[:70]}")

        if payload and not DRY_RUN:
            ok = supa_patch("alunos", aluno_bd["id"], payload)
            if ok:
                cnt_atualizados += 1
        elif payload:
            cnt_atualizados += 1  # conta como "seria atualizado" no dry-run

    # Relatório final
    print()
    print("=" * 70)
    print("  RELATÓRIO FINAL")
    print("=" * 70)
    print(f"  Match por CPF  : {cnt_match_cpf}")
    print(f"  Match por Nome : {cnt_match_nome}")
    print(f"  Sem Match      : {cnt_sem_match}")
    print(f"  {'Atualizados' if not DRY_RUN else 'Seriam atualizados'}: {cnt_atualizados}")
    if sem_match_lista:
        print()
        print("  Alunos sem match (verificar manualmente):")
        for nm in sem_match_lista:
            print(f"    • {nm}")
    print()
    if DRY_RUN:
        print("  ℹ️  Nenhuma alteração foi feita. Execute com --executar para aplicar.")
    else:
        print("  ✅ Migração concluída. Verifique o backup salvo antes de qualquer rollback.")
    print()


if __name__ == "__main__":
    main()
