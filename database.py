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


def get_agendamentos_pendentes(limite=8):
    """Retorna os agendamentos pendentes para a dashboard do main.py"""
    try:
        res = (
            supabase.from_("agendamentos")
            .select("*, alunos(nome)")
            .eq("status", "Pendente")
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
                .limit(limite)
                .execute()
            )
            return res.data if res.data else []
        except Exception:
            return []


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
            "peso": blindar_float(pre.get("peso")),
            "altura": blindar_float(pre.get("altura")),
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
# 👨‍🎓 GESTÃO DE ALUNOS E DIÁRIOS
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


def get_diarios_periodo(data_inicio, data_fim, turma=""):
    try:
        query = (
            supabase.from_("diario_aulas")
            .select("*")
            .gte("data_aula", str(data_inicio))
            .lte("data_aula", str(data_fim))
        )
        if turma:
            query = query.eq("turma", turma)
        res = query.order("data_aula").execute()
        return pd.DataFrame(res.data)
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


# ==============================================================================
# ✅ FREQUÊNCIA E RELATÓRIOS (MOTOR ANTI-FURO)
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


def get_relatorio_periodo(data_inicio, data_fim, turma_filtro="Todas"):
    """
    Constrói a matriz cruzando os dias oficiais de aula (Diário) com os alunos.
    Denominador correto: total de aulas registradas no Diário por turma.
    Se não houver registro no dia da aula → FALTA (Motor Anti-Furo).
    """
    try:
        q_al = (
            supabase.table("alunos").select("id, nome, turma").neq("status", "Inativo")
        )
        if turma_filtro and turma_filtro != "Todas":
            q_al = q_al.eq("turma", turma_filtro)
        df_alunos = pd.DataFrame(q_al.execute().data)
        if df_alunos.empty:
            return pd.DataFrame()

        q_fr = (
            supabase.table("frequencia")
            .select("aluno_id, data_aula, status")
            .gte("data_aula", str(data_inicio))
            .lte("data_aula", str(data_fim))
        )
        df_freq = pd.DataFrame(q_fr.execute().data)

        q_diario = (
            supabase.table("diario_aulas")
            .select("turma, data_aula")
            .gte("data_aula", str(data_inicio))
            .lte("data_aula", str(data_fim))
        )
        if turma_filtro and turma_filtro != "Todas":
            q_diario = q_diario.eq("turma", turma_filtro)
        df_diario = pd.DataFrame(q_diario.execute().data)

        if df_diario.empty:
            return pd.DataFrame()

        resultados = []
        for _, aluno in df_alunos.iterrows():
            aluno_id    = aluno["id"]
            turma_aluno = aluno["turma"]

            # Dias reais de aula desta turma no período (fonte: Diário)
            dias_aula_turma = sorted(set(
                df_diario[df_diario["turma"] == turma_aluno]["data_aula"].tolist()
            ))
            total_aulas_turma = len(dias_aula_turma)
            if total_aulas_turma == 0:
                continue  # turma sem diário no período → pula aluno

            linha = {"Nome": aluno["nome"], "Turma": turma_aluno}
            faltas, presencas, justificadas = 0, 0, 0

            for dia in dias_aula_turma:
                dia_str = pd.to_datetime(dia).strftime("%d/%m")

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
        return True, "Salvo!"
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
        r_f = supabase.from_("frequencia").select("status").gte("data_aula", c30).execute()
        df_f = pd.DataFrame(r_f.data or [])
        t_reg = len(df_f)
        pres  = int((df_f["status"] == "PRESENTE").sum()) if not df_f.empty else 0
        taxa  = round(pres / t_reg * 100, 1) if t_reg > 0 else 0.0
    except Exception:
        taxa = 0.0
    try:
        r_f15 = (supabase.from_("frequencia").select("aluno_id")
                 .gte("data_aula", c15).eq("status", "PRESENTE").execute())
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


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
def bi_frequencia_turmas(dias=30):
    try:
        corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
        r_f = (supabase.from_("frequencia").select("aluno_id, status")
               .gte("data_aula", corte).execute())
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


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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
               .gte("data_aula", corte).eq("status", "PRESENTE").execute())
        df_f = pd.DataFrame(r_f.data or [])
        pres_ids = set(df_f["aluno_id"].tolist()) if not df_f.empty else set()
        ausentes = df_al[~df_al["id"].isin(pres_ids)].copy()
        if ausentes.empty:
            return pd.DataFrame()
        # Última presença de todos os tempos
        r_ult = (supabase.from_("frequencia").select("aluno_id, data_aula")
                 .in_("aluno_id", ausentes["id"].tolist())
                 .eq("status", "PRESENTE").execute())
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


# ==============================================================================
# 🔧 FUNÇÕES COMPLEMENTARES (turma, estatísticas, prontuário, CRM, atestados)
# ==============================================================================

def atualizar_turma_aluno(aluno_id, nova_turma):
    try:
        supabase.from_("alunos").update({"turma": nova_turma}).eq("id", str(aluno_id)).execute()
        return True
    except Exception:
        return False


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


def excluir_avaliacao_prontuario(aval_id):
    try:
        supabase.from_("prontuario_avaliacoes").delete().eq("id", aval_id).execute()
        return True, "Excluído."
    except Exception as e:
        return False, str(e)


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


def salvar_atestado_temporario(aluno_id, data_registro, motivo, url_documento):
    try:
        supabase.table("atestados_temporarios").insert({
            "aluno_id": str(aluno_id),
            "data_registro": str(data_registro),
            "motivo": str(motivo).strip(),
            "url_documento": str(url_documento),
        }).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


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
