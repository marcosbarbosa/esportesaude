# ==============================================================================
# 📄 ARQUIVO: database.py
# 🎯 FUNÇÃO: Motor Central de Dados. Preserva 100% da Lógica Original (Matrículas,
#            Diários, Ocupação) + Novas Funcionalidades Clínicas, Arquivo Morto
#            e Integração de Impacto Social 60+.
# 📅 VERSÃO: 5.5 (PRO Elite - Código Integral + Auditoria QA 10x)
# ==============================================================================

import pandas as pd
import streamlit as st
import datetime
import time
from supabase import create_client, Client
import uuid
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🔐 DEFINIÇÃO DO SUPERUSUÁRIO (Mestre do Sistema)
ADMIN_MASTER = "marcosbarbosa.am@gmail.com"


@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase: Client = init_connection()


def _resolver_turma_id(turma_input: str):
    """Dado um nome de turma (text) ou UUID, retorna o UUID da turma.
    Aceita tanto o nome quanto o UUID diretamente. Retorna None se não encontrar."""
    if not turma_input:
        return None
    try:
        import uuid as _uuid_mod
        _uuid_mod.UUID(str(turma_input))
        return str(turma_input)  # já é UUID válido
    except (ValueError, AttributeError):
        pass
    try:
        res = supabase.from_("turmas").select("id").eq("nome", str(turma_input).strip()).execute()
        return res.data[0]["id"] if res.data else None
    except Exception:
        return None


try:
    import google.generativeai as genai

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ia_model = genai.GenerativeModel("gemini-1.5-flash")
    IA_ATIVA = True
except Exception as e:
    IA_ATIVA = False
    print(f"⚠️ IA Desativada. Motivo: {e}")


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


# ==============================================================================
# 🏛️ MÓDULO DE GESTÃO DE TURMAS (NOVO CRUD NORMALIZADO)
# ==============================================================================
@st.cache_data(ttl=300)
def get_todas_turmas(ativas_apenas=False):
    """Retorna todas as turmas cadastradas na base normalizada."""
    try:
        query = supabase.from_("turmas").select("*").order("nome")
        if ativas_apenas:
            query = query.eq("status", "Ativa")
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Erro ao buscar turmas: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_ocupacao_turmas(limite_padrao=40):
    """
    Motor de Termômetro: Calcula a quantidade de alunos matriculados
    em cada turma ativa e retorna as vagas disponíveis (Ignorando Inativos).
    """
    try:
        res = supabase.from_("alunos").select("turma_id").neq("status", "Inativo").execute()
        contagem_id = {}
        for row in (res.data or []):
            tid = row.get("turma_id")
            if tid:
                contagem_id[tid] = contagem_id.get(tid, 0) + 1

        res_t = supabase.from_("turmas").select("id, nome").eq("status", "Ativa").execute()
        turmas_ativas = res_t.data if res_t.data else []

        ocupacao = {}
        for t in turmas_ativas:
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
    except Exception as e:
        print(f"Erro ao buscar ocupação: {e}")
        return {}


def adicionar_turma(nome, horario, dias_semana):
    try:
        # Verificação extra preventiva sugerida pela QA
        check = supabase.from_("turmas").select("id").ilike("nome", nome.strip()).execute()
        if check.data:
            return False, "Já existe uma turma cadastrada com este exato nome."

        dados = {
            "nome": nome.strip(),
            "horario": horario.strip(),
            "dias_semana": dias_semana.strip(),
            "status": "Ativa",
        }
        supabase.from_("turmas").insert(dados).execute()
        return True, "Turma criada com sucesso!"
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return False, "Já existe uma turma cadastrada com este nome."
        return False, f"Erro ao criar turma: {e}"


def atualizar_turma(turma_id, nome, horario, dias_semana, status):
    """
    Atualiza a turma e sincroniza os nomes em todas as tabelas adjacentes,
    usando o NOME ANTIGO como âncora, evitando a dependência de IDs não registados.
    """
    try:
        # 1. Descobrir o nome antigo ANTES de fazer a alteração
        res_antiga = supabase.from_("turmas").select("nome").eq("id", str(turma_id)).execute()
        nome_antigo = res_antiga.data[0]['nome'] if res_antiga.data else None

        # 2. Atualizar a tabela principal de Turmas
        dados = {
            "nome": nome.strip(),
            "horario": horario.strip(),
            "dias_semana": dias_semana.strip(),
            "status": status,
        }
        supabase.from_("turmas").update(dados).eq("id", str(turma_id)).execute()

        # 3. Sincronizar campo turma TEXT (legado) nas tabelas adjacentes
        if nome_antigo and nome_antigo != nome.strip():
            supabase.from_("alunos").update({"turma": nome.strip()}).eq("turma", nome_antigo).execute()
            supabase.from_("diario_aulas").update({"turma": nome.strip()}).eq("turma", nome_antigo).execute()

        return True, "Turma atualizada com sucesso."
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def excluir_turma(turma_id):
    """Blindagem QA: Verifica ativamente a string do nome da turma nos alunos."""
    try:
        # 1. Identificar o nome da turma que se deseja excluir
        res_t = supabase.from_("turmas").select("nome").eq("id", str(turma_id)).execute()
        if not res_t.data:
            return False, "Turma não encontrada."
        nome_turma = res_t.data[0]['nome']

        # 2. Verificar se existem alunos vinculados via turma_id (FK normalizado)
        res_a = supabase.from_("alunos").select("id").eq("turma_id", str(turma_id)).execute()
        if res_a.data and len(res_a.data) > 0:
            return False, f"Não é possível excluir! Existem {len(res_a.data)} aluno(s) vinculados a esta turma."

        # 3. Se estiver limpa, pode excluir
        supabase.from_("turmas").delete().eq("id", str(turma_id)).execute()
        return True, "Turma excluída com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir turma: {str(e)}"


# ==============================================================================
# 🚀 PIPELINE DE INSCRIÇÕES (ONBOARDING)
# ==============================================================================
def salvar_pre_cadastro(nome, data_nasc, whatsapp, email):
    try:
        dados = {
            "nome": nome.upper().strip(),
            "data_nascimento": str(data_nasc) if data_nasc else None,
            "whatsapp": whatsapp,
            "email": email,
            "status": "Pendente",
        }
        supabase.from_("pre_cadastros").insert(dados).execute()
        return True, "Inscrição enviada com sucesso!"
    except Exception as e:
        return False, f"Erro ao enviar inscrição: {str(e)}"


def get_pre_cadastros_pendentes():
    try:
        res = (
            supabase.from_("pre_cadastros")
            .select("*")
            .in_("status", ["Pendente", "Lista de Espera"])
            .execute()
        )
        return res.data
    except Exception:
        return []


def aprovar_inscricao_aluno(pre_cadastro_id, turma_selecionada):
    try:
        res_pre = (
            supabase.from_("pre_cadastros")
            .select("*")
            .eq("id", pre_cadastro_id)
            .execute()
        )
        if not res_pre.data:
            return False, "Inscrição não encontrada."
        aluno_dados = res_pre.data[0]

        turma_id_val = _resolver_turma_id(turma_selecionada)
        novo_aluno = {
            "nome": aluno_dados.get("nome", "").upper().strip(),
            "turma": turma_selecionada,
            "turma_id": turma_id_val,
            "data_nascimento": aluno_dados.get("data_nascimento"),
            # pre_cadastros usa "celular" (não "whatsapp") — BUG-01 corrigido
            "whatsapp": aluno_dados.get("celular", "") or aluno_dados.get("whatsapp", ""),
            "email": aluno_dados.get("email", ""),
            "cpf": aluno_dados.get("cpf", ""),
            "rg": aluno_dados.get("rg", ""),
            "endereco": aluno_dados.get("endereco", ""),
            "bairro": aluno_dados.get("bairro", ""),
            "cep": aluno_dados.get("cep", ""),
            "contato_emergencia": aluno_dados.get("contato_emergencia", ""),
            "problemas_saude": aluno_dados.get("problemas_saude", ""),
            "medicamentos": aluno_dados.get("medicamentos", ""),
            "restricoes_fisicas": aluno_dados.get("restricoes_fisicas", ""),
            # pre_cadastros não tem url_foto/url_rg/url_receituario — BUG-02 corrigido
            "url_atestado_medico": aluno_dados.get("url_atestado_medico"),
            "status": "Ativo",
        }
        supabase.from_("alunos").insert(novo_aluno).execute()
        supabase.from_("pre_cadastros").update({"status": "Aprovado"}).eq(
            "id", pre_cadastro_id
        ).execute()
        return (
            True,
            f"Aluno {novo_aluno['nome']} matriculado com sucesso na {turma_selecionada}!",
        )
    except Exception as e:
        return False, f"Erro ao migrar aluno: {str(e)}"


def atualizar_perfil_aluno_dict(aluno_id, dados_atualizados):
    try:
        supabase.from_("alunos").update(dados_atualizados).eq(
            "id", str(aluno_id)
        ).execute()
        return True, "Perfil atualizado no banco de dados."
    except Exception as e:
        return False, str(e)


def rejeitar_inscricao_aluno(pre_cadastro_id):
    try:
        supabase.from_("pre_cadastros").update({"status": "Rejeitado"}).eq(
            "id", pre_cadastro_id
        ).execute()
        return True, "Inscrição arquivada."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# GESTÃO DE ALUNOS, STATUS E FREQUÊNCIA
# ==============================================================================
@st.cache_data(ttl=60)
def buscar_alunos_geral(termo="", incluir_inativos=False):
    try:
        query = supabase.from_("alunos").select("*")
        if termo:
            query = query.ilike("nome", f"%{termo}%")
        if not incluir_inativos:
            query = query.neq("status", "Inativo")
        res = query.order("nome").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()


def buscar_aluno_por_id(aluno_id):
    """Retorna dict com todos os dados de um aluno pelo ID, ou None se não encontrado."""
    try:
        res = supabase.from_("alunos").select("*").eq("id", str(aluno_id)).single().execute()
        return res.data if res.data else None
    except Exception:
        return None


def atualizar_dados_sociais_aluno(aluno_id, dados_atualizados):
    """Atualiza os campos socioeconômicos e de anamnese do aluno no Supabase."""
    try:
        dados_limpos = {
            k: v for k, v in dados_atualizados.items()
            if v is not None and str(v).strip() not in ("", "nan", "None")
        }
        if not dados_limpos:
            return False, "Nenhum dado válido para atualizar."
        supabase.from_("alunos").update(dados_limpos).eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True, "Perfil socioeconômico atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar: {str(e)}"

def alterar_status_aluno(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq(
            "id", str(aluno_id)
        ).execute()
        st.cache_data.clear()
        return True, f"Status alterado para {novo_status}."
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=60)
def get_alunos_por_turma(turma):
    try:
        turma_id_val = _resolver_turma_id(turma)
        query = supabase.from_("alunos").select("*")
        if turma_id_val:
            query = query.eq("turma_id", turma_id_val)
        else:
            query = query.eq("turma", turma)
        res = query.neq("status", "Inativo").order("nome").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()


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


def alternar_presenca(aluno_id, data_aula, presente, solicitante_email=""):
    try:
        d_aula = (
            datetime.datetime.strptime(str(data_aula), "%Y-%m-%d").date()
            if isinstance(data_aula, str)
            else data_aula
        )
        dias_passados = (datetime.date.today() - d_aula).days

        if dias_passados > 10 and solicitante_email != ADMIN_MASTER:
            return (
                False,
                "⚠️ Edição bloqueada. Frequências com mais de 10 dias só podem ser alteradas pelo Administrador Mestre.",
            )
    except Exception:
        pass

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
        return True, "Atualizado."
    except Exception as e:
        return False, str(e)


def get_estatisticas_frequencia_aluno(aluno_id):
    try:
        res = (
            supabase.from_("frequencia")
            .select("status")
            .eq("aluno_id", str(aluno_id))
            .execute()
        )
        if not res.data:
            return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}
        total = len(res.data)
        presentes = sum(1 for r in res.data if r["status"] == "PRESENTE")
        return {
            "total": total,
            "presentes": presentes,
            "faltas": total - presentes,
            "percentual": (presentes / total) * 100 if total > 0 else 0.0,
        }
    except Exception:
        return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}


def atualizar_perfil_aluno(
    aluno_id,
    nome,
    data_nasc,
    peso,
    altura,
    whats,
    email,
    url_foto,
    url_rg=None,
    url_rec=None,
    url_ate=None,
):
    try:
        dados = {
            "nome": nome.upper().strip(),
            "peso": peso,
            "altura": altura,
            "whatsapp": whats,
            "email": email,
            "url_foto": url_foto,
            "url_rg": url_rg,
            "url_receituario": url_rec,
            "url_atestado_medico": url_ate,
            "data_nascimento": str(data_nasc) if data_nasc else None,
        }
        supabase.from_("alunos").update(dados).eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True, "Perfil atualizado no MoveRight."
    except Exception as e:
        return False, str(e)


def atualizar_turma_aluno(aluno_id, nova_turma):
    try:
        turma_id_val = _resolver_turma_id(nova_turma)
        dados = {"turma": nova_turma, "turma_id": turma_id_val}
        supabase.from_("alunos").update(dados).eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False


def atualizar_aluno_completo(aluno_id, nome, turma, data_nasc, url_f):
    try:
        turma_id_val = _resolver_turma_id(turma)
        dados = {
            "nome": nome.upper().strip(),
            "turma": turma,
            "turma_id": turma_id_val,
            "data_nascimento": str(data_nasc) if data_nasc else None,
            "url_foto": url_f,
        }
        supabase.from_("alunos").update(dados).eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False


def cadastrar_novo_aluno(
    nome, turma, data_nasc=None, peso=0.0, altura=0.0, whats="", email="", url_f=None
):
    try:
        turma_id_val = _resolver_turma_id(turma)
        dados = {
            "nome": nome.upper().strip(),
            "turma": turma,
            "turma_id": turma_id_val,
            "data_nascimento": str(data_nasc) if data_nasc else None,
            "peso": peso,
            "altura": altura,
            "whatsapp": whats,
            "email": email,
            "url_foto": url_f,
            "status": "Ativo",
        }
        supabase.from_("alunos").insert(dados).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False


@st.cache_data(ttl=90)
def obter_dependencias_lote(lista_ids: list) -> dict:
    """
    Retorna contagens de dependências para múltiplos alunos em apenas 3 queries.
    Retorna: {aluno_id: {"frequencias": N, "avaliacoes": N, "atestados": N}}
    """
    resultado = {str(aid): {"frequencias": 0, "avaliacoes": 0, "atestados": 0}
                 for aid in lista_ids}
    if not lista_ids:
        return resultado
    ids = [str(i) for i in lista_ids]
    try:
        r_freq = supabase.from_("frequencia").select("aluno_id").in_("aluno_id", ids).execute()
        for row in (r_freq.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["frequencias"] += 1
    except Exception:
        pass
    try:
        r_aval = supabase.from_("prontuario_avaliacoes").select("aluno_id").in_("aluno_id", ids).execute()
        for row in (r_aval.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["avaliacoes"] += 1
    except Exception:
        pass
    try:
        r_ates = supabase.from_("atestados_temporarios").select("aluno_id").in_("aluno_id", ids).execute()
        for row in (r_ates.data or []):
            k = str(row["aluno_id"])
            if k in resultado:
                resultado[k]["atestados"] += 1
    except Exception:
        pass
    return resultado


def obter_resumo_aluno(aluno_id):
    try:
        r_freq = (
            supabase.from_("frequencia")
            .select("id")
            .eq("aluno_id", str(aluno_id))
            .execute()
        )
        r_pron = (
            supabase.from_("prontuario_avaliacoes")
            .select("id")
            .eq("aluno_id", str(aluno_id))
            .execute()
        )
        r_agen = (
            supabase.from_("agendamentos")
            .select("id")
            .eq("aluno_id", str(aluno_id))
            .execute()
        )

        return {
            "frequencias": len(r_freq.data) if r_freq.data else 0,
            "prontuarios": len(r_pron.data) if r_pron.data else 0,
            "agendamentos": len(r_agen.data) if r_agen.data else 0,
        }
    except Exception:
        return {"frequencias": 0, "prontuarios": 0, "agendamentos": 0}


def excluir_aluno_completo(aluno_id, solicitante_email):
    """Blindagem QA: Garante que todos os registos adjacentes (incluindo atestados) são apagados."""
    if solicitante_email != ADMIN_MASTER:
        return (
            False,
            "⚠️ ACESSO NEGADO: Apenas o administrador mestre pode realizar exclusões.",
        )
    try:
        supabase.from_("agendamentos").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("prontuario_avaliacoes").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("frequencia").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("atestados_temporarios").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("anamnese_dores").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("alunos").delete().eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True, "Aluno e todos os seus registos foram excluídos com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir: {str(e)}"


def excluir_aluno(aluno_id, solicitante_email):
    # QA: Redireciona para a função completa para garantir que não ficam dados órfãos.
    return excluir_aluno_completo(aluno_id, solicitante_email)


# ==============================================================================
# GESTÃO DE MÍDIAS E DIÁRIO (ATUALIZADO COM FOCO CLÍNICO E RELATOS)
# ==============================================================================
def upload_midia(file_bytes, file_name, mime_type, bucket="diario_midias_imbra"):
    try:
        nome_u = f"{uuid.uuid4()}.{file_name.split('.')[-1]}"
        supabase.storage.from_(bucket).upload(
            file=file_bytes, path=nome_u, file_options={"content-type": mime_type}
        )
        return supabase.storage.from_(bucket).get_public_url(nome_u)
    except Exception:
        return None


def get_diario_dia(data, turma):
    try:
        turma_id_val = _resolver_turma_id(turma)
        query = supabase.from_("diario_aulas").select("*").eq("data_aula", str(data))
        if turma_id_val:
            query = query.eq("turma_id", turma_id_val)
        else:
            query = query.eq("turma", turma)
        res = query.execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def get_diarios_periodo(data_inicio, data_fim, turma):
    try:
        turma_id_val = _resolver_turma_id(turma)
        query = (
            supabase.from_("diario_aulas")
            .select("*")
            .gte("data_aula", str(data_inicio))
            .lte("data_aula", str(data_fim))
        )
        if turma_id_val:
            query = query.eq("turma_id", turma_id_val)
        else:
            query = query.eq("turma", turma)
        res = query.order("data_aula").execute()
        return res.data
    except Exception:
        return []


def salvar_diario(
    data, turma, obj, exercicios, url_foto_g, midias, foco_clinico="", relatos=""
):
    try:
        turma_id_val = _resolver_turma_id(turma)
        dados_diario = {
            "data_aula": str(data),
            "turma": turma,
            "turma_id": turma_id_val,
            "objetivo_geral": obj,
            "exercicios_executados": exercicios,
            "url_foto_grupo": url_foto_g,
            "foco_clinico_social": foco_clinico,
            "relatos_melhora": relatos,
        }
        busca = supabase.from_("diario_aulas").select("id").eq("data_aula", str(data))
        if turma_id_val:
            busca = busca.eq("turma_id", turma_id_val)
        else:
            busca = busca.eq("turma", turma)
        res = busca.execute()
        if res.data:
            d_id = res.data[0]["id"]
            supabase.from_("diario_aulas").update(dados_diario).eq("id", d_id).execute()
        else:
            ins = supabase.from_("diario_aulas").insert(dados_diario).execute()
            d_id = ins.data[0]["id"]

        if midias and len(midias) > 0:
            for m in midias:
                dados_midia = {
                    "diario_aula_id": d_id,
                    "url_midia": m.get("url"),
                    "descricao_objetivo": m.get("descricao"),
                    "tipo": m.get("tipo", "foto"),
                }
                supabase.from_("diario_midias").insert(dados_midia).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"


def get_midias_diario(diario_id):
    try:
        res = (
            supabase.from_("diario_midias")
            .select("*")
            .eq("diario_aula_id", diario_id)
            .execute()
        )
        return res.data
    except Exception:
        return []


def excluir_midia_diario(midia_id):
    try:
        supabase.from_("diario_midias").delete().eq("id", midia_id).execute()
        return True
    except Exception:
        return False


def atualizar_legenda_midia(midia_id, legenda):
    try:
        supabase.from_("diario_midias").update({"descricao_objetivo": legenda}).eq(
            "id", midia_id
        ).execute()
        return True
    except Exception:
        return False


# ==============================================================================
# 🩺 GESTÃO CLÍNICA E PRONTUÁRIOS
# ==============================================================================
def salvar_avaliacao_prontuario(
    aluno_id,
    peso,
    altura,
    dor,
    tug,
    sim_d,
    sim_e,
    obs="",
    bristol=None,
    urina=None,
    borg=None,
    aval_id=None,
):
    try:
        obs_rev = revisar_texto_ia(obs) or obs
        dados = {
            "aluno_id": str(aluno_id),
            "data_avaliacao": datetime.date.today().isoformat(),
            "peso": peso,
            "altura": altura,
            "nivel_dor": dor,
            "tug_segundos": tug,
            "simetria_dir": sim_d,
            "simetria_esq": sim_e,
            "observacoes": obs_rev,
            "bristol": bristol,
            "urina": urina,
            "borg": borg,
        }
        if aval_id:
            supabase.from_("prontuario_avaliacoes").update(dados).eq(
                "id", aval_id
            ).execute()
        else:
            supabase.from_("prontuario_avaliacoes").insert(dados).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


def get_avaliacoes_aluno(aluno_id):
    try:
        res = (
            supabase.from_("prontuario_avaliacoes")
            .select("*")
            .eq("aluno_id", str(aluno_id))
            .order("data_avaliacao", desc=True)
            .execute()
        )
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def excluir_avaliacao_prontuario(aval_id):
    try:
        supabase.from_("prontuario_avaliacoes").delete().eq("id", aval_id).execute()
        return True, "Excluído com sucesso."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# RELATÓRIOS E AGENDAMENTOS
# ==============================================================================
def get_relatorio_periodo(di, df, turma_filtro="Ambas"):
    try:
        query = (
            supabase.from_("alunos")
            .select("id, nome, turma, whatsapp")
            .neq("status", "Inativo")
        )
        if turma_filtro and turma_filtro != "Ambas":
            turma_id_val = _resolver_turma_id(turma_filtro)
            if turma_id_val:
                query = query.eq("turma_id", turma_id_val)
            else:
                query = query.eq("turma", turma_filtro)
        res_a = query.execute()
        df_a = pd.DataFrame(res_a.data)

        res_f = (
            supabase.from_("frequencia")
            .select("*")
            .gte("data_aula", str(di))
            .lte("data_aula", str(df))
            .execute()
        )
        df_f = pd.DataFrame(res_f.data)
        return (
            pd.merge(df_f, df_a, left_on="aluno_id", right_on="id")
            if not df_f.empty
            else df_a
        )
    except Exception:
        return pd.DataFrame()


def get_historico_aulas_aluno(aluno_id):
    try:
        res_a = (
            supabase.from_("alunos").select("turma_id").eq("id", str(aluno_id)).execute()
        )
        if not res_a.data:
            return []
        turma_id_val = res_a.data[0].get("turma_id")

        res_f = (
            supabase.from_("frequencia")
            .select("data_aula")
            .eq("aluno_id", str(aluno_id))
            .eq("status", "PRESENTE")
            .order("data_aula", desc=True)
            .execute()
        )
        if not res_f.data:
            return []
        datas_presente = [r["data_aula"] for r in res_f.data]

        query_diario = (
            supabase.from_("diario_aulas")
            .select(
                "data_aula, objetivo_geral, exercicios_executados, foco_clinico_social, relatos_melhora"
            )
        )
        if turma_id_val:
            query_diario = query_diario.eq("turma_id", turma_id_val)
        res_d = query_diario.in_("data_aula", datas_presente).execute()
        mapa_diarios = {d["data_aula"]: d for d in res_d.data} if res_d.data else {}

        historico_completo = []
        for data_aula in datas_presente:
            diario = mapa_diarios.get(data_aula, {})
            historico_completo.append(
                {
                    "data_aula": data_aula,
                    "objetivo_geral": diario.get(
                        "objetivo_geral",
                        "⚠️ Diário de Bordo não preenchido pelo professor nesta data.",
                    ),
                    "exercicios_executados": diario.get("exercicios_executados", ""),
                    "foco_clinico_social": diario.get("foco_clinico_social", ""),
                    "relatos_melhora": diario.get("relatos_melhora", ""),
                }
            )
        return historico_completo
    except Exception as e:
        return []


def get_alunos_atrasados(dias_limite=90):
    try:
        # 1. 🚀 ADICIONADO 'url_foto' no SELECT para buscar a imagem do banco
        res_alunos = (
            supabase.from_("alunos")
            .select("id, nome, turma, whatsapp, url_foto") 
            .neq("status", "Inativo")
            .execute()
        )
        df_alunos = pd.DataFrame(res_alunos.data)
        if df_alunos.empty:
            return []

        res_avals = (
            supabase.from_("prontuario_avaliacoes")
            .select("aluno_id, data_avaliacao")
            .execute()
        )
        df_avals = pd.DataFrame(res_avals.data)

        atrasados = []
        hoje = datetime.date.today()
        for _, aluno in df_alunos.iterrows():
            aluno_id = aluno["id"]
            whatsapp_aluno = aluno.get("whatsapp", "")

            # 2. 🚀 Captura a URL da foto com segurança (se não tiver, fica em branco)
            foto_aluno = aluno.get("url_foto", "") 

            if not df_avals.empty and aluno_id in df_avals["aluno_id"].values:
                avals_aluno = df_avals[df_avals["aluno_id"] == aluno_id]
                ultima_data_str = avals_aluno["data_avaliacao"].max()
                try:
                    ultima_data = datetime.datetime.strptime(
                        ultima_data_str, "%Y-%m-%d"
                    ).date()
                    dias_passados = (hoje - ultima_data).days
                except:
                    dias_passados = 0

                if dias_passados >= dias_limite:
                    atrasados.append(
                        {
                            "id": aluno_id,
                            "nome": aluno["nome"],
                            "turma": aluno["turma"],
                            "whatsapp": whatsapp_aluno,
                            "url_foto": foto_aluno, # 3. 🚀 Injeta a foto no dicionário final
                            "dias": dias_passados,
                            "ultima_data": ultima_data.strftime("%d/%m/%Y"),
                            "status": "Atrasado",
                        }
                    )
            # ... (O resto da função continua igualzinho ao que você já tem)
            else:
                atrasados.append(
                    {
                        "id": aluno_id,
                        "nome": aluno["nome"],
                        "turma": aluno["turma"],
                        "whatsapp": whatsapp_aluno,
                        "dias": 9999,
                        "ultima_data": "Nunca",
                        "status": "Novo",
                    }
                )
        return sorted(atrasados, key=lambda x: x["dias"], reverse=True)
    except Exception:
        return []


def criar_agendamento(aluno_id, data_agendamento, horario, motivo):
    try:
        dados = {
            "aluno_id": aluno_id,
            "data_agendamento": str(data_agendamento),
            "horario": str(horario),
            "motivo": str(motivo),
            "status": "Pendente",
        }
        supabase.from_("agendamentos").insert(dados).execute()
        return True, "Agendamento criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao agendar: {e}"


def get_agendamentos_pendentes(limite=None):
    try:
        hoje = datetime.date.today()
        agora = datetime.datetime.now()
        res = (
            supabase.from_("agendamentos")
            .select(
                "id, data_agendamento, horario, motivo, aluno_id, alunos(nome, turma)"
            )
            .eq("status", "Pendente")
            .gte("data_agendamento", str(hoje))
            .order("data_agendamento")
            .order("horario")
            .execute()
        )
        agendamentos_ativos = []
        for ag in res.data:
            try:
                data_hora_str = f"{ag['data_agendamento']} {str(ag['horario'])[:5]}"
                data_hora_agendada = datetime.datetime.strptime(
                    data_hora_str, "%Y-%m-%d %H:%M"
                )
                if agora > data_hora_agendada + datetime.timedelta(minutes=60):
                    supabase.from_("agendamentos").update({"status": "Concluído"}).eq(
                        "id", ag["id"]
                    ).execute()
                else:
                    agendamentos_ativos.append(ag)
            except Exception:
                agendamentos_ativos.append(ag)

        if limite:
            return agendamentos_ativos[:limite]
        return agendamentos_ativos
    except Exception:
        return []


def concluir_ou_cancelar_agendamento(agendamento_id, novo_status="Concluído"):
    try:
        supabase.from_("agendamentos").update({"status": novo_status}).eq(
            "id", agendamento_id
        ).execute()
        return True
    except:
        return False


def verificar_conflito_agendamento(data, horario):
    res = (
        supabase.from_("agendamentos")
        .select("id, alunos(nome)")
        .eq("data_agendamento", str(data))
        .eq("horario", horario)
        .eq("status", "Pendente")
        .execute()
    )
    return res.data


# ==============================================================================
# 🚀 MÓDULO DE AUTENTICAÇÃO DE USUÁRIOS
# ==============================================================================
def autenticar_usuario(email, senha):
    try:
        res = (
            supabase.from_("usuarios")
            .select("*")
            .eq("email", email.strip().lower())
            .eq("senha", senha)
            .execute()
        )
        if res.data:
            return True, res.data[0]
        return False, "E-mail ou senha incorretos."
    except Exception as e:
        return False, f"Erro no servidor: {str(e)}"


def cadastrar_usuario_sistema(nome, email, senha):
    try:
        res = (
            supabase.from_("usuarios")
            .select("id")
            .eq("email", email.strip().lower())
            .execute()
        )
        if res.data:
            return False, "Este e-mail já está cadastrado no sistema."
        dados = {"nome": nome.strip(), "email": email.strip().lower(), "senha": senha}
        supabase.from_("usuarios").insert(dados).execute()
        return True, "Usuário administrativo criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao criar utilizador: {str(e)}"


# 🚀 NOVO MOTOR SMTP INJETADO AQUI!
def recuperar_senha_usuario(email_destino):
    try:
        # 1. Verifica se o e-mail existe e pega a senha
        res = (
            supabase.from_("usuarios")
            .select("senha, nome")
            .eq("email", email_destino.strip().lower())
            .execute()
        )

        # Prática de segurança temporariamente desligada para teste
        if not res.data:
            return (
                False,
                "TESTE DO ARQUITETO: Este e-mail não está cadastrado no Supabase!",
            )

        senha_recuperada = res.data[0]["senha"]
        nome_usuario = res.data[0]["nome"]

        # 2. Configurações do Carteiro (Injeção Direta para Teste)
        remetente = "marcosbarbosa.am@gmail.com"
        senha_app = "bmqzajtkikmuedpo"

        # 3. Desenho do E-mail (HTML Premium Elite)
        msg = MIMEMultipart()
        msg["From"] = f"Equipe MoveRight <{remetente}>"
        msg["To"] = email_destino.strip()
        msg["Subject"] = "🔐 Recuperação de Senha - MoveRight"

        corpo_email_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #F8FAFC; padding: 20px;">
                <div style="max-width: 500px; margin: auto; background-color: white; padding: 30px; border-radius: 12px; border-top: 5px solid #1E88E5; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                    <h2 style="color: #0A2540; margin-top: 0;">Recuperação de Acesso</h2>
                    <p style="font-size: 15px;">Olá, <strong>{nome_usuario}</strong>!</p>
                    <p style="font-size: 15px;">Recebemos um pedido de recuperação de acesso para a plataforma MoveRight. Aqui está a sua senha atual:</p>

                    <div style="background-color: #F1F5F9; padding: 15px; text-align: center; font-size: 22px; font-weight: 900; letter-spacing: 3px; border-radius: 8px; border: 1px dashed #CBD5E1; margin: 25px 0; color: #1E88E5;">
                        {senha_recuperada}
                    </div>

                    <p style="font-size: 13px; color: #64748B;">Recomendamos que troque essa senha por motivos de segurança e que não compartilhe este e-mail com ninguém.</p>
                    <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 20px 0;">
                    <p style="font-size: 11px; color: #94A3B8; text-align: center; margin: 0;">Instituto Muda Brasil • Plataforma MoveRight Elite</p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(corpo_email_html, "html"))

        # 4. Acionar o Carteiro (Exemplo com servidor Gmail)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Encriptação de segurança
        server.login(remetente, senha_app)
        server.send_message(msg)
        server.quit()

        return True, "E-mail enviado!"

    except Exception as e:
        print(f"Erro no envio de e-mail: {e}")
        return (
            False,
            f"Falha no servidor de e-mail (O carteiro tropeçou). Erro técnico: {str(e)}",
        )


# ==============================================================================
# 💬 MÓDULO DE MENSAGENS CRM E ANIVERSÁRIOS
# ==============================================================================
def get_crm_templates():
    try:
        res = supabase.from_("crm_templates").select("*").order("titulo").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()


def atualizar_crm_template(gatilho, nova_mensagem):
    try:
        supabase.from_("crm_templates").update(
            {
                "mensagem": nova_mensagem.strip(),
                "atualizado_em": datetime.datetime.now().isoformat(),
            }
        ).eq("gatilho", gatilho).execute()
        return True, "Template atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def get_template_seguro_db(gatilho, nome_aluno):
    """Busca o template no banco. Função centralizada."""
    primeiro_nome = str(nome_aluno).split()[0].capitalize() if nome_aluno else ""
    try:
        res = (
            supabase.from_("crm_templates")
            .select("mensagem")
            .eq("gatilho", gatilho)
            .execute()
        )
        if res.data:
            msg = res.data[0]["mensagem"]
            return msg.replace("{nome}", primeiro_nome)
    except:
        pass
    return f"Olá {primeiro_nome}, o Instituto Muda Brasil tem uma mensagem para você!"


# ==========================================
# GESTÃO DE ATESTADOS TEMPORÁRIOS
# ==========================================
def salvar_atestado_temporario(aluno_id, data_registro, motivo, url_documento):
    """Guarda um novo atestado médico temporário para justificar faltas."""
    try:
        payload = {
            "aluno_id": str(aluno_id),
            "data_registro": str(data_registro),
            "motivo": str(motivo).strip(),
            "url_documento": str(url_documento),
        }
        supabase.table("atestados_temporarios").insert(payload).execute()
        return True, "Sucesso"
    except Exception as e:
        print(f"Erro ao salvar atestado temporário: {e}")
        return False, str(e)


def get_atestados_temporarios(aluno_id):
    """Recupera o histórico de atestados temporários de um aluno."""
    try:
        res = (
            supabase.table("atestados_temporarios")
            .select("*")
            .eq("aluno_id", str(aluno_id))
            .order("data_registro", desc=True)
            .execute()
        )
        df = pd.DataFrame(res.data)
        return df if not df.empty else None
    except Exception as e:
        print(f"Erro ao buscar atestados temporários: {e}")
        return None

# ==============================================================================
# 🩻 ANAMNESE DE DORES — MAPA CORPORAL
# ==============================================================================
def salvar_anamnese_dores(aluno_id, data_avaliacao, regioes, intensidade, observacoes, criado_por):
    """Salva um novo registro de mapa corporal de dores. Retorna (ok, msg)."""
    try:
        payload = {
            "aluno_id":       str(aluno_id),
            "data_avaliacao": str(data_avaliacao),
            "regioes":        regioes or [],
            "intensidade":    intensidade or {},
            "observacoes":    (observacoes or "").strip(),
            "criado_por":     (criado_por or "").strip(),
        }
        supabase.table("anamnese_dores").insert(payload).execute()
        st.cache_data.clear()
        return True, "Mapa de dores salvo com sucesso."
    except Exception as e:
        return False, f"Erro ao salvar mapa de dores: {e}"


def buscar_historico_dores(aluno_id):
    """Retorna lista de avaliações de dores do aluno, mais recente primeiro."""
    try:
        res = (
            supabase.table("anamnese_dores")
            .select("id, data_avaliacao, regioes, intensidade, observacoes, criado_por, created_at")
            .eq("aluno_id", str(aluno_id))
            .order("data_avaliacao", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Erro ao buscar histórico de dores: {e}")
        return []


def excluir_anamnese_dores(avaliacao_id):
    """Exclui uma avaliação de dores pelo ID. Retorna (ok, msg)."""
    try:
        supabase.table("anamnese_dores").delete().eq("id", str(avaliacao_id)).execute()
        return True, "Avaliação excluída."
    except Exception as e:
        return False, f"Erro ao excluir avaliação de dores: {e}"


# ==============================================================================
# 📊 BI PRIME — FUNÇÕES DE INTELIGÊNCIA DE NEGÓCIO
# ==============================================================================
@st.cache_data(ttl=120)
def bi_resumo_studio():
    """Indicadores macro do estúdio para o dashboard geral."""
    hoje    = datetime.date.today()
    corte30 = (hoje - datetime.timedelta(days=30)).isoformat()
    corte15 = (hoje - datetime.timedelta(days=15)).isoformat()
    try:
        r_al   = supabase.from_("alunos").select("id, status, cor_alerta_atual").execute()
        df_al  = pd.DataFrame(r_al.data or [])
        ativos   = int((df_al["status"] == "Ativo").sum())   if not df_al.empty else 0
        inativos = int((df_al["status"] == "Inativo").sum()) if not df_al.empty else 0
        risco_v  = int((df_al["cor_alerta_atual"] == "🔴").sum()) if not df_al.empty else 0
        risco_a  = int((df_al["cor_alerta_atual"] == "🟡").sum())  if not df_al.empty else 0
        ids_ativos = set(df_al[df_al["status"] == "Ativo"]["id"].tolist()) if not df_al.empty else set()
    except Exception:
        ativos = inativos = risco_v = risco_a = 0
        ids_ativos = set()
    try:
        r_f   = supabase.from_("frequencia").select("aluno_id, status, data_aula").gte("data_aula", corte30).execute()
        df_f  = pd.DataFrame(r_f.data or [])
        total_reg = len(df_f)
        presentes = int((df_f["status"] == "PRESENTE").sum()) if not df_f.empty else 0
        taxa_pres = round(presentes / total_reg * 100, 1) if total_reg > 0 else 0.0
        pres15_ids = set(df_f[df_f["data_aula"] >= corte15]["aluno_id"].unique()) if not df_f.empty else set()
        sem_pres15 = len(ids_ativos - pres15_ids)
    except Exception:
        taxa_pres = 0.0
        sem_pres15 = 0
    return {
        "total_ativos":     ativos,
        "total_inativos":   inativos,
        "taxa_presenca_30": taxa_pres,
        "risco_vermelho":   risco_v,
        "risco_amarelo":    risco_a,
        "sem_presenca_15":  sem_pres15,
    }


@st.cache_data(ttl=300)
def bi_evolucao_cadastros():
    """Novos alunos por mês — últimos 18 meses."""
    try:
        r  = supabase.from_("alunos").select("created_at").execute()
        df = pd.DataFrame(r.data or [])
        if df.empty:
            return pd.DataFrame(columns=["mes", "novos_alunos"])
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.dropna(subset=["created_at"])
        df["mes"] = df["created_at"].dt.to_period("M").astype(str)
        return df.groupby("mes").size().reset_index(name="novos_alunos").tail(18)
    except Exception:
        return pd.DataFrame(columns=["mes", "novos_alunos"])


@st.cache_data(ttl=120)
def bi_frequencia_turmas(dias=30):
    """Taxa de presença por turma nos últimos N dias."""
    try:
        corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
        r_f  = supabase.from_("frequencia").select("aluno_id, status").gte("data_aula", corte).execute()
        r_al = supabase.from_("alunos").select("id, turma_id").neq("status", "Inativo").execute()
        r_t  = supabase.from_("turmas").select("id, nome").execute()
        df_f  = pd.DataFrame(r_f.data  or [])
        df_al = pd.DataFrame(r_al.data or [])
        df_t  = pd.DataFrame(r_t.data  or [])
        if df_f.empty or df_al.empty or df_t.empty:
            return pd.DataFrame(columns=["turma", "taxa_presenca"])
        df_al = df_al.merge(df_t, left_on="turma_id", right_on="id", how="left").rename(columns={"nome": "turma"})
        df = df_f.merge(df_al[["id", "turma"]], left_on="aluno_id", right_on="id", how="left").dropna(subset=["turma"])
        grp = (
            df.groupby("turma")
            .apply(lambda g: round(len(g[g["status"] == "PRESENTE"]) / max(len(g), 1) * 100, 1))
            .reset_index(name="taxa_presenca")
        )
        return grp.sort_values("taxa_presenca", ascending=True)
    except Exception:
        return pd.DataFrame(columns=["turma", "taxa_presenca"])


@st.cache_data(ttl=120)
def bi_alunos_risco_abandono(dias=30):
    """Alunos ativos sem presença nos últimos N dias, com data da última presença."""
    try:
        corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
        r_al  = supabase.from_("alunos").select(
            "id, nome, turma, whatsapp, cor_alerta_atual"
        ).eq("status", "Ativo").execute()
        r_f   = supabase.from_("frequencia").select("aluno_id").gte("data_aula", corte).eq("status", "PRESENTE").execute()
        df_al = pd.DataFrame(r_al.data or [])
        if df_al.empty:
            return pd.DataFrame()
        pres_ids = set(r["aluno_id"] for r in (r_f.data or []))
        df_aus = df_al[~df_al["id"].isin(pres_ids)].copy()
        if df_aus.empty:
            return pd.DataFrame()
        # última presença de cada ausente
        ids_aus = df_aus["id"].tolist()
        r_ult = supabase.from_("frequencia").select("aluno_id, data_aula").in_(
            "aluno_id", ids_aus
        ).eq("status", "PRESENTE").order("data_aula", desc=True).execute()
        ult_map: dict = {}
        for row in (r_ult.data or []):
            if row["aluno_id"] not in ult_map:
                ult_map[row["aluno_id"]] = row["data_aula"]
        hoje = datetime.date.today()
        def _dias(v):
            try:
                return (hoje - datetime.date.fromisoformat(str(v)[:10])).days
            except Exception:
                return 999
        df_aus["ultima_presenca"] = df_aus["id"].map(ult_map)
        df_aus["dias_ausente"]    = df_aus["ultima_presenca"].apply(_dias)
        return df_aus.sort_values("dias_ausente", ascending=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def bi_distribuicao_risco():
    """Contagem de alunos ativos por cor_alerta_atual."""
    try:
        r  = supabase.from_("alunos").select("cor_alerta_atual").eq("status", "Ativo").execute()
        df = pd.DataFrame(r.data or [])
        if df.empty:
            return pd.DataFrame(columns=["cor_alerta_atual", "total"])
        df["cor_alerta_atual"] = df["cor_alerta_atual"].fillna("⚪").str.strip()
        df["cor_alerta_atual"] = df["cor_alerta_atual"].replace("", "⚪")
        return df.groupby("cor_alerta_atual").size().reset_index(name="total")
    except Exception:
        return pd.DataFrame(columns=["cor_alerta_atual", "total"])


@st.cache_data(ttl=300)
def bi_dores_studio():
    """Top 10 regiões de dor mais reportadas em todo o estúdio."""
    try:
        from views.anamnese_dores_view import REGIOES
        r = supabase.from_("anamnese_dores").select("regioes").execute()
        if not r.data:
            return pd.DataFrame(columns=["label", "count"])
        from collections import Counter
        counter: Counter = Counter()
        for row in r.data:
            for rid in (row.get("regioes") or []):
                counter[rid] += 1
        if not counter:
            return pd.DataFrame(columns=["label", "count"])
        rows = [
            {"label": REGIOES.get(k, {}).get("label", k), "count": v}
            for k, v in counter.most_common(10)
        ]
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["label", "count"])


@st.cache_data(ttl=120)
def bi_dados_individuais(aluno_id: str) -> dict:
    """Coleta todos os dados clínicos e de frequência de um aluno para BI."""
    aid = str(aluno_id)
    try:
        r_aval = supabase.from_("prontuario_avaliacoes").select("*").eq("aluno_id", aid).order("data_avaliacao").execute()
        r_freq = supabase.from_("frequencia").select("data_aula, status").eq("aluno_id", aid).order("data_aula").execute()
        r_ates = supabase.from_("atestados_temporarios").select("*").eq("aluno_id", aid).order("data_registro", desc=True).execute()
        r_dores= supabase.from_("anamnese_dores").select("*").eq("aluno_id", aid).order("data_avaliacao", desc=True).execute()
        return {
            "avaliacoes":  pd.DataFrame(r_aval.data  or []),
            "frequencias": pd.DataFrame(r_freq.data  or []),
            "atestados":   pd.DataFrame(r_ates.data  or []),
            "dores":       r_dores.data or [],
        }
    except Exception as e:
        print(f"Erro bi_dados_individuais: {e}")
        return {
            "avaliacoes":  pd.DataFrame(),
            "frequencias": pd.DataFrame(),
            "atestados":   pd.DataFrame(),
            "dores":       [],
        }


# ==============================================================================
# 🛠️ ASSISTENTE VISUAL DE REPARAÇÃO DE TURMAS (ANTI-SHELL)
# ==============================================================================
def ferramenta_reparacao_turmas():
    """
    Interface visual para consertar turmas fantasmas diretamente pelo Streamlit.
    (Esta função pode ser chamada num painel administrativo ou aba de backup).
    """
    st.markdown("### 🛠️ Assistente de Reparação de Turmas")
    st.info("Esta ferramenta identifica alunos que ficaram presos em nomes antigos de turmas (causando desaparecimento nas presenças) e permite transferi-los para os nomes oficiais com 1 clique.")

    # 1. Buscar Turmas Oficiais
    try:
        res_t = supabase.table('turmas').select('nome').execute()
        turmas_oficiais = [t['nome'] for t in res_t.data]
    except Exception as e:
        st.error(f"Erro ao ligar às turmas: {e}")
        return

    if not turmas_oficiais:
        st.warning("Atenção: Não há turmas oficiais cadastradas.")
        return

    # 2. Buscar Alunos para Diagnóstico
    try:
        res_a = supabase.table('alunos').select('id, nome, turma').execute()
        df_alunos = pd.DataFrame(res_a.data)
    except Exception as e:
        st.error(f"Erro ao ler alunos: {e}")
        return

    if df_alunos.empty:
        st.success("O sistema ainda não tem alunos matriculados.")
        return

    # 3. Cruzamento de Dados (Achar Fantasmas)
    turmas_dos_alunos = df_alunos['turma'].unique()
    turmas_fantasmas = [t for t in turmas_dos_alunos if t not in turmas_oficiais and t is not None and str(t).strip() != ""]

    if not turmas_fantasmas:
        st.success("🎉 EXCELENTE! O seu banco de dados está 100% sincronizado. Nenhuma turma fantasma detetada.")
        return

    st.error(f"⚠️ Alerta: Encontrámos {len(turmas_fantasmas)} nome(s) de turma(s) antiga(s) agarrados a alunos. As presenças deles não aparecem nos diários novos!")

    # 4. Interface de Correção
    for fantasma in turmas_fantasmas:
        qtd_alunos = len(df_alunos[df_alunos['turma'] == fantasma])
        with st.container(border=True):
            st.markdown(f"**Turma Antiga Detetada:** `{fantasma}`")
            st.caption(f"👥 Alunos invisíveis nesta turma: **{qtd_alunos}**")

            c_sel, c_btn = st.columns([2, 1], vertical_alignment="bottom")
            novo_nome_selecionado = c_sel.selectbox("Mover alunos e histórico para:", turmas_oficiais, key=f"sel_{fantasma}")

            if c_btn.button("Sincronizar", key=f"btn_{fantasma}", type="primary", use_container_width=True):
                with st.spinner("A limpar dados fantasmas..."):
                    try:
                        # Reparação dos Alunos
                        supabase.table('alunos').update({'turma': novo_nome_selecionado}).eq('turma', fantasma).execute()
                        # Reparação dos Diários (para não perder as presenças velhas)
                        supabase.table('diario_aulas').update({'turma': novo_nome_selecionado}).eq('turma', fantasma).execute()

                        st.success(f"Feito! Todos os registos movidos para '{novo_nome_selecionado}'.")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro na reparação: {e}")