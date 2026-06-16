# ==============================================================================
# 📄 ARQUIVO: database.py
# 🎯 FUNÇÃO: Motor Central de Dados. Preserva 100% da Lógica Original + Cadastro Full.
# 📅 VERSÃO: 7.3 (ULTRA-PRIME - Código Integral c/ Login Blindado Anti-Crash)
# ==============================================================================

import json
import re
import pandas as pd
import streamlit as st
import datetime
import time
from supabase import create_client, Client
import uuid
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🔐 DEFINIÇÃO DO SUPERUSUÁRIO (Mestre do Sistema)
ADMIN_MASTER = "marcosbarbosa.am@gmail.com"


@st.cache_resource(show_spinner=False)
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase: Client = init_connection()


def _resolver_turma_id(turma_input: str):
    """Dado um nome de turma (text) ou UUID, retorna o UUID da turma."""
    if not turma_input:
        return None
    try:
        import uuid as _uuid_mod

        _uuid_mod.UUID(str(turma_input))
        return str(turma_input)
    except (ValueError, AttributeError):
        pass
    try:
        res = (
            supabase.from_("turmas")
            .select("id")
            .eq("nome", str(turma_input).strip())
            .execute()
        )
        return res.data[0]["id"] if res.data else None
    except Exception:
        return None


# ==============================================================================
# 🤖 INTEGRAÇÃO IA (GEMINI) E BLINDAGEM DE DADOS
# ==============================================================================
try:
    import google.generativeai as genai

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ia_model = genai.GenerativeModel("gemini-1.5-flash")
    IA_ATIVA = True
except Exception as e:
    IA_ATIVA = False
    print(f"⚠️ IA Desativada: {e}")


def revisar_texto_ia(texto):
    if not IA_ATIVA or not texto or len(texto.strip()) < 5:
        return None
    prompt = f"Corrija a gramática, ortografia e acentuação do texto. Mantenha o sentido original.\nTexto: '{texto}'\nRetorne APENAS o texto corrigido."
    try:
        response = ia_model.generate_content(prompt)
        sugestao = response.text.strip()
        return sugestao if sugestao.lower() != texto.lower() else None
    except:
        return None


def blindar_float(valor):
    try:
        if valor is None or pd.isna(valor):
            return 0.0
        val = float(valor)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0


def _normalizar_altura(valor):
    """Altura em metros (coluna numeric(4,2), máx 99.99).

    Valores claramente em centímetros (> 3, ex.: 170) são convertidos para
    metros para evitar 'numeric field overflow' na migração do aluno.
    """
    alt = blindar_float(valor)
    if alt < 0:                # valor inválido/negativo
        alt = 0.0
    if alt > 3:                # digitado em cm (ex.: 170 -> 1.70)
        alt = alt / 100.0
    if alt > 99.99:            # teto da coluna numeric(4,2)
        alt = 99.99
    return round(alt, 2)


def _normalizar_peso(valor):
    """Peso arredondado a 2 casas (evita excesso de precisão)."""
    p = blindar_float(valor)
    if p < 0:
        p = 0.0
    return round(p, 2)


# ==============================================================================
# 🔐 AUTENTICAÇÃO, CRM E COMPATIBILIDADE MAIN.PY
# ==============================================================================
def autenticar_usuario(email, senha):
    """Função de Login — usa somente a tabela 'usuarios'"""
    email_limpo = str(email).strip().lower()
    senha_limpa = str(senha).strip()
    try:
        res = (
            supabase.table("usuarios")
            .select("*")
            .eq("email", email_limpo)
            .eq("senha", senha_limpa)
            .execute()
        )
        if res.data:
            return True, res.data[0]
        return False, "E-mail ou senha incorretos."
    except Exception as e:
        return False, f"Erro no servidor: {str(e)}"


def get_template_seguro_db(chave, nome_aluno=""):
    """Puxador de mensagens/CRM solicitado pelo main.py"""
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("valor")
            .eq("chave", chave)
            .execute()
        )
        if res.data:
            texto = res.data[0]["valor"]
            if nome_aluno:
                primeiro_nome = str(nome_aluno).split()[0].title()
                texto = texto.replace("{nome}", primeiro_nome)
            return texto
        return "Mensagem padrão. Configure no painel."
    except Exception:
        return "Mensagem padrão. (Erro de DB)"


def cadastrar_usuario_sistema(nome, email, senha):
    """Função de registo solicitada pelo main.py — usa tabela 'usuarios'"""
    try:
        res = (
            supabase.table("usuarios")
            .select("id")
            .eq("email", email.strip().lower())
            .execute()
        )
        if res.data:
            return False, "E-mail já está registado."
        novo_usuario = {
            "nome": nome.strip(),
            "email": email.strip().lower(),
            "senha": senha,
            "perfil": "Admin",
        }
        supabase.table("usuarios").insert(novo_usuario).execute()
        return True, "✅ Conta criada com sucesso!"
    except Exception as e:
        return False, str(e)


def recuperar_senha_usuario(email):
    """Função de recuperação de senha no main.py"""
    return False, "Função de recuperação em manutenção."


@st.cache_data(ttl=180, show_spinner=False)
def get_agendamentos_pendentes(limite=8):
    """Retorna os agendamentos pendentes para a dashboard do main.py"""
    try:
        res = (
            supabase.from_("agendamentos")
            .select("*, alunos(*)")
            .eq("status", "Pendente")
            .order("data_agendamento", desc=False)
            .limit(limite)
            .execute()
        )
        return res.data if res.data else []
    except Exception:
        try:
            res = (
                supabase.from_("agendamentos")
                .select("*")
                .eq("status", "Pendente")
                .order("data_agendamento", desc=False)
                .limit(limite)
                .execute()
            )
            return res.data if res.data else []
        except Exception:
            return []


# ==============================================================================
# 🏛️ GESTÃO DE TURMAS
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_todas_turmas(ativas_apenas=False):
    try:
        query = supabase.from_("turmas").select("*").order("nome")
        if ativas_apenas:
            query = query.eq("status", "Ativa")
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_ocupacao_turmas(limite_padrao=40):
    try:
        res = (
            supabase.from_("alunos")
            .select("turma_id")
            .neq("status", "Inativo")
            .execute()
        )
        contagem_id = {}
        for row in res.data or []:
            tid = row.get("turma_id")
            if tid:
                contagem_id[tid] = contagem_id.get(tid, 0) + 1

        res_t = (
            supabase.from_("turmas").select("id, nome").eq("status", "Ativa").execute()
        )
        ocupacao = {}
        for t in res_t.data or []:
            qtd = contagem_id.get(t["id"], 0)
            vagas = limite_padrao - qtd
            status_cor = (
                "🔴 LOTADA"
                if vagas <= 0
                else ("🟡 ALERTA" if vagas <= 5 else "🟢 LIVRE")
            )
            ocupacao[t["nome"]] = {
                "qtd": qtd,
                "limite": limite_padrao,
                "vagas": vagas,
                "status": status_cor,
            }
        return ocupacao
    except Exception:
        return {}


def adicionar_turma(nome, horario, dias_semana):
    try:
        check = (
            supabase.from_("turmas").select("id").ilike("nome", nome.strip()).execute()
        )
        if check.data:
            return False, "Turma já existe."
        supabase.from_("turmas").insert(
            {
                "nome": nome.strip(),
                "horario": horario.strip(),
                "dias_semana": dias_semana.strip(),
                "status": "Ativa",
            }
        ).execute()
        return True, "Turma criada!"
    except Exception as e:
        return False, str(e)


def atualizar_turma(turma_id, nome, horario, dias_semana, status):
    try:
        res_a = (
            supabase.from_("turmas").select("nome").eq("id", str(turma_id)).execute()
        )
        nome_antigo = res_a.data[0]["nome"] if res_a.data else None
        supabase.from_("turmas").update(
            {
                "nome": nome.strip(),
                "horario": horario.strip(),
                "dias_semana": dias_semana.strip(),
                "status": status,
            }
        ).eq("id", str(turma_id)).execute()
        if nome_antigo and nome_antigo != nome.strip():
            supabase.from_("alunos").update({"turma": nome.strip()}).eq(
                "turma", nome_antigo
            ).execute()
            supabase.from_("diario_aulas").update({"turma": nome.strip()}).eq(
                "turma", nome_antigo
            ).execute()
        return True, "Atualizada."
    except Exception as e:
        return False, str(e)


def excluir_turma(turma_id):
    try:
        res_a = (
            supabase.from_("alunos")
            .select("id")
            .eq("turma_id", str(turma_id))
            .execute()
        )
        if res_a.data and len(res_a.data) > 0:
            return False, f"Existem {len(res_a.data)} alunos na turma."
        supabase.from_("turmas").delete().eq("id", str(turma_id)).execute()
        return True, "Excluída."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# 🚀 PIPELINE DE INSCRIÇÕES (CADASTRO FULL 28 CAMPOS)
# ==============================================================================
@st.cache_data(ttl=180, show_spinner=False)
def get_pre_cadastros_pendentes():
    try:
        res = (
            supabase.from_("pre_cadastros")
            .select("*")
            .in_("status", ["Pendente", "Lista de Espera", "Duplicata"])
            .execute()
        )
        return res.data
    except Exception:
        return []


def _so_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def verificar_aluno_existente(nome="", data_nascimento=None, cpf=None):
    """Retorna o primeiro aluno já cadastrado que parece ser a MESMA pessoa
    (mesmo CPF, ou mesmo nome + data de nascimento, ou mesmo nome exato quando
    não há nascimento/CPF para comparar). Retorna None se não houver.

    Usado para impedir cadastros duplicados na aprovação e na inclusão manual.
    """
    try:
        cpf_n = _so_digitos(cpf)
        # 1. CPF é identificador forte: verifica GLOBALMENTE, independente do nome
        #    (pega duplicado mesmo com nome digitado diferente).
        if cpf_n:
            res_cpf = (
                supabase.from_("alunos")
                .select("id, nome, turma, status, data_nascimento, cpf")
                .eq("cpf", cpf_n)
                .execute()
            )
            if res_cpf.data:
                return res_cpf.data[0]

        # 2. Sem CPF (ou CPF não bateu): compara por nome + data de nascimento.
        nome_n = str(nome or "").upper().strip()
        if not nome_n:
            return None
        res = (
            supabase.from_("alunos")
            .select("id, nome, turma, status, data_nascimento, cpf")
            .ilike("nome", nome_n)
            .execute()
        )
        candidatos = res.data or []
        nasc_n = str(data_nascimento) if data_nascimento else ""
        for c in candidatos:
            if nasc_n and c.get("data_nascimento") and str(c.get("data_nascimento")) == nasc_n:
                return c
        # Sem CPF nem nascimento para desempatar: nome exato já basta como alerta
        if not cpf_n and not nasc_n and candidatos:
            return candidatos[0]
        return None
    except Exception:
        return None


def aprovar_inscricao_aluno(pre_cadastro_id, turma_selecionada, forcar=False):
    """Aprova inscrição e insere na tabela alunos.
    forcar=True: ignora verificação de duplicata (use quando o operador
    confirmou que é uma pessoa diferente ou decidiu matricular mesmo assim).
    """
    try:
        res_pre = (
            supabase.from_("pre_cadastros")
            .select("*")
            .eq("id", pre_cadastro_id)
            .execute()
        )
        if not res_pre.data:
            return False, "Inscrição não encontrada."

        pre = res_pre.data[0]
        turma_id_val = _resolver_turma_id(turma_selecionada)

        novo_aluno = {
            "nome": pre.get("nome", "").upper().strip(),
            "turma": turma_selecionada,
            "turma_id": turma_id_val,
            "data_nascimento": pre.get("data_nascimento"),
            "whatsapp": pre.get("celular", "") or pre.get("whatsapp", ""),
            "email": pre.get("email", ""),
            "cpf": pre.get("cpf", ""),
            "rg": pre.get("rg", ""),
            "naturalidade": pre.get("naturalidade", ""),
            "sexo": pre.get("sexo", ""),
            "estado_civil": pre.get("estado_civil", ""),
            "nome_conjuge": pre.get("nome_conjuge", ""),
            "grau_instrucao": pre.get("grau_instrucao", ""),
            "peso": _normalizar_peso(pre.get("peso")),
            "altura": _normalizar_altura(pre.get("altura")),
            "endereco": pre.get("endereco", ""),
            "complemento": pre.get("complemento", ""),
            "bairro": pre.get("bairro", ""),
            "cep": pre.get("cep", ""),
            "problemas_saude": pre.get("problemas_saude", ""),
            "medicamentos": pre.get("medicamentos", ""),
            "alergia_medicamento": pre.get("alergia_medicamento", ""),
            "restricoes_fisicas": pre.get("restricoes_fisicas", ""),
            "pratica_outras_atividades": pre.get("pratica_outras_atividades", ""),
            "incomodo_atividades": pre.get("incomodo_atividades", ""),
            "contato_emergencia": pre.get("contato_emergencia", ""),
            "residentes_moradia": pre.get("residentes_moradia", ""),
            "aposentado": pre.get("aposentado", ""),
            "fonte_renda": pre.get("fonte_renda", ""),
            "renda_familiar": pre.get("renda_familiar", ""),
            "interesse_voluntariado": pre.get("interesse_voluntariado", ""),
            "areas_voluntariado": pre.get("areas_voluntariado", ""),
            "url_foto": pre.get("url_foto"),
            "url_rg": pre.get("url_rg"),
            "url_receituario": pre.get("url_receituario"),
            "url_atestado_medico": pre.get("url_atestado_medico"),
            "status": "Ativo",
        }

        # Proteção anti-duplicidade: se já existe aluno com este CPF (ou nome +
        # nascimento), NÃO cria outro. Arquiva a inscrição e avisa o operador.
        if not forcar:
            existente = verificar_aluno_existente(
                novo_aluno["nome"], novo_aluno.get("data_nascimento"), novo_aluno.get("cpf")
            )
            if existente:
                # NÃO marca como "Aprovado" — usa "Duplicata" para que a inscrição
                # permaneça VISÍVEL na triagem e o operador possa resolver.
                # Bug anterior: marcava "Aprovado" e a ficha desaparecia sem criar aluno.
                supabase.from_("pre_cadastros").update({"status": "Duplicata"}).eq(
                    "id", pre_cadastro_id
                ).execute()
                _inv_alunos()
                return False, (
                    f"⚠️ '{novo_aluno['nome']}' já existe no sistema "
                    f"(turma {existente.get('turma') or '—'}, status {existente.get('status') or '—'}). "
                    "Inscrição marcada como **Duplicata** — revise na triagem e force a matrícula se for pessoa diferente."
                )

        supabase.from_("alunos").insert(_com_fonetica(novo_aluno)).execute()
        supabase.from_("pre_cadastros").update({"status": "Aprovado"}).eq(
            "id", pre_cadastro_id
        ).execute()
        _inv_alunos()
        return True, f"Aluno {novo_aluno['nome']} matriculado na {turma_selecionada}!"
    except Exception as e:
        return False, f"Erro ao migrar aluno: {str(e)}"


def rejeitar_inscricao_aluno(pre_cadastro_id):
    try:
        supabase.from_("pre_cadastros").update({"status": "Rejeitado"}).eq(
            "id", pre_cadastro_id
        ).execute()
        return True, "Arquivada."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# 👨‍🎓 GESTÃO DE ALUNOS E DIÁRIOS
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def _carregar_base_alunos(incluir_inativos=False):
    """Download paginado da base de alunos (sem filtro de termo) — supera o
    limite de 1000 linhas do PostgREST.

    Cacheado APENAS por `incluir_inativos`. Assim, buscas por termos diferentes
    reutilizam o mesmo download em vez de re-baixar a base inteira a cada busca
    (o filtro fonético acontece em Python sobre este resultado já em memória).
    """
    todos = []
    inicio = 0
    while True:
        query = supabase.from_("alunos").select("*")
        if not incluir_inativos:
            query = query.neq("status", "Inativo")
        res = query.order("nome").range(inicio, inicio + 999).execute()
        if res.data:
            todos.extend(res.data)
        if not res.data or len(res.data) < 1000:
            break
        inicio += 1000
    return pd.DataFrame(todos)


@st.cache_data(ttl=600, show_spinner=False)
def _coluna_fonetica_disponivel() -> bool:
    """Detecta se a coluna persistida `nome_fonetica` já existe em `alunos`.

    Enquanto ela não existir (criação exige DDL no Supabase), TODO o caminho cai
    no comportamento atual (download da base + filtro em Python), sem regressão.
    Assim que a coluna for criada, o filtro server-side e a sincronização em
    insert/update passam a funcionar automaticamente."""
    try:
        supabase.from_("alunos").select("nome_fonetica").limit(1).execute()
        return True
    except Exception:
        return False


@st.cache_data(ttl=600, show_spinner=False)
def _coluna_fonetica_pronta(incluir_inativos=False) -> bool:
    """True apenas quando a coluna existe E está 100% preenchida (nenhum aluno no
    escopo com `nome_fonetica` nulo). Garante que o filtro server-side nunca
    perca alunos antigos ainda não retro-preenchidos (`backfill_nome_fonetica`)."""
    try:
        q = supabase.from_("alunos").select("id").is_("nome_fonetica", "null")
        if not incluir_inativos:
            q = q.neq("status", "Inativo")
        res = q.limit(1).execute()
        return not res.data
    except Exception:
        return False


def _escape_like(s: str) -> str:
    """Escapa os curingas de LIKE/ILIKE (`\\`, `%`, `_`) para que o filtro
    server-side faça correspondência literal de substring, idêntica ao
    `str.contains(..., regex=False)` usado no filtro em Python."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _com_fonetica(dados: dict) -> dict:
    """Acrescenta `nome_fonetica` ao payload quando há 'nome' e a coluna existe.

    No-op seguro quando a coluna ainda não foi criada — evita o erro
    'column does not exist' que quebraria qualquer insert/update de aluno."""
    if dados and dados.get("nome") and _coluna_fonetica_disponivel():
        from utils.texto import normalizar_fonetica
        return {**dados, "nome_fonetica": normalizar_fonetica(dados["nome"])}
    return dados


def _buscar_alunos_serverside(alvo, incluir_inativos):
    """Filtra alunos no banco por `nome_fonetica` (ILIKE substring), paginando
    para superar o limite de 1000 linhas do PostgREST. Só baixa os alunos que
    casam com o termo — escala sem trazer a base inteira."""
    padrao = f"%{_escape_like(alvo)}%"
    todos = []
    inicio = 0
    while True:
        query = supabase.from_("alunos").select("*").ilike("nome_fonetica", padrao)
        if not incluir_inativos:
            query = query.neq("status", "Inativo")
        res = query.order("nome").range(inicio, inicio + 999).execute()
        if res.data:
            todos.extend(res.data)
        if not res.data or len(res.data) < 1000:
            break
        inicio += 1000
    return pd.DataFrame(todos)


@st.cache_data(ttl=300, show_spinner=False)
def buscar_alunos_geral(termo="", incluir_inativos=False):
    """Busca alunos por termo (filtro FONÉTICO tolerante a acentos/grafia).

    Quando a coluna persistida `nome_fonetica` existe e está preenchida, filtra
    SERVER-SIDE (só baixa os alunos que casam — escala com a base). Caso
    contrário, mantém o caminho atual: base baixada uma única vez (cache de
    `_carregar_base_alunos`) e filtrada em Python. Resultados são idênticos nos
    dois caminhos."""
    try:
        from utils.texto import normalizar_fonetica
        alvo = normalizar_fonetica(termo) if termo else ""

        # Caminho escalável: filtro no banco pela coluna fonética persistida.
        if alvo and _coluna_fonetica_pronta(incluir_inativos):
            return _buscar_alunos_serverside(alvo, incluir_inativos)

        # Fallback (coluna ausente/incompleta): download único + filtro em Python.
        df = _carregar_base_alunos(incluir_inativos)
        if alvo and not df.empty and "nome" in df.columns:
            df = df[
                df["nome"].fillna("").apply(normalizar_fonetica).str.contains(alvo, na=False, regex=False)
            ]
        return df
    except Exception:
        return pd.DataFrame()


def backfill_nome_fonetica():
    """Retro-preenche `alunos.nome_fonetica` para os alunos já existentes.

    Requisito: a coluna `nome_fonetica` já deve existir no Supabase (criação por
    DDL). Após rodar, `_coluna_fonetica_pronta` passa a True e a busca usa o
    filtro server-side. Idempotente: só atualiza linhas com valor ausente/divergente.
    Retorna (bool, msg)."""
    if not _coluna_fonetica_disponivel():
        return False, (
            "Coluna 'nome_fonetica' não existe. Crie-a no Supabase "
            "(ALTER TABLE alunos ADD COLUMN nome_fonetica text;) antes do backfill."
        )
    from utils.texto import normalizar_fonetica
    try:
        df = _carregar_base_alunos(incluir_inativos=True)
        if df.empty:
            return True, "Nenhum aluno para preencher."
        atualizados = 0
        for _, row in df.iterrows():
            nome = row.get("nome")
            alvo = normalizar_fonetica(nome) if nome else ""
            atual = row.get("nome_fonetica") if "nome_fonetica" in df.columns else None
            if (atual or "") == alvo:
                continue
            supabase.from_("alunos").update({"nome_fonetica": alvo}).eq(
                "id", str(row["id"])
            ).execute()
            atualizados += 1
        _inv_alunos()
        return True, f"Backfill concluído: {atualizados} aluno(s) atualizado(s)."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_aluno_por_id(aluno_id):
    try:
        res = (
            supabase.from_("alunos")
            .select("*")
            .eq("id", str(aluno_id))
            .single()
            .execute()
        )
        return res.data if res.data else None
    except Exception:
        return None


# ── Invalidação cirúrgica de cache ────────────────────────────────────────────
# Cada helper limpa APENAS as funções afetadas, preservando todos os demais.
# Nunca use st.cache_data.clear() — isso apaga tudo e causa "Running" global.

def _inv_alunos():
    """Caches de lista/perfil de alunos, prontuários e BI de risco."""
    for fn in (
        _carregar_base_alunos, buscar_alunos_geral, _coluna_fonetica_pronta,
        buscar_aluno_por_id, get_alunos_por_turma,
        get_avaliacoes_aluno, get_atestados_temporarios,
        get_estatisticas_frequencia_aluno, get_historico_aulas_aluno,
        bi_resumo_studio, bi_distribuicao_risco, bi_alunos_risco_abandono,
        bi_evolucao_cadastros, bi_dados_individuais, get_pre_cadastros_pendentes,
    ):
        try:
            fn.clear()
        except Exception:
            pass


def _inv_agendamentos():
    """Cache de agendamentos pendentes."""
    try:
        get_agendamentos_pendentes.clear()
    except Exception:
        pass


def _inv_frequencia():
    """Caches de frequência, última presença e BI — chamar após alternar_presenca ou excluir aula."""
    for fn in (
        get_ultima_presenca_batch, load_frequencia_ultima_presenca,
        get_presencas_dia, bi_presencas_periodo, bi_frequencia_turmas,
        bi_resumo_studio, get_diarios_periodo,
    ):
        try:
            fn.clear()
        except Exception:
            pass


def _inv_dores():
    """Caches de anamnese de dores (histórico individual e agregado BI)."""
    for fn in (buscar_historico_dores, bi_dores_studio):
        try:
            fn.clear()
        except Exception:
            pass


# ── Mutações de aluno ─────────────────────────────────────────────────────────

def atualizar_dados_sociais_aluno(aluno_id, dados_atualizados):
    try:
        dados_limpos = {
            k: v
            for k, v in dados_atualizados.items()
            if v is not None and str(v).strip() not in ("", "nan", "None")
        }
        supabase.from_("alunos").update(_com_fonetica(dados_limpos)).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Perfil atualizado!"
    except Exception as e:
        return False, str(e)


def alterar_status_aluno(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq(
            "id", str(aluno_id)
        ).execute()
        _inv_alunos()
        return True, "Status alterado."
    except Exception as e:
        return False, str(e)


def excluir_aluno_completo(aluno_id, solicitante_email):
    if solicitante_email != ADMIN_MASTER:
        return False, "Acesso Negado."
    try:
        aid = str(aluno_id)
        supabase.from_("agendamentos").delete().eq("aluno_id", aid).execute()
        supabase.from_("prontuario_avaliacoes").delete().eq("aluno_id", aid).execute()
        supabase.from_("frequencia").delete().eq("aluno_id", aid).execute()
        supabase.from_("atestados_temporarios").delete().eq("aluno_id", aid).execute()
        supabase.from_("anamnese_dores").delete().eq("aluno_id", aid).execute()
        supabase.from_("alunos").delete().eq("id", aid).execute()
        _inv_alunos()
        return True, "Excluído."
    except Exception as e:
        return False, str(e)


def excluir_aluno(aluno_id):
    """Remove o aluno da tabela alunos (sem cascade). Retorna (bool, msg)."""
    try:
        supabase.from_("alunos").delete().eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Aluno removido."
    except Exception as e:
        return False, str(e)


def cadastrar_novo_aluno(nome, turma, **kwargs):
    """Insere um novo aluno com status Ativo. Retorna True/False."""
    try:
        payload = {"nome": str(nome).strip(), "turma": str(turma).strip(),
                   "status": "Ativo"}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        supabase.from_("alunos").insert(_com_fonetica(payload)).execute()
        _inv_alunos()
        return True
    except Exception:
        return False


def atualizar_perfil_aluno(aluno_id, nome, data_nascimento, peso, altura,
                           whatsapp, obs="", email_usuario=""):
    """Atualiza campos do perfil do aluno. Retorna (bool, msg)."""
    try:
        dados = {
            "nome": str(nome).strip(),
            "data_nascimento": str(data_nascimento) if data_nascimento else None,
            "peso": float(peso) if peso else None,
            "altura": float(altura) if altura else None,
            "whatsapp": str(whatsapp).strip() if whatsapp else None,
        }
        if obs:
            dados["observacoes"] = str(obs).strip()
        dados_limpos = {k: v for k, v in dados.items() if v is not None}
        supabase.from_("alunos").update(_com_fonetica(dados_limpos)).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Perfil atualizado!"
    except Exception as e:
        return False, str(e)


def atualizar_perfil_aluno_dict(aluno_id, payload: dict):
    """Atualiza aluno com um dicionário arbitrário de campos. Retorna (bool, msg)."""
    try:
        dados_limpos = {k: v for k, v in payload.items()
                        if v is not None and str(v).strip() not in ("", "nan", "None")}
        if not dados_limpos:
            return False, "Nenhum campo para atualizar."
        supabase.from_("alunos").update(_com_fonetica(dados_limpos)).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Dados atualizados."
    except Exception as e:
        return False, str(e)


def atualizar_aluno_completo(aluno_id, dados: dict):
    """Atualiza o aluno com um dict completo de campos. Retorna (bool, msg)."""
    try:
        dados_limpos = {k: v for k, v in dados.items()
                        if v is not None and str(v).strip() not in ("", "nan", "None")}
        supabase.from_("alunos").update(_com_fonetica(dados_limpos)).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Aluno atualizado."
    except Exception as e:
        return False, str(e)


def atualizar_termo_imagem(aluno_id: str, novo_valor: bool, operador: str = "", aluno_nome: str = "") -> tuple:
    """Atualiza termo_imagem do aluno, registra log e invalida cache. Retorna (bool, msg)."""
    import json, datetime as _dt
    try:
        supabase.from_("alunos").update({"termo_imagem": novo_valor}).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        ts = _dt.datetime.now().isoformat(timespec="seconds")
        chave = f"lgpd_log_{ts}_{aluno_id}"
        valor = json.dumps({
            "aluno_id": aluno_id,
            "aluno_nome": aluno_nome,
            "status": "Autorizado" if novo_valor else "Revogado",
            "operador": operador or "—",
            "timestamp": ts,
        }, ensure_ascii=False)
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        get_logs_lgpd.clear()
        return True, "Autorização atualizada."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=60, show_spinner=False)
def get_logs_lgpd(limit: int = 300) -> list:
    """Retorna logs de alteração LGPD (mais recente primeiro)."""
    import json
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("chave,valor")
            .like("chave", "lgpd_log_%")
            .order("chave", desc=True)
            .limit(limit)
            .execute()
        )
        logs = []
        for r in (res.data or []):
            try:
                logs.append(json.loads(r["valor"]))
            except Exception:
                pass
        return logs
    except Exception:
        return []


def registrar_log_matricula_doc(aluno_id, aluno_nome, docs_faltantes, operador: str = "", turma: str = "", turma_lotada: bool = False) -> bool:
    """Registra log de matrícula forçada (documentos faltantes e/ou turma lotada)."""
    import json, datetime as _dt
    try:
        ts = _dt.datetime.now().isoformat(timespec="seconds")
        chave = f"matricula_doc_log_{ts}_{aluno_id}"
        valor = json.dumps({
            "aluno_id": str(aluno_id),
            "aluno_nome": aluno_nome,
            "docs_faltantes": list(docs_faltantes),
            "turma": turma or "—",
            "turma_lotada": bool(turma_lotada),
            "operador": operador or "—",
            "timestamp": ts,
        }, ensure_ascii=False)
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        get_logs_matricula_docs.clear()
        return True
    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def get_logs_matricula_docs(limit: int = 300) -> list:
    """Retorna logs de matrículas com documentos faltantes (mais recente primeiro)."""
    import json
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("chave,valor")
            .like("chave", "matricula_doc_log_%")
            .order("chave", desc=True)
            .limit(limit)
            .execute()
        )
        logs = []
        for r in (res.data or []):
            try:
                logs.append(json.loads(r["valor"]))
            except Exception:
                pass
        return logs
    except Exception:
        return []


def atualizar_data_nascimento(aluno_id, data_nascimento):
    """Atualiza somente a data de nascimento do aluno. Retorna (bool, msg)."""
    try:
        supabase.from_("alunos").update(
            {"data_nascimento": str(data_nascimento)}
        ).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True, "Data de nascimento atualizada."
    except Exception as e:
        return False, str(e)


def criar_agendamento(aluno_id, data, hora, tipo="Avaliação"):
    """Cria um novo agendamento pendente. Retorna (bool, msg)."""
    try:
        supabase.from_("agendamentos").insert({
            "aluno_id":         str(aluno_id),
            "data_agendamento": str(data),
            "horario":          str(hora),
            "motivo":           str(tipo),
            "status":           "Pendente",
        }).execute()
        _inv_agendamentos()
        return True, "Agendamento criado."
    except Exception as e:
        return False, str(e)


def concluir_ou_cancelar_agendamento(agendamento_id, status):
    """Atualiza o status de um agendamento (ex: 'Concluído', 'Cancelado')."""
    try:
        supabase.from_("agendamentos").update(
            {"status": str(status)}
        ).eq("id", str(agendamento_id)).execute()
        _inv_agendamentos()
        return True, "Agendamento atualizado."
    except Exception as e:
        return False, str(e)


def atualizar_agendamento(agendamento_id, nova_data, novo_horario):
    """Atualiza data e horário de um agendamento pendente. Retorna (bool, msg)."""
    try:
        supabase.from_("agendamentos").update({
            "data_agendamento": str(nova_data),
            "horario":          str(novo_horario),
        }).eq("id", str(agendamento_id)).execute()
        _inv_agendamentos()
        return True, "Agendamento atualizado."
    except Exception as e:
        return False, str(e)


def obter_dependencias_lote(ids: list) -> dict:
    """
    Retorna {aluno_id: {frequencias: N, avaliacoes: N, atestados: N}}
    para uma lista de aluno_ids — apenas 3 queries independente do tamanho.
    """
    resultado = {str(i): {"frequencias": 0, "avaliacoes": 0, "atestados": 0}
                 for i in ids}
    if not ids:
        return resultado
    ids_str = [str(i) for i in ids]
    try:
        r = supabase.from_("frequencia").select("aluno_id").in_("aluno_id", ids_str).execute()
        for row in (r.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["frequencias"] += 1
    except Exception:
        pass
    try:
        r = supabase.from_("prontuario_avaliacoes").select("aluno_id").in_("aluno_id", ids_str).execute()
        for row in (r.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["avaliacoes"] += 1
    except Exception:
        pass
    try:
        r = supabase.from_("atestados_temporarios").select("aluno_id").in_("aluno_id", ids_str).execute()
        for row in (r.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["atestados"] += 1
    except Exception:
        pass
    return resultado


@st.cache_data(ttl=120, show_spinner=False)
def get_alunos_por_turma(turma_nome):
    try:
        res = (
            supabase.from_("alunos")
            .select("*")
            .eq("turma", turma_nome)
            .neq("status", "Inativo")
            .execute()
        )
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def get_alunos_sem_autorizacao_imagem() -> pd.DataFrame:
    """Retorna alunos ativos que NÃO autorizaram (ou não responderam) o uso de imagem."""
    try:
        res = (
            supabase.from_("alunos")
            .select("id,nome,url_foto,data_nascimento,turma,status,termo_imagem")
            .neq("status", "Inativo")
            .or_("termo_imagem.is.null,termo_imagem.eq.false")
            .order("nome")
            .execute()
        )
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_alunos_com_atestado_bloqueado() -> pd.DataFrame:
    """Retorna alunos ativos com atestado_bloqueado=true."""
    try:
        res = (
            supabase.from_("alunos")
            .select("id,nome,url_foto,data_nascimento,turma,status,atestado_bloqueado,obs_atestado_bloqueio")
            .neq("status", "Inativo")
            .eq("atestado_bloqueado", True)
            .order("nome")
            .execute()
        )
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def atualizar_atestado_bloqueio(aluno_id: str, bloqueado: bool, obs: str = "",
                                 operador: str = "", aluno_nome: str = "") -> tuple:
    """Ativa ou desativa o bloqueio de atestado médico. Retorna (bool, msg)."""
    import json, datetime as _dt
    try:
        supabase.from_("alunos").update({
            "atestado_bloqueado": bloqueado,
            "obs_atestado_bloqueio": obs.strip() if obs else None,
        }).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        ts = _dt.datetime.now().isoformat(timespec="seconds")
        chave = f"atestado_log_{ts}_{aluno_id}"
        valor = json.dumps({
            "aluno_id": aluno_id,
            "aluno_nome": aluno_nome,
            "status": "Bloqueado" if bloqueado else "Liberado",
            "obs": obs or "—",
            "operador": operador or "—",
            "timestamp": ts,
        }, ensure_ascii=False)
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        get_alunos_com_atestado_bloqueado.clear()
        return True, "Situação de atestado atualizada."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# 🧪 AVALIAÇÃO PENDENTE — funções para identificar e bloquear alunos sem avaliação
# ==============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_ids_alunos_avaliados() -> set:
    """Retorna set de aluno_ids que possuem ao menos 1 registro em prontuario_avaliacoes."""
    try:
        inicio = 0
        ids: set = set()
        while True:
            res = (
                supabase.from_("prontuario_avaliacoes")
                .select("aluno_id")
                .range(inicio, inicio + 999)
                .execute()
            )
            for row in (res.data or []):
                if row.get("aluno_id"):
                    ids.add(str(row["aluno_id"]))
            if len(res.data or []) < 1000:
                break
            inicio += 1000
        return ids
    except Exception:
        return set()


@st.cache_data(ttl=60, show_spinner=False)
def get_alunos_sem_avaliacao() -> pd.DataFrame:
    """Retorna alunos ativos que nunca tiveram uma avaliação em prontuario_avaliacoes."""
    try:
        ids_avaliados = get_ids_alunos_avaliados()
        res = (
            supabase.from_("alunos")
            .select("id,nome,url_foto,data_nascimento,turma,status,whatsapp,avaliacao_pendente,obs_avaliacao_pendente")
            .neq("status", "Inativo")
            .order("nome")
            .execute()
        )
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        df["id"] = df["id"].astype(str)
        return df[~df["id"].isin(ids_avaliados)].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_alunos_com_avaliacao_pendente() -> pd.DataFrame:
    """Retorna alunos ativos com avaliacao_pendente=true (bloqueados até reavaliação)."""
    try:
        res = (
            supabase.from_("alunos")
            .select("id,nome,url_foto,data_nascimento,turma,status,avaliacao_pendente,obs_avaliacao_pendente")
            .neq("status", "Inativo")
            .eq("avaliacao_pendente", True)
            .order("nome")
            .execute()
        )
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def atualizar_avaliacao_pendente(aluno_id: str, pendente: bool, obs: str = "",
                                  operador: str = "", aluno_nome: str = "") -> tuple:
    """Ativa ou desativa o bloqueio por avaliação/reavaliação pendente. Retorna (bool, msg)."""
    import json, datetime as _dt
    try:
        supabase.from_("alunos").update({
            "avaliacao_pendente": pendente,
            "obs_avaliacao_pendente": obs.strip() if obs else None,
        }).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        ts = _dt.datetime.now().isoformat(timespec="seconds")
        chave = f"aval_pend_log_{ts}_{aluno_id}"
        valor = json.dumps({
            "aluno_id": aluno_id,
            "aluno_nome": aluno_nome,
            "status": "Bloqueado" if pendente else "Liberado",
            "obs": obs or "—",
            "operador": operador or "—",
            "timestamp": ts,
        }, ensure_ascii=False)
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        get_alunos_com_avaliacao_pendente.clear()
        get_alunos_sem_avaliacao.clear()
        get_ids_alunos_avaliados.clear()
        return True, "Situação de avaliação atualizada."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=300, show_spinner=False)
def listar_datas_aulas_registradas() -> pd.DataFrame:
    """
    Retorna DataFrame com todas as datas que têm registros em frequencia ou diario_aulas.
    Colunas: data_aula (date), total_presencas (int), turmas_diario (list[str])
    """
    try:
        # limit=50000 evita o corte silencioso de 1000 linhas do PostgREST
        r_freq = (
            supabase.from_("frequencia")
            .select("data_aula, status")
            .limit(50000)
            .execute()
        )
        r_diario = (
            supabase.from_("diario_aulas")
            .select("data_aula, turma")
            .limit(10000)
            .execute()
        )

        df_f = pd.DataFrame(r_freq.data or [])
        df_d = pd.DataFrame(r_diario.data or [])

        # Normaliza ambas as colunas para "YYYY-MM-DD" string pura.
        # CRÍTICO: frequencia.data_aula pode ser date  → "2026-05-21"
        #          diario_aulas.data_aula pode ser timestamp → "2026-05-21T00:00:00+00:00"
        # pd.to_datetime com series mista (naive + tz-aware) converte tz-aware para NaT
        # mesmo com errors='coerce' — por isso usamos str[:10] (sempre YYYY-MM-DD).
        _RE_DATA = r"^\d{4}-\d{2}-\d{2}$"
        if not df_f.empty:
            df_f["data_aula"] = df_f["data_aula"].astype(str).str[:10]
            df_f = df_f[df_f["data_aula"].str.match(_RE_DATA, na=False)]
        if not df_d.empty:
            df_d["data_aula"] = df_d["data_aula"].astype(str).str[:10]
            df_d = df_d[df_d["data_aula"].str.match(_RE_DATA, na=False)]

        datas = set()
        if not df_f.empty:
            datas.update(df_f["data_aula"].dropna().tolist())
        if not df_d.empty:
            datas.update(df_d["data_aula"].dropna().tolist())

        if not datas:
            return pd.DataFrame(columns=["data_aula", "total_presencas", "turmas_diario"])

        # Pré-calcula contagens usando value_counts (muito mais rápido que loop ==)
        contagem_freq = (
            df_f["data_aula"].value_counts() if not df_f.empty
            else pd.Series(dtype=int)
        )

        rows = []
        for d in sorted(datas, reverse=True):
            presencas = int(contagem_freq.get(d, 0))
            turmas = []
            if not df_d.empty:
                turmas = df_d[df_d["data_aula"] == d]["turma"].dropna().tolist()
            rows.append({"data_aula": d, "total_presencas": presencas, "turmas_diario": turmas})

        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["data_aula", "total_presencas", "turmas_diario"])


def excluir_dia_aula_completo(data_str: str, solicitante_email: str):
    """
    Apaga TODOS os registros de frequencia e diario_aulas para a data informada.
    Apenas ADMIN_MASTER pode executar. Retorna (bool, msg, n_freq, n_diario).
    """
    if solicitante_email != ADMIN_MASTER:
        return False, "Acesso negado — apenas o Administrador Mestre pode excluir dias de aula.", 0, 0
    try:
        r_freq = (
            supabase.from_("frequencia")
            .delete()
            .eq("data_aula", data_str)
            .execute()
        )
        r_diario = (
            supabase.from_("diario_aulas")
            .delete()
            .eq("data_aula", data_str)
            .execute()
        )
        n_freq   = len(r_freq.data)   if r_freq.data   else 0
        n_diario = len(r_diario.data) if r_diario.data else 0
        _inv_frequencia()
        listar_datas_aulas_registradas.clear()
        return True, f"Data {data_str} excluída.", n_freq, n_diario
    except Exception as e:
        return False, str(e), 0, 0


def get_diarios_periodo(data_inicio, data_fim, turma=""):
    """Retorna diários com paginação automática — supera o limite de 1000 linhas do PostgREST."""
    try:
        todos = []
        inicio = 0
        while True:
            query = (
                supabase.from_("diario_aulas")
                .select("*")
                .gte("data_aula", str(data_inicio))
                .lte("data_aula", str(data_fim))
            )
            if turma:
                query = query.eq("turma", turma)
            res = query.order("data_aula").range(inicio, inicio + 999).execute()
            if res.data:
                todos.extend(res.data)
            if not res.data or len(res.data) < 1000:
                break
            inicio += 1000
        return pd.DataFrame(todos)
    except Exception:
        return pd.DataFrame()


def get_diario_dia(data_aula, turma):
    """Retorna o registro do diário de aulas para uma data e turma específicas, ou None."""
    try:
        res = (
            supabase.from_("diario_aulas")
            .select("*")
            .eq("data_aula", str(data_aula))
            .eq("turma", str(turma))
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        return None


def get_midias_diario(diario_id):
    try:
        res = (
            supabase.from_("diario_midias")
            .select("*")
            .eq("diario_aula_id", str(diario_id))
            .execute()
        )
        return res.data
    except Exception:
        return []


def atualizar_legenda_midia(midia_id, nova_legenda):
    """Atualiza o campo legenda de um registro em diario_midias."""
    try:
        supabase.from_("diario_midias").update(
            {"legenda": nova_legenda}
        ).eq("id", str(midia_id)).execute()
        return True
    except Exception:
        return False


def excluir_midia_diario(midia_id):
    """Exclui um registro de mídia do diário de aulas."""
    try:
        supabase.from_("diario_midias").delete().eq("id", str(midia_id)).execute()
        return True
    except Exception:
        return False


# ==============================================================================
# ✅ FREQUÊNCIA E RELATÓRIOS (MOTOR ANTI-FURO)
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def load_atestados_vencimento():
    """Retorna DataFrame com colunas [id, data_vencimento_atestado].

    Busca o atestado de aptidao_fisica mais recente (maior data_vencimento)
    por aluno em atestados_temporarios. Usado para exibir semáforo de
    vencimento no grid principal."""
    try:
        res = (
            supabase.from_("atestados_temporarios")
            .select("aluno_id, data_vencimento")
            .eq("tipo_atestado", "aptidao_fisica")
            .not_.is_("data_vencimento", "null")
            .execute()
        )
        if not res.data:
            return pd.DataFrame(columns=["id", "data_vencimento_atestado"])
        df_at = pd.DataFrame(res.data)
        df_at["data_vencimento"] = pd.to_datetime(df_at["data_vencimento"], errors="coerce")
        mais_recente = (
            df_at.groupby("aluno_id")["data_vencimento"].max().reset_index()
        )
        mais_recente.columns = ["id", "data_vencimento_atestado"]
        return mais_recente
    except Exception:
        return pd.DataFrame(columns=["id", "data_vencimento_atestado"])


@st.cache_data(ttl=300, show_spinner=False)
def load_frequencia_ultima_presenca():
    """Retorna DataFrame com colunas [id, ultima_presenca] — máx data_aula PRESENTE por aluno."""
    try:
        res = (
            supabase.from_("frequencia")
            .select("aluno_id, data_aula")
            .eq("status", "PRESENTE")
            .order("data_aula", desc=True)
            .limit(200000)
            .execute()
        )
        if not res.data:
            return pd.DataFrame(columns=["id", "ultima_presenca"])
        df_f = pd.DataFrame(res.data)
        df_f["data_aula"] = pd.to_datetime(df_f["data_aula"], errors="coerce")
        ultima = df_f.groupby("aluno_id")["data_aula"].max().reset_index()
        ultima.columns = ["id", "ultima_presenca"]
        return ultima
    except Exception:
        return pd.DataFrame(columns=["id", "ultima_presenca"])


def alternar_presenca(aluno_id, data_aula, presente, solicitante_email=""):
    status = "PRESENTE" if presente else "FALTA"
    try:
        res = (
            supabase.from_("frequencia")
            .select("id")
            .eq("aluno_id", str(aluno_id))
            .eq("data_aula", str(data_aula))
            .execute()
        )
        if res.data:
            supabase.from_("frequencia").update({"status": status}).eq(
                "id", res.data[0]["id"]
            ).execute()
        else:
            supabase.from_("frequencia").insert(
                {
                    "aluno_id": str(aluno_id),
                    "data_aula": str(data_aula),
                    "status": status,
                }
            ).execute()
        _inv_frequencia()
        return True, "Ok"
    except Exception as e:
        return False, str(e)


def get_presencas_dia(data_aula, lista_ids):
    if not lista_ids:
        return {}
    try:
        res = (
            supabase.from_("frequencia")
            .select("aluno_id, status")
            .eq("data_aula", str(data_aula))
            .in_("aluno_id", lista_ids)
            .execute()
        )
        return {item["aluno_id"]: (item["status"] == "PRESENTE") for item in res.data}
    except Exception:
        return {}


def upload_midia(file_bytes, file_name, mime_type, bucket="diario_midias_imbra", tentativas=3):
    """Envia um arquivo ao Storage do Supabase com novas tentativas em caso de
    falha transitória (rede/timeout). Retorna a URL pública ou None se todas as
    tentativas falharem."""
    ext = (file_name.rsplit(".", 1)[-1] if "." in file_name else "bin").lower()
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            nome_u = f"{uuid.uuid4()}.{ext}"
            supabase.storage.from_(bucket).upload(
                file=file_bytes,
                path=nome_u,
                file_options={"content-type": mime_type or "application/octet-stream"},
            )
            url = supabase.storage.from_(bucket).get_public_url(nome_u)
            if not url or str(url).strip() in ("", "None", "null"):
                ultimo_erro = "URL pública vazia após upload"
                print(f"[upload_midia] AVISO (tentativa {tentativa}/{tentativas}): "
                      f"URL vazia após upload de '{nome_u}' no bucket '{bucket}'")
                continue
            return url
        except Exception as e:
            ultimo_erro = str(e)
            print(f"[upload_midia] tentativa {tentativa}/{tentativas} falhou ao enviar "
                  f"'{file_name}' para bucket '{bucket}': {e}")
    print(f"[upload_midia] ERRO definitivo ao enviar '{file_name}' para "
          f"bucket '{bucket}': {ultimo_erro}")
    return None


def salvar_diario(
    data, turma, obj, exercicios, url_foto_g, midias, foco_clinico="", relatos=""
):
    try:
        turma_id_val = _resolver_turma_id(turma)
        dados = {
            "data_aula": str(data),
            "turma": turma,
            "turma_id": turma_id_val,
            "objetivo_geral": obj,
            "exercicios_executados": exercicios,
            "url_foto_grupo": url_foto_g,
            "foco_clinico_social": foco_clinico,
            "relatos_melhora": relatos,
        }
        busca = (
            supabase.from_("diario_aulas")
            .select("id")
            .eq("data_aula", str(data))
            .eq("turma", turma)
            .execute()
        )
        if busca.data:
            d_id = busca.data[0]["id"]
            supabase.from_("diario_aulas").update(dados).eq("id", d_id).execute()
        else:
            ins = supabase.from_("diario_aulas").insert(dados).execute()
            d_id = ins.data[0]["id"]

        if midias:
            for m in midias:
                supabase.from_("diario_midias").insert(
                    {
                        "diario_aula_id": d_id,
                        "url_midia": m.get("url"),
                        "descricao_objetivo": m.get("descricao"),
                        "tipo": m.get("tipo", "foto"),
                    }
                ).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


def get_relatorio_periodo(data_inicio, data_fim, turma_filtro="Todas"):
    """
    Constrói a matriz cruzando os dias oficiais de aula (Diário) com os alunos.
    Denominador correto: total de aulas registradas no Diário por turma.
    Se não houver registro no dia da aula → FALTA (Motor Anti-Furo).
    Todas as sub-queries usam paginação automática (chunks de 1 000 linhas)
    para superar o limite do PostgREST e evitar corte silencioso de dados.
    """
    def _paginar(query_fn):
        """Executa query_fn(inicio, fim) em loop até esgotar os dados."""
        todos, inicio = [], 0
        while True:
            res = query_fn(inicio, inicio + 999).execute()
            if res.data:
                todos.extend(res.data)
            if not res.data or len(res.data) < 1000:
                break
            inicio += 1000
        return todos

    # Normaliza qualquer valor (date puro 'YYYY-MM-DD' OU timestamp
    # 'YYYY-MM-DDTHH:MM:SS+00:00') para a string de data pura 'YYYY-MM-DD'.
    # CRÍTICO: diario_aulas.data_aula pode vir como timestamp e frequencia.data_aula
    # como date — sem normalizar, comparações de igualdade e filtros de intervalo
    # silenciosamente falham (ver listar_datas_aulas_registradas).
    def _norm_data(v):
        return str(v)[:10] if v is not None else ""

    try:
        di_str = _norm_data(data_inicio)
        df_str = _norm_data(data_fim)
        # Limite superior exclusivo (df + 1 dia) para que filtros .lt() capturem
        # tanto 'YYYY-MM-DD' quanto 'YYYY-MM-DDTHH:MM:SS+00:00' do último dia.
        try:
            df_excl = (pd.to_datetime(df_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            df_excl = df_str

        # ── Alunos ──────────────────────────────────────────────────────────
        def _q_al(i, f):
            q = supabase.table("alunos").select("id, nome, turma").neq("status", "Inativo")
            if turma_filtro and turma_filtro != "Todas":
                q = q.eq("turma", turma_filtro)
            return q.range(i, f)
        df_alunos = pd.DataFrame(_paginar(_q_al))
        if df_alunos.empty:
            return pd.DataFrame()

        # ── Frequência (select mínimo para economizar banda) ─────────────────
        def _q_fr(i, f):
            return (
                supabase.table("frequencia")
                .select("aluno_id, data_aula, status")
                .gte("data_aula", di_str)
                .lt("data_aula", df_excl)
                .range(i, f)
            )
        df_freq = pd.DataFrame(_paginar(_q_fr))
        if not df_freq.empty:
            df_freq["aluno_id"] = df_freq["aluno_id"].astype(str)
            df_freq["data_aula"] = df_freq["data_aula"].astype(str).str[:10]

        # ── Diário ───────────────────────────────────────────────────────────
        def _q_di(i, f):
            q = (
                supabase.table("diario_aulas")
                .select("turma, data_aula")
                .gte("data_aula", di_str)
                .lt("data_aula", df_excl)
            )
            if turma_filtro and turma_filtro != "Todas":
                q = q.eq("turma", turma_filtro)
            return q.range(i, f)
        df_diario = pd.DataFrame(_paginar(_q_di))
        if not df_diario.empty:
            df_diario["data_aula"] = df_diario["data_aula"].astype(str).str[:10]

        # ── Dias de aula por turma — UNIÃO Diário ∪ Frequência ───────────────
        # ANTI-FURO REVERSO: se houve registro de frequência num dia, então houve
        # aula — mesmo que o professor não tenha criado a linha no Diário. Sem isto,
        # presenças lançadas sem diário ficam invisíveis no relatório (causa raiz do
        # bug "Não foram encontradas aulas no Diário"). frequencia não tem coluna
        # turma → mapeamos aluno_id → turma pelos alunos carregados.
        id_para_turma = {
            str(r_id): r_turma
            for r_id, r_turma in zip(df_alunos["id"], df_alunos["turma"])
        }
        dias_por_turma = {}
        if not df_diario.empty:
            for _, r in df_diario.iterrows():
                d = _norm_data(r["data_aula"])
                if di_str <= d <= df_str:
                    dias_por_turma.setdefault(r["turma"], set()).add(d)
        if not df_freq.empty:
            for _, r in df_freq.iterrows():
                t = id_para_turma.get(str(r["aluno_id"]))
                if not t:
                    continue
                d = _norm_data(r["data_aula"])
                if di_str <= d <= df_str:
                    dias_por_turma.setdefault(t, set()).add(d)

        if not dias_por_turma:
            return pd.DataFrame()

        resultados = []
        for _, aluno in df_alunos.iterrows():
            aluno_id    = str(aluno["id"])
            turma_aluno = aluno["turma"]

            # Dias reais de aula desta turma no período (Diário ∪ Frequência)
            dias_aula_turma = sorted(dias_por_turma.get(turma_aluno, set()))
            total_aulas_turma = len(dias_aula_turma)
            if total_aulas_turma == 0:
                continue  # turma sem aula no período → pula aluno

            linha = {"Nome": aluno["nome"], "Turma": turma_aluno}
            faltas, presencas, justificadas = 0, 0, 0

            for dia in dias_aula_turma:
                dia_str = pd.to_datetime(dia).strftime("%d/%m")

                if not df_freq.empty:
                    reg = df_freq[
                        (df_freq["aluno_id"] == aluno_id)
                        & (df_freq["data_aula"] == dia)
                    ]
                    if not reg.empty:
                        status = str(reg.iloc[0]["status"]).upper()
                        if status == "PRESENTE":
                            linha[dia_str] = "P"
                            presencas += 1
                        elif status == "JUSTIFICADA":
                            linha[dia_str] = "J"
                            justificadas += 1
                        else:
                            linha[dia_str] = "F"
                            faltas += 1
                    else:
                        # Dia existia no Diário mas sem registro → FALTA (Anti-Furo)
                        linha[dia_str] = "F"
                        faltas += 1
                else:
                    linha[dia_str] = "F"
                    faltas += 1

            # Denominador real: total de aulas da turma no Diário
            linha["Total Aulas"] = total_aulas_turma
            linha["Total P"]     = presencas
            linha["Total F"]     = faltas
            linha["Total J"]     = justificadas

            taxa = (presencas / total_aulas_turma * 100) if total_aulas_turma > 0 else 0
            linha["% Presença"]  = f"{taxa:.1f}%"

            resultados.append(linha)

        return pd.DataFrame(resultados).sort_values(by="Nome")
    except Exception as e:
        print(f"Erro na matriz de relatório: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_presentes_dia_todos(data: str) -> list:
    """
    Retorna todos os alunos presentes num dado dia (todas as turmas).
    Usado no relatório de Prestação de Contas Diária.
    data: string ISO 'YYYY-MM-DD'
    """
    try:
        res = (
            supabase.from_("frequencia")
            .select("aluno_id, alunos(nome, turma)")
            .eq("data_aula", data)
            .eq("status", "PRESENTE")
            .execute()
        )
        return res.data if res.data else []
    except Exception:
        return []


# ==============================================================================
# 📅 CALENDÁRIO INSTITUCIONAL — Dias Sem Aula (reuniões, recesso, etc.)
# ==============================================================================

def get_dias_sem_aula(data_ini: str = None, data_fim: str = None) -> set:
    """
    Retorna set de datetime.date com dias registrados como SEM AULA
    (reuniões internas, recessos institucionais, feriados locais, etc.).
    Filtra pelo intervalo se fornecido; caso contrário, retorna todos.
    Tabela: dias_sem_aula (data date PK, motivo text, criado_em, criado_por)
    """
    import datetime as _dt
    try:
        q = supabase.from_("dias_sem_aula").select("data")
        if data_ini:
            q = q.gte("data", data_ini)
        if data_fim:
            q = q.lte("data", data_fim)
        res = q.order("data").execute()
        return {
            _dt.date.fromisoformat(str(r["data"]))
            for r in (res.data or [])
            if r.get("data")
        }
    except Exception:
        return set()


def get_primeira_data_frequencia():
    """
    Retorna a data (datetime.date) do PRIMEIRO dia com frequência registrada no
    sistema, ou None se ainda não houver nenhum registro. Usada para auto-preencher
    e travar a data inicial dos relatórios (não permitir período anterior ao início
    real da frequência).
    """
    import datetime as _dt
    try:
        r = (
            supabase.from_("frequencia")
            .select("data_aula")
            .order("data_aula")
            .limit(1)
            .execute()
        )
        if not r.data:
            return None
        return _dt.date.fromisoformat(str(r.data[0]["data_aula"])[:10])
    except Exception:
        return None


def registrar_dia_sem_aula(data_iso: str, motivo: str = "", criado_por: str = "") -> bool:
    """
    Registra um dia como SEM AULA no calendário institucional.
    Tenta insert; se já existir (duplicate), faz update do motivo/criado_por.
    Retorna True se sucesso.
    """
    payload = {"data": data_iso, "motivo": str(motivo or "").strip(), "criado_por": str(criado_por or "").strip()}
    try:
        supabase.from_("dias_sem_aula").insert(payload).execute()
        return True
    except Exception:
        pass
    try:
        supabase.from_("dias_sem_aula").update(
            {"motivo": str(motivo or "").strip(), "criado_por": str(criado_por or "").strip()}
        ).eq("data", data_iso).execute()
        return True
    except Exception:
        return False


def remover_dia_sem_aula(data_iso: str) -> bool:
    """Remove um dia do calendário institucional. Retorna True se sucesso."""
    try:
        supabase.from_("dias_sem_aula").delete().eq("data", data_iso).execute()
        return True
    except Exception:
        return False


def get_dias_sem_aula_periodo_df(data_ini: str, data_fim: str):
    """
    Retorna DataFrame com todos os campos dos dias sem aula no período,
    para exibição na tela de gestão.
    """
    try:
        res = (
            supabase.from_("dias_sem_aula")
            .select("data, motivo, criado_por, criado_em")
            .gte("data", data_ini)
            .lte("data", data_fim)
            .order("data")
            .execute()
        )
        import pandas as _pd
        return _pd.DataFrame(res.data or [])
    except Exception:
        import pandas as _pd
        return _pd.DataFrame()


def get_presentes_periodo_todos(data_ini: str, data_fim: str) -> dict:
    """
    Retorna dict { 'YYYY-MM-DD': ['Nome1', 'Nome2', ...] } para todos os dias
    com pelo menos 1 presente no intervalo [data_ini, data_fim].

    Estratégia em 2 passos para garantir paginação correta:
      1. Pagina 'frequencia' SEM join (só data_aula + aluno_id) — igual a
         bi_presencas_periodo, que já é comprovadamente correto.
      2. Busca nomes dos alunos por aluno_id em lote separado.
    O .range() com join embutido (alunos(nome)) para na 1ª página de 1000
    independentemente do loop — por isso a abordagem sem join é necessária.
    """
    try:
        # ── Passo 1: buscar todos os registros PRESENTE com paginação ────────
        PAGE        = 1000
        MAX_PAGINAS = 50        # máx 50.000 registros
        registros   = []
        offset      = 0
        for _ in range(MAX_PAGINAS):
            res = (
                supabase.from_("frequencia")
                .select("data_aula, aluno_id")
                .gte("data_aula", data_ini)
                .lte("data_aula", data_fim)
                .eq("status", "PRESENTE")
                .order("data_aula")
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            lote = res.data or []
            registros.extend(lote)
            if len(lote) < PAGE:
                break
            offset += PAGE

        if not registros:
            return {}

        # ── Passo 2: buscar nomes dos alunos em lote ────────────────────────
        aluno_ids = list({r["aluno_id"] for r in registros if r.get("aluno_id")})
        nomes_map: dict = {}
        CHUNK = 500
        for i in range(0, len(aluno_ids), CHUNK):
            chunk = aluno_ids[i : i + CHUNK]
            res_n = (
                supabase.from_("alunos")
                .select("id, nome")
                .in_("id", chunk)
                .execute()
            )
            for a in (res_n.data or []):
                nomes_map[a["id"]] = (a.get("nome") or "").strip()

        # ── Passo 3: montar dict por dia ─────────────────────────────────────
        por_dia: dict = {}
        for r in registros:
            data  = str(r.get("data_aula", "")).strip()
            nome  = nomes_map.get(r.get("aluno_id"), "")
            if not data or not nome:
                continue
            por_dia.setdefault(data, set()).add(nome)

        return {
            d: sorted(por_dia[d])
            for d in sorted(por_dia)
        }
    except Exception:
        return {}


# ==============================================================================
# 🩺 GESTÃO CLÍNICA E AVALIAÇÕES
# ==============================================================================
def salvar_avaliacao_aluno(dados):
    """Salva a avaliação clínica vinda do formato antigo/dicionário do main.py"""
    try:
        payload = {
            "aluno_id": dados.get("aluno_id"),
            "data_avaliacao": dados.get("data_avaliacao"),
            "avaliador": dados.get("avaliador", "Equipe"),
            "pressao_arterial": dados.get("pressao_arterial"),
            "peso": blindar_float(dados.get("peso")),
            "altura": blindar_float(dados.get("altura")),
            "imc": blindar_float(dados.get("imc")),
            "frequencia_cardiaca": blindar_float(dados.get("frequencia_cardiaca")),
            "saturacao_o2": blindar_float(dados.get("saturacao_o2")),
            "glicemia": blindar_float(dados.get("glicemia")),
            "temperatura": blindar_float(dados.get("temperatura")),
        }
        campos_reservados = list(payload.keys()) + ["id", "criado_em"]
        extras = {k: v for k, v in dados.items() if k not in campos_reservados}
        if extras:
            payload["observacoes"] = json.dumps(extras, ensure_ascii=False)
        supabase.table("avaliacoes").insert(payload).execute()
        return True, "Avaliação clínica guardada com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar avaliação: {e}"


def salvar_avaliacao_prontuario(
    aluno_id,
    data_av,
    dor,
    quedas,
    cirurgias,
    meds,
    mob_d,
    mob_e,
    f_d,
    f_e,
    tug1,
    tug2,
    tug3,
    avaliacao_id=None,
    bristol=None,
    urina=None,
    borg=None,
):
    try:
        obs_rev = revisar_texto_ia(meds) or meds
        dados_extras = {
            "quedas_6m": int(blindar_float(quedas)),
            "cirurgias": str(cirurgias) if cirurgias else "",
            "medicamentos": str(obs_rev) if obs_rev else "",
            "mobilidade_pes_dir": str(mob_d) if mob_d else "",
            "mobilidade_pes_esq": str(mob_e) if mob_e else "",
            "tug_cog_animais": blindar_float(tug2),
            "tug_cog_perguntas": blindar_float(tug3),
        }
        json_obs = json.dumps(dados_extras, ensure_ascii=False)

        dados = {
            "aluno_id": str(aluno_id),
            "data_avaliacao": str(data_av),
            "nivel_dor": int(blindar_float(dor)),
            "simetria_dir": blindar_float(f_d),
            "simetria_esq": blindar_float(f_e),
            "tug_segundos": blindar_float(tug1),
            "observacoes": json_obs,
            "bristol": str(bristol) if bristol else None,
            "urina": str(urina) if urina else None,
            "borg": str(borg) if borg else None,
            "peso": 0.0,
            "altura": 0.0,
        }
        if avaliacao_id:
            supabase.from_("prontuario_avaliacoes").update(dados).eq(
                "id", str(avaliacao_id)
            ).execute()
        else:
            supabase.from_("prontuario_avaliacoes").insert(dados).execute()
        try:
            get_avaliacoes_aluno.clear()
            bi_dados_individuais.clear()
        except Exception:
            pass
        return True, "Salvo!"
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def get_avaliacoes_aluno(aluno_id):
    try:
        res = (
            supabase.from_("prontuario_avaliacoes")
            .select("*")
            .eq("aluno_id", str(aluno_id))
            .order("data_avaliacao", desc=True)
            .execute()
        )
        if not res.data:
            return pd.DataFrame()
        registros = []
        for row in res.data:
            nr = row.copy()
            obs = str(row.get("observacoes") or "").strip()
            if obs.startswith("{") and obs.endswith("}"):
                try:
                    for k, v in json.loads(obs).items():
                        nr[k] = v
                    nr["medicamentos"] = json.loads(obs).get("medicamentos", "")
                except:
                    nr["medicamentos"] = obs
            else:
                nr["medicamentos"] = obs

            nr["dor_nivel"] = row.get("nivel_dor", 0)
            nr["forca_dir"] = row.get("simetria_dir", 0)
            nr["forca_esq"] = row.get("simetria_esq", 0)
            nr["tug_simples"] = row.get("tug_segundos", 0)
            registros.append(nr)
        return pd.DataFrame(registros)
    except Exception:
        return pd.DataFrame()


# ==============================================================================
# 📊 BI PRIME - INTELIGÊNCIA DE NEGÓCIOS
# ==============================================================================
@st.cache_data(ttl=120, show_spinner=False)
def bi_resumo_studio():
    hoje = datetime.date.today()
    c30 = (hoje - datetime.timedelta(days=30)).isoformat()
    c15 = (hoje - datetime.timedelta(days=15)).isoformat()
    try:
        r_al = supabase.from_("alunos").select("id, status, cor_alerta_atual").execute()
        df = pd.DataFrame(r_al.data or [])
        ativos    = int((df["status"] == "Ativo").sum())   if not df.empty else 0
        inativos  = int((df["status"] == "Inativo").sum()) if not df.empty else 0
        risco_v   = int((df.get("cor_alerta_atual", pd.Series()) == "🔴").sum()) if not df.empty else 0
        risco_a   = int((df.get("cor_alerta_atual", pd.Series()) == "🟡").sum()) if not df.empty else 0
        ids_ativos = set(df[df["status"] == "Ativo"]["id"].tolist()) if not df.empty else set()
    except Exception:
        ativos = inativos = risco_v = risco_a = 0
        ids_ativos = set()
    try:
        r_f = supabase.from_("frequencia").select("status").gte("data_aula", c30).limit(10000).execute()
        df_f = pd.DataFrame(r_f.data or [])
        t_reg = len(df_f)
        pres  = int((df_f["status"] == "PRESENTE").sum()) if not df_f.empty else 0
        taxa  = round(pres / t_reg * 100, 1) if t_reg > 0 else 0.0
    except Exception:
        taxa = 0.0
    try:
        r_f15 = (supabase.from_("frequencia").select("aluno_id")
                 .gte("data_aula", c15).eq("status", "PRESENTE").limit(5000).execute())
        ids_com_pres = {r["aluno_id"] for r in (r_f15.data or [])}
        sem_pres_15  = len(ids_ativos - ids_com_pres)
    except Exception:
        sem_pres_15 = 0
    return {
        "total_ativos":    ativos,
        "total_inativos":  inativos,
        "taxa_presenca_30": taxa,
        "risco_vermelho":  risco_v,
        "risco_amarelo":   risco_a,
        "sem_presenca_15": sem_pres_15,
    }


@st.cache_data(ttl=300, show_spinner=False)
def bi_media_alunos_dia():
    """Média de alunos (distintos) presentes por dia de aula.

    Retorna dict com:
      - media_periodo : média/dia desde o início do projeto (1ª presença registrada)
      - media_mes     : média/dia no mês corrente (dia 1 até hoje)
      - dias_periodo  : nº de dias com aula no período
      - dias_mes      : nº de dias com aula no mês
      - inicio_periodo: data (YYYY-MM-DD) da 1ª presença, ou None
    """
    hoje = datetime.date.today()
    vazio = {
        "media_periodo": 0.0, "media_mes": 0.0,
        "dias_periodo": 0, "dias_mes": 0, "inicio_periodo": None,
    }
    try:
        r = (supabase.from_("frequencia").select("data_aula")
             .eq("status", "PRESENTE").order("data_aula").limit(1).execute())
        if not r.data:
            return vazio
        inicio = str(r.data[0]["data_aula"])[:10]
    except Exception:
        return vazio

    # Carrega TODAS as presenças do período (início → hoje) com paginação
    # completa — sem teto artificial, para que a média "desde o início do
    # projeto" nunca seja calculada sobre dados truncados.
    try:
        PAGE = 1000
        registros = []
        offset = 0
        while True:
            r = (
                supabase.from_("frequencia")
                .select("data_aula, aluno_id")
                .eq("status", "PRESENTE")
                .gte("data_aula", inicio)
                .lte("data_aula", hoje.isoformat())
                .order("data_aula")
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            lote = r.data or []
            registros.extend(lote)
            if len(lote) < PAGE:
                break
            offset += PAGE
    except Exception:
        return vazio

    if not registros:
        return vazio

    df = pd.DataFrame(registros)
    df["dia"] = df["data_aula"].astype(str).str[:10]

    def _calc(sub):
        if sub.empty:
            return 0.0, 0
        if "aluno_id" in sub.columns:
            por_dia = sub.groupby("dia")["aluno_id"].nunique()
        else:
            por_dia = sub.groupby("dia").size()
        dias = int(len(por_dia))
        media = round(float(por_dia.mean()), 1) if dias else 0.0
        return media, dias

    media_per, dias_per = _calc(df)
    primeiro_mes = hoje.replace(day=1).isoformat()
    media_mes, dias_mes = _calc(df[df["dia"] >= primeiro_mes])
    return {
        "media_periodo": media_per, "media_mes": media_mes,
        "dias_periodo": dias_per, "dias_mes": dias_mes,
        "inicio_periodo": inicio,
    }


@st.cache_data(ttl=300, show_spinner=False)
def bi_presencas_por_mes():
    """Total de presenças (registros PRESENTE) no ANO corrente, detalhado por mês.

    Retorna dict com:
      - total_ano : total de presenças desde 01/jan do ano atual até hoje
      - por_mes   : lista [(rótulo_mes, total), ...] de Janeiro até o mês atual
                    (inclui meses com 0 presenças)
      - ano       : ano de referência (int)
    """
    hoje = datetime.date.today()
    ano = hoje.year
    inicio_ano = datetime.date(ano, 1, 1).isoformat()
    meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    vazio = {"total_ano": 0, "por_mes": [], "ano": ano}

    try:
        PAGE = 1000
        registros = []
        offset = 0
        while True:
            r = (
                supabase.from_("frequencia")
                .select("data_aula")
                .eq("status", "PRESENTE")
                .gte("data_aula", inicio_ano)
                .lte("data_aula", hoje.isoformat())
                .order("data_aula")
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            lote = r.data or []
            registros.extend(lote)
            if len(lote) < PAGE:
                break
            offset += PAGE
    except Exception:
        return vazio

    total = len(registros)
    cont = {}
    if registros:
        df = pd.DataFrame(registros)
        df["mes"] = df["data_aula"].astype(str).str[5:7]
        cont = df.groupby("mes").size().to_dict()

    por_mes = [
        (f"{meses_pt[m - 1]}/{str(ano)[2:]}", int(cont.get(f"{m:02d}", 0)))
        for m in range(1, hoje.month + 1)
    ]
    return {"total_ano": total, "por_mes": por_mes, "ano": ano}


@st.cache_data(ttl=120, show_spinner=False)
def bi_evolucao_cadastros():
    try:
        r = supabase.from_("alunos").select("created_at").execute()
        df = pd.DataFrame(r.data or [])
        if df.empty or "created_at" not in df.columns:
            return pd.DataFrame()
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        corte = datetime.date.today() - datetime.timedelta(days=18 * 30)
        df = df[df["created_at"].dt.date >= corte]
        df["mes"] = df["created_at"].dt.strftime("%b/%y")
        df["ordem"] = df["created_at"].dt.to_period("M")
        contagem = (df.groupby(["ordem", "mes"]).size()
                    .reset_index(name="novos_alunos")
                    .sort_values("ordem"))
        return contagem[["mes", "novos_alunos"]].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_frequencia_turmas(dias=30):
    try:
        corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
        r_f = (supabase.from_("frequencia").select("aluno_id, status")
               .gte("data_aula", corte).limit(20000).execute())
        df_f = pd.DataFrame(r_f.data or [])
        if df_f.empty:
            return pd.DataFrame()
        r_al = supabase.from_("alunos").select("id, turma").eq("status", "Ativo").execute()
        df_al = pd.DataFrame(r_al.data or [])
        if df_al.empty:
            return pd.DataFrame()
        df = df_f.merge(df_al, left_on="aluno_id", right_on="id", how="left")
        df = df.dropna(subset=["turma"])
        agg = df.groupby("turma").apply(
            lambda g: round((g["status"] == "PRESENTE").sum() / len(g) * 100, 1)
        ).reset_index(name="taxa_presenca")
        return agg.sort_values("taxa_presenca", ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_distribuicao_risco():
    try:
        r = supabase.from_("alunos").select("cor_alerta_atual").eq("status", "Ativo").execute()
        df = pd.DataFrame(r.data or [])
        if df.empty:
            return pd.DataFrame()
        df["cor_alerta_atual"] = df["cor_alerta_atual"].fillna("⚪").replace("", "⚪")
        contagem = df["cor_alerta_atual"].value_counts().reset_index()
        contagem.columns = ["cor_alerta_atual", "total"]
        return contagem
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_dores_studio():
    try:
        r = supabase.from_("anamnese_dores").select("regiao").execute()
        df = pd.DataFrame(r.data or [])
        if df.empty or "regiao" not in df.columns:
            return pd.DataFrame()
        contagem = df["regiao"].value_counts().head(10).reset_index()
        contagem.columns = ["label", "count"]
        return contagem
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_alunos_risco_abandono(dias=30):
    try:
        hoje = datetime.date.today()
        corte = (hoje - datetime.timedelta(days=dias)).isoformat()
        r_al = (supabase.from_("alunos")
                .select("id, nome, turma, whatsapp, cor_alerta_atual")
                .eq("status", "Ativo").execute())
        df_al = pd.DataFrame(r_al.data or [])
        if df_al.empty:
            return pd.DataFrame()
        r_f = (supabase.from_("frequencia").select("aluno_id, data_aula")
               .gte("data_aula", corte).eq("status", "PRESENTE").limit(10000).execute())
        df_f = pd.DataFrame(r_f.data or [])
        pres_ids = set(df_f["aluno_id"].tolist()) if not df_f.empty else set()
        ausentes = df_al[~df_al["id"].isin(pres_ids)].copy()
        if ausentes.empty:
            return pd.DataFrame()
        # Última presença de todos os tempos
        r_ult = (supabase.from_("frequencia").select("aluno_id, data_aula")
                 .in_("aluno_id", ausentes["id"].tolist())
                 .eq("status", "PRESENTE").limit(10000).execute())
        df_ult = pd.DataFrame(r_ult.data or [])
        if not df_ult.empty:
            ult_pres = (df_ult.groupby("aluno_id")["data_aula"].max()
                        .reset_index().rename(columns={"data_aula": "ultima_presenca"}))
            ausentes = ausentes.merge(ult_pres, left_on="id", right_on="aluno_id", how="left")
        else:
            ausentes["ultima_presenca"] = None
        ausentes["dias_ausente"] = ausentes["ultima_presenca"].apply(
            lambda d: (hoje - datetime.date.fromisoformat(str(d))).days
            if d and str(d) not in ("None", "nan", "") else dias + 1
        )
        return ausentes.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_presencas_periodo(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """
    Retorna todos os registos PRESENTE no intervalo.
    Usa paginação por .range() para contornar o limite de 1000 linhas
    que o servidor Supabase impõe independentemente do .limit() do cliente.
    """
    try:
        PAGE       = 1000
        MAX_PAGINAS = 30          # guarda: máximo 30.000 registros (evita loop infinito)
        todos      = []
        offset     = 0
        for _ in range(MAX_PAGINAS):
            r = (
                supabase.from_("frequencia")
                .select("data_aula, aluno_id")
                .eq("status", "PRESENTE")
                .gte("data_aula", str(data_inicio))
                .lte("data_aula", str(data_fim))
                .order("data_aula")
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            lote = r.data or []
            todos.extend(lote)
            if len(lote) < PAGE:
                break          # última página: menos de PAGE itens → fim dos dados
            offset += PAGE
        return pd.DataFrame(todos)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def bi_dados_individuais(aluno_id):
    """
    Retorna dict com DataFrames e listas para o relatório BI individual do aluno.
    Chaves: 'avaliacoes', 'frequencias', 'atestados', 'dores'
    """
    resultado = {"avaliacoes": pd.DataFrame(), "frequencias": pd.DataFrame(),
                 "atestados": pd.DataFrame(), "dores": []}
    try:
        r_av = (supabase.from_("prontuario_avaliacoes").select("*")
                .eq("aluno_id", str(aluno_id)).order("data_avaliacao").execute())
        resultado["avaliacoes"] = pd.DataFrame(r_av.data or [])
    except Exception:
        pass
    try:
        r_fr = (supabase.from_("frequencia").select("data_aula, status")
                .eq("aluno_id", str(aluno_id)).order("data_aula").execute())
        resultado["frequencias"] = pd.DataFrame(r_fr.data or [])
    except Exception:
        pass
    try:
        r_at = (supabase.from_("atestados_temporarios").select("*")
                .eq("aluno_id", str(aluno_id)).execute())
        resultado["atestados"] = pd.DataFrame(r_at.data or [])
    except Exception:
        pass
    try:
        r_do = (supabase.from_("anamnese_dores").select("*")
                .eq("aluno_id", str(aluno_id)).execute())
        resultado["dores"] = r_do.data or []
    except Exception:
        pass
    return resultado


# ==============================================================================
# 🔧 FUNÇÕES COMPLEMENTARES (turma, estatísticas, prontuário, CRM, atestados)
# ==============================================================================

def atualizar_turma_aluno(aluno_id, nova_turma):
    try:
        dados = {"turma": nova_turma, "turma_id": _resolver_turma_id(nova_turma)}
        supabase.from_("alunos").update(dados).eq("id", str(aluno_id)).execute()
        _inv_alunos()
        return True
    except Exception:
        return False


@st.cache_data(ttl=120, show_spinner=False)
def get_estatisticas_frequencia_aluno(aluno_id):
    try:
        res = supabase.from_("frequencia").select("status").eq("aluno_id", str(aluno_id)).execute()
        if not res.data:
            return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}
        total = len(res.data)
        presentes = sum(1 for r in res.data if r["status"] == "PRESENTE")
        return {"total": total, "presentes": presentes, "faltas": total - presentes,
                "percentual": (presentes / total) * 100 if total > 0 else 0.0}
    except Exception:
        return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}


@st.cache_data(ttl=180, show_spinner=False)
def get_ultima_presenca_batch(ids: tuple) -> dict:
    """
    Recebe uma tuple de aluno_ids e retorna {str(aluno_id): 'DD/MM/AA'}.
    Faz uma única query ao banco para toda a lista — use em grids de busca.
    TTL 3 min para não travar o cache nos grids interativos.
    """
    if not ids:
        return {}
    try:
        res = (
            supabase.from_("frequencia")
            .select("aluno_id, data_aula")
            .in_("aluno_id", [str(i) for i in ids])
            .eq("status", "PRESENTE")
            .order("data_aula", desc=True)
            .limit(5000)
            .execute()
        )
        if not res.data:
            return {}
        df = pd.DataFrame(res.data)
        ult = df.groupby("aluno_id")["data_aula"].max()
        resultado = {}
        for aid, d in ult.items():
            try:
                resultado[str(aid)] = datetime.date.fromisoformat(
                    str(d)[:10]
                ).strftime("%d/%m/%y")
            except Exception:
                pass
        return resultado
    except Exception:
        return {}


def excluir_avaliacao_prontuario(aval_id):
    try:
        supabase.from_("prontuario_avaliacoes").delete().eq("id", aval_id).execute()
        return True, "Excluído."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def get_historico_aulas_aluno(aluno_id):
    try:
        turma_aluno = supabase.from_("alunos").select("turma").eq("id", str(aluno_id)).execute().data[0]["turma"]
        datas_presente = [
            r["data_aula"] for r in
            supabase.from_("frequencia").select("data_aula")
            .eq("aluno_id", str(aluno_id)).eq("status", "PRESENTE")
            .order("data_aula", desc=True).execute().data
        ]
        match = re.search(r"(0[789]|1[012])", str(turma_aluno))
        hora_busca = match.group(1) if match else str(turma_aluno).split(" - ")[0].strip()
        mapa_diarios = {
            d["data_aula"]: d for d in
            supabase.from_("diario_aulas")
            .select("data_aula, objetivo_geral, exercicios_executados, foco_clinico_social, relatos_melhora")
            .ilike("turma", f"%{hora_busca}%")
            .in_("data_aula", datas_presente).execute().data
        }
        return [
            {"data_aula": dt,
             "objetivo_geral": mapa_diarios.get(dt, {}).get("objetivo_geral", "⚠️ Sem diário."),
             "exercicios_executados": mapa_diarios.get(dt, {}).get("exercicios_executados", ""),
             "foco_clinico_social": mapa_diarios.get(dt, {}).get("foco_clinico_social", ""),
             "relatos_melhora": mapa_diarios.get(dt, {}).get("relatos_melhora", "")}
            for dt in datas_presente
        ]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_crm_templates():
    try:
        return pd.DataFrame(supabase.from_("crm_templates").select("*").order("titulo").execute().data)
    except Exception:
        return pd.DataFrame()


def atualizar_crm_template(gatilho, nova_mensagem):
    try:
        supabase.from_("crm_templates").update(
            {"mensagem": nova_mensagem.strip(), "atualizado_em": datetime.datetime.now().isoformat()}
        ).eq("gatilho", gatilho).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


def salvar_atestado_temporario(aluno_id, data_registro, motivo, url_documento,
                               data_vencimento=None, tipo_atestado="outro"):
    """Arquiva um atestado na tabela atestados_temporarios.
    Se tipo_atestado='aptidao_fisica', atualiza também url_atestado_medico do aluno.
    Fallback gracioso para colunas ainda não criadas via migration.
    """
    payload = {
        "aluno_id":       str(aluno_id),
        "data_registro":  str(data_registro),
        "motivo":         str(motivo).strip(),
        "url_documento":  url_documento,
        "tipo_atestado":  str(tipo_atestado),
    }
    if data_vencimento:
        payload["data_vencimento"] = str(data_vencimento)

    def _insert(p):
        supabase.table("atestados_temporarios").insert(p).execute()

    try:
        _insert(payload)
    except Exception as e:
        err = str(e)
        fallback = dict(payload)
        removable = []
        if "tipo_atestado" in err:
            removable.append("tipo_atestado")
        if "data_vencimento" in err:
            removable.append("data_vencimento")
        if removable:
            for k in removable:
                fallback.pop(k, None)
            try:
                _insert(fallback)
            except Exception as e2:
                return False, str(e2)
        else:
            return False, err

    if str(tipo_atestado) == "aptidao_fisica":
        try:
            supabase.table("alunos").update(
                {"url_atestado_medico": str(url_documento)}
            ).eq("id", str(aluno_id)).execute()
        except Exception:
            pass

    return True, "Sucesso"


def get_atestados_vencendo(dias: int = 30) -> list:
    """Retorna atestados a vencer em até N dias (inclui já vencidos).
    Cada item tem: aluno_id, nome, turma, whatsapp, data_vencimento, motivo, dias_restantes.
    Retorna [] se a coluna data_vencimento não existe ou nenhum resultado."""
    import datetime as _dv
    try:
        hoje   = _dv.date.today()
        limite = hoje + _dv.timedelta(days=dias)
        res = (
            supabase.table("atestados_temporarios")
            .select("aluno_id,data_vencimento,motivo")
            .lte("data_vencimento", str(limite))
            .not_.is_("data_vencimento", "null")
            .order("data_vencimento")
            .execute()
        )
        if not res.data:
            return []
        aluno_ids = list({r["aluno_id"] for r in res.data})
        res2 = (
            supabase.table("alunos")
            .select("id,nome,turma,whatsapp")
            .in_("id", aluno_ids)
            .eq("status", "Ativo")
            .execute()
        )
        aluno_map = {str(a["id"]): a for a in (res2.data or [])}
        resultado = []
        visto = set()
        for r in res.data:
            a = aluno_map.get(str(r["aluno_id"]))
            if not a:
                continue
            chave = str(r["aluno_id"])
            if chave in visto:
                continue
            visto.add(chave)
            try:
                dv = _dv.date.fromisoformat(str(r["data_vencimento"])[:10])
                dias_rest = (dv - hoje).days
            except Exception:
                dias_rest = None
            resultado.append({
                **r,
                "nome":          a["nome"],
                "turma":         a.get("turma"),
                "whatsapp":      a.get("whatsapp"),
                "dias_restantes": dias_rest,
            })
        return resultado
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def get_atestados_temporarios(aluno_id):
    try:
        df = pd.DataFrame(
            supabase.table("atestados_temporarios").select("*")
            .eq("aluno_id", str(aluno_id)).order("data_registro", desc=True).execute().data
        )
        return df if not df.empty else None
    except Exception:
        return None


# ==============================================================================
# 🩻 ANAMNESE DE DORES (mapa corporal)
# ==============================================================================

def salvar_anamnese_dores(aluno_id, data_avaliacao, regioes, intensidade, observacoes, criado_por):
    try:
        import json as _json
        payload = {
            "aluno_id": str(aluno_id),
            "data_avaliacao": str(data_avaliacao),
            "regioes": regioes if isinstance(regioes, list) else list(regioes),
            "intensidade": intensidade if isinstance(intensidade, dict) else _json.loads(intensidade),
            "observacoes": str(observacoes or "").strip(),
            "criado_por": str(criado_por or "").strip(),
        }
        supabase.table("anamnese_dores").insert(payload).execute()
        _inv_dores()
        return True, "Salvo com sucesso."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_historico_dores(aluno_id):
    try:
        res = (
            supabase.table("anamnese_dores")
            .select("*")
            .eq("aluno_id", str(aluno_id))
            .order("data_avaliacao", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def excluir_anamnese_dores(registro_id):
    try:
        supabase.table("anamnese_dores").delete().eq("id", str(registro_id)).execute()
        _inv_dores()
        return True, "Excluído com sucesso."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# 🛠️ AUDITORIA: REPARAÇÃO DE TURMAS
# ==============================================================================
def ferramenta_reparacao_turmas():
    st.markdown("### 🛠️ Assistente de Reparação de Turmas")
    st.info("Esta ferramenta identifica alunos presos em nomes antigos de turmas.")
    try:
        res_t = supabase.table("turmas").select("nome").execute()
        turmas_oficiais = [t["nome"] for t in res_t.data]
        res_a = supabase.table("alunos").select("id, nome, turma").execute()
        df_alunos = pd.DataFrame(res_a.data)

        tf = [t for t in df_alunos["turma"].unique() if t not in turmas_oficiais and t]
        if not tf:
            st.success("Banco 100% sincronizado.")
            return

        for f in tf:
            with st.container(border=True):
                st.write(f"**Turma Antiga:** `{f}`")
                novo = st.selectbox("Mover para:", turmas_oficiais, key=f"sel_{f}")
                if st.button("Sincronizar", key=f"btn_{f}"):
                    supabase.table("alunos").update({"turma": novo}).eq(
                        "turma", f
                    ).execute()
                    st.rerun()
    except Exception as e:
        st.error(str(e))


def get_emails_sistema() -> list:
    """Retorna [{nome, email}] dos usuários cadastrados, ordenados por nome."""
    try:
        res = supabase.from_("usuarios").select("nome,email").order("nome").execute()
        return [r for r in (res.data or []) if r.get("email", "").strip()]
    except Exception:
        return []


def listar_usuarios_sistema() -> tuple:
    """Retorna (lista, erro_str) dos operadores do sistema.
    Tenta progressivamente remover colunas opcionais que ainda não existam
    (ativo, perfil) para não retornar vazio por migration pendente."""
    tentativas = [
        "id,nome,email,perfil,ativo,criado_em",
        "id,nome,email,ativo,criado_em",
        "id,nome,email,criado_em",
        "id,nome,email",
    ]
    for cols in tentativas:
        try:
            res = supabase.table("usuarios").select(cols).order("nome").execute()
            return res.data or [], None
        except Exception as e:
            last_err = str(e)
            continue
    return [], last_err


def atualizar_usuario_sistema(uid: str, payload: dict):
    """Atualiza campos de um usuário (nome, email, senha, ativo). Retorna (bool, msg)."""
    try:
        if "email" in payload:
            email_novo = payload["email"].strip().lower()
            dup = supabase.table("usuarios").select("id").eq("email", email_novo).neq("id", uid).execute()
            if dup.data:
                return False, "Este e-mail já está em uso por outro usuário."
            payload["email"] = email_novo
        if "nome" in payload:
            payload["nome"] = payload["nome"].strip()
        supabase.table("usuarios").update(payload).eq("id", uid).execute()
        return True, "✅ Usuário atualizado com sucesso."
    except Exception as e:
        return False, str(e)


def excluir_usuario_sistema(uid: str, email_session: str):
    """Exclui permanentemente um usuário. Impede auto-exclusão. Retorna (bool, msg)."""
    try:
        res = supabase.table("usuarios").select("email").eq("id", uid).execute()
        if not res.data:
            return False, "Usuário não encontrado."
        if res.data[0].get("email", "").strip().lower() == email_session.strip().lower():
            return False, "Você não pode excluir sua própria conta."
        supabase.table("usuarios").delete().eq("id", uid).execute()
        return True, "✅ Usuário excluído permanentemente."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# 🩺 REGISTROS DE PRESSÃO ARTERIAL
# ==============================================================================
SQL_CRIAR_REGISTROS_PA = """-- Execute no Supabase → SQL Editor para habilitar lançamento digital de PA:
CREATE TABLE IF NOT EXISTS registros_pa (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id        UUID REFERENCES alunos(id) ON DELETE CASCADE,
    aluno_nome      TEXT,
    data            DATE NOT NULL,
    hora            TEXT,
    sistolica       INTEGER NOT NULL,
    diastolica      INTEGER NOT NULL,
    pulso           INTEGER,
    momento         TEXT DEFAULT 'Antes da aula',
    braco           TEXT DEFAULT 'Esquerdo',
    posicao         TEXT DEFAULT 'Sentado',
    repeticao       TEXT DEFAULT '1ª aferição',
    exercicio_antes BOOLEAN DEFAULT FALSE,
    estimulantes    BOOLEAN DEFAULT FALSE,
    sintomas        JSONB DEFAULT '[]',
    obs             TEXT,
    turma           TEXT,
    professor       TEXT,
    registrado_por  TEXT,
    classificacao   TEXT,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_registros_pa_aluno ON registros_pa(aluno_id);
CREATE INDEX IF NOT EXISTS idx_registros_pa_data  ON registros_pa(data DESC);
-- Desabilita RLS para que o client anon do sistema possa ler/gravar:
ALTER TABLE registros_pa DISABLE ROW LEVEL SECURITY;
"""

# SQL para corrigir tabela já existente que foi criada com RLS habilitado
SQL_CORRIGIR_RLS_PA = """-- Correção rápida: desabilita Row-Level Security na tabela registros_pa
-- Execute no Supabase → SQL Editor:
ALTER TABLE registros_pa DISABLE ROW LEVEL SECURITY;
"""


def _tabela_pa_existe() -> bool:
    """Verifica se a tabela registros_pa existe no Supabase."""
    try:
        supabase.table("registros_pa").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def salvar_registro_pa(payload: dict) -> tuple:
    """Insere um registro de PA. Retorna (bool, msg)."""
    try:
        import uuid as _uuid
        payload.setdefault("id", str(_uuid.uuid4()))
        supabase.table("registros_pa").insert(payload).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def atualizar_registro_pa(registro_id: str, payload: dict) -> tuple:
    """Atualiza um registro de PA existente. Retorna (bool, msg)."""
    try:
        p = {k: v for k, v in payload.items() if k != "id"}
        supabase.table("registros_pa").update(p).eq("id", registro_id).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def get_registros_pa(aluno_id: str, limit: int = 100) -> list:
    """Retorna histórico de PA de um aluno, do mais recente para o mais antigo."""
    try:
        r = (
            supabase.table("registros_pa")
            .select("*")
            .eq("aluno_id", aluno_id)
            .order("data", desc=True)
            .order("criado_em", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def deletar_registro_pa(registro_id: str) -> tuple:
    """Remove permanentemente um registro de PA. Retorna (bool, msg)."""
    try:
        supabase.table("registros_pa").delete().eq("id", registro_id).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def get_registros_pa_turma(turma: str, data: str) -> list:
    """Retorna todos os registros de PA de uma turma numa data específica."""
    try:
        r = (
            supabase.table("registros_pa")
            .select("*")
            .eq("turma", turma)
            .eq("data", data)
            .order("aluno_nome")
            .execute()
        )
        return r.data or []
    except Exception:
        return []
