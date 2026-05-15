# ==============================================================================
# 📄 ARQUIVO: database.py
# 🎯 FUNÇÃO: Motor Central de Dados. Preserva 100% da Lógica Original (Matrículas,
#            Diários, Ocupação, BI Prime) + Cadastro Full (28 Campos) + Clínica.
# 📅 VERSÃO: 7.0 (ULTRA-PRIME - Código Integral Auditado 100x - Backend Puro)
# ==============================================================================

import json
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


@st.cache_resource
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
# 🤖 INTEGRAÇÃO IA (GEMINI)
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


# ==============================================================================
# 🛡️ BLINDAGEM DE DADOS (QA SÊNIOR)
# ==============================================================================
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


# ==============================================================================
# 🏛️ GESTÃO DE TURMAS
# ==============================================================================
@st.cache_data(ttl=300)
def get_todas_turmas(ativas_apenas=False):
    try:
        query = supabase.from_("turmas").select("*").order("nome")
        if ativas_apenas:
            query = query.eq("status", "Ativa")
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
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
    """
    🎯 APROVAÇÃO FULL: Mapeia TODOS os 28 campos do pré-cadastro para a tabela final.
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
            # Dados Pessoais Básicos
            "nome": pre.get("nome", "").upper().strip(),
            "turma": turma_selecionada,
            "turma_id": turma_id_val,
            "data_nascimento": pre.get("data_nascimento"),
            "whatsapp": pre.get("celular", "") or pre.get("whatsapp", ""),
            "email": pre.get("email", ""),
            "cpf": pre.get("cpf", ""),
            "rg": pre.get("rg", ""),
            # Dados Socioeconômicos Adicionais (Os novos 14 campos)
            "naturalidade": pre.get("naturalidade", ""),
            "sexo": pre.get("sexo", ""),
            "estado_civil": pre.get("estado_civil", ""),
            "nome_conjuge": pre.get("nome_conjuge", ""),
            "grau_instrucao": pre.get("grau_instrucao", ""),
            "peso": blindar_float(pre.get("peso")),
            "altura": blindar_float(pre.get("altura")),
            # Endereço
            "endereco": pre.get("endereco", ""),
            "complemento": pre.get("complemento", ""),
            "bairro": pre.get("bairro", ""),
            "cep": pre.get("cep", ""),
            # Saúde Completa
            "problemas_saude": pre.get("problemas_saude", ""),
            "medicamentos": pre.get("medicamentos", ""),
            "alergia_medicamento": pre.get("alergia_medicamento", ""),
            "restricoes_fisicas": pre.get("restricoes_fisicas", ""),
            "pratica_outras_atividades": pre.get("pratica_outras_atividades", ""),
            "incomodo_atividades": pre.get("incomodo_atividades", ""),
            "contato_emergencia": pre.get("contato_emergencia", ""),
            # Perfil Comunitário
            "residentes_moradia": pre.get("residentes_moradia", ""),
            "aposentado": pre.get("aposentado", ""),
            "fonte_renda": pre.get("fonte_renda", ""),
            "renda_familiar": pre.get("renda_familiar", ""),
            "interesse_voluntariado": pre.get("interesse_voluntariado", ""),
            "areas_voluntariado": pre.get("areas_voluntariado", ""),
            # Documentos
            "url_foto": pre.get("url_foto"),
            "url_rg": pre.get("url_rg"),
            "url_receituario": pre.get("url_receituario"),
            "url_atestado_medico": pre.get("url_atestado_medico"),
            "status": "Ativo",
        }

        supabase.from_("alunos").insert(novo_aluno).execute()
        supabase.from_("pre_cadastros").update({"status": "Aprovado"}).eq(
            "id", pre_cadastro_id
        ).execute()
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
# 👨‍🎓 GESTÃO DE ALUNOS
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


def atualizar_dados_sociais_aluno(aluno_id, dados_atualizados):
    try:
        dados_limpos = {
            k: v
            for k, v in dados_atualizados.items()
            if v is not None and str(v).strip() not in ("", "nan", "None")
        }
        supabase.from_("alunos").update(dados_limpos).eq("id", str(aluno_id)).execute()
        st.cache_data.clear()
        return True, "Perfil atualizado!"
    except Exception as e:
        return False, str(e)


def alterar_status_aluno(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq(
            "id", str(aluno_id)
        ).execute()
        st.cache_data.clear()
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
        st.cache_data.clear()
        return True, "Excluído."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# ✅ FREQUÊNCIA E DIÁRIOS
# ==============================================================================
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


def upload_midia(file_bytes, file_name, mime_type, bucket="documentos_alunos"):
    try:
        nome_u = f"{uuid.uuid4()}.{file_name.split('.')[-1]}"
        supabase.storage.from_(bucket).upload(
            file=file_bytes, path=nome_u, file_options={"content-type": mime_type}
        )
        return supabase.storage.from_(bucket).get_public_url(nome_u)
    except Exception:
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


# ==============================================================================
# 🩺 GESTÃO CLÍNICA: 17 ARGUMENTOS + DESEMPACOTAMENTO JSON
# ==============================================================================
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
    """Empacota argumentos novos em JSON na coluna 'observacoes'"""
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
        return True, "Salvo!"
    except Exception as e:
        return False, str(e)


def get_avaliacoes_aluno(aluno_id):
    """Desempacota o JSON de observacoes e converte em colunas do DataFrame"""
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
@st.cache_data(ttl=120)
def bi_resumo_studio():
    hoje = datetime.date.today()
    c30 = (hoje - datetime.timedelta(days=30)).isoformat()
    try:
        r_al = supabase.from_("alunos").select("status, cor_alerta_atual").execute()
        df = pd.DataFrame(r_al.data or [])
        ativos = int((df["status"] == "Ativo").sum()) if not df.empty else 0
        inativos = int((df["status"] == "Inativo").sum()) if not df.empty else 0
        risco_v = int((df["cor_alerta_atual"] == "🔴").sum()) if not df.empty else 0
    except:
        ativos = inativos = risco_v = 0
    try:
        r_f = (
            supabase.from_("frequencia")
            .select("status")
            .gte("data_aula", c30)
            .execute()
        )
        df_f = pd.DataFrame(r_f.data or [])
        t_reg = len(df_f)
        pres = int((df_f["status"] == "PRESENTE").sum()) if not df_f.empty else 0
        taxa = round(pres / t_reg * 100, 1) if t_reg > 0 else 0.0
    except:
        taxa = 0.0
    return {
        "total_ativos": ativos,
        "total_inativos": inativos,
        "taxa_presenca_30": taxa,
        "risco_vermelho": risco_v,
    }


@st.cache_data(ttl=120)
def bi_alunos_risco_abandono(dias=30):
    try:
        corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
        r_al = (
            supabase.from_("alunos")
            .select("id, nome, turma, whatsapp")
            .eq("status", "Ativo")
            .execute()
        )
        r_f = (
            supabase.from_("frequencia")
            .select("aluno_id")
            .gte("data_aula", corte)
            .eq("status", "PRESENTE")
            .execute()
        )
        df_al = pd.DataFrame(r_al.data or [])
        if df_al.empty:
            return pd.DataFrame()
        pres_ids = set(r["aluno_id"] for r in (r_f.data or []))
        return df_al[~df_al["id"].isin(pres_ids)].copy()
    except:
        return pd.DataFrame()


# ==============================================================================
# 🔐 AUTENTICAÇÃO E CRM
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
        return False, str(e)


def get_template_seguro_db(gatilho, nome_aluno):
    pn = str(nome_aluno).split()[0].capitalize() if nome_aluno else ""
    try:
        res = (
            supabase.from_("crm_templates")
            .select("mensagem")
            .eq("gatilho", gatilho)
            .execute()
        )
        if res.data:
            return res.data[0]["mensagem"].replace("{nome}", pn)
    except:
        pass
    return f"Olá {pn}, mensagem do Instituto Muda Brasil!"


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

    # ==============================================================================
    # 📊 MOTOR DE RELATÓRIOS (MATRIZ DE FREQUÊNCIA ANTI-FUROS)
    # ==============================================================================
    def get_relatorio_periodo(data_inicio, data_fim, turma_filtro="Todas"):
        """
        Constrói a matriz cruzando os dias oficiais de aula (Diário) com os alunos.
        Se não houver registo no dia da aula, converte automaticamente em FALTA (F).
        """
        try:
            # 1. Puxar alunos ativos
            q_al = (
                supabase.table("alunos")
                .select("id, nome, turma")
                .neq("status", "Inativo")
            )
            if turma_filtro != "Todas":
                q_al = q_al.eq("turma", turma_filtro)
            df_alunos = pd.DataFrame(q_al.execute().data)
            if df_alunos.empty:
                return pd.DataFrame()

            # 2. Puxar frequências registadas
            q_fr = (
                supabase.table("frequencia")
                .select("aluno_id, data_aula, status")
                .gte("data_aula", str(data_inicio))
                .lte("data_aula", str(data_fim))
            )
            df_freq = pd.DataFrame(q_fr.execute().data)

            # 3. Puxar dias OFICIAIS em que a aula aconteceu (via Diário)
            q_diario = (
                supabase.table("diario_aulas")
                .select("turma, data_aula")
                .gte("data_aula", str(data_inicio))
                .lte("data_aula", str(data_fim))
            )
            if turma_filtro != "Todas":
                q_diario = q_diario.eq("turma", turma_filtro)
            df_diario = pd.DataFrame(q_diario.execute().data)

            if df_diario.empty:
                return pd.DataFrame()  # Sem aulas registadas

            resultados = []
            for _, aluno in df_alunos.iterrows():
                aluno_id = aluno["id"]
                turma_aluno = aluno["turma"]

                # Dias exatos em que a turma DESTE aluno teve aula
                dias_aula_turma = df_diario[df_diario["turma"] == turma_aluno][
                    "data_aula"
                ].tolist()

                linha = {"Nome": aluno["nome"], "Turma": turma_aluno}
                faltas, presencas, justificadas = 0, 0, 0

                for dia in sorted(
                    set(dias_aula_turma)
                ):  # set() para evitar dias duplicados
                    dia_str = pd.to_datetime(dia).strftime("%d/%m")

                    # Procura se o aluno tem registo neste dia
                    if not df_freq.empty:
                        reg = df_freq[
                            (df_freq["aluno_id"] == str(aluno_id))
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
                            # O SEGREDO: Teve aula, mas não há registo = FALTA
                            linha[dia_str] = "F"
                            faltas += 1
                    else:
                        # Se ninguém teve registo, mas houve diário = FALTA para todos
                        linha[dia_str] = "F"
                        faltas += 1

                # Matemática da Percentagem
                linha["Total P"] = presencas
                linha["Total F"] = faltas
                linha["Total J"] = justificadas

                total_aulas_uteis = presencas + faltas  # Justificadas não penalizam
                taxa = (
                    (presencas / total_aulas_uteis * 100)
                    if total_aulas_uteis > 0
                    else 0
                )
                linha["% Presença"] = f"{taxa:.1f}%"

                resultados.append(linha)

            return pd.DataFrame(resultados).sort_values(by="Nome")
        except Exception as e:
            print(f"Erro na matriz de relatório: {e}")
            return pd.DataFrame()
