# ==============================================================================
# 📄 MÓDULO 2: db_academico.py (Secretaria)
# ⚙️ Gestão de Turmas, Alunos, Frequência, Inscrições e Assistente de Reparação.
# ==============================================================================

import pandas as pd
import streamlit as st
import datetime
import time
from db_core import supabase, ADMIN_MASTER

# ==============================================================================
# 🏛️ GESTÃO DE TURMAS (Com Auditoria QA)
# ==============================================================================
def get_todas_turmas(ativas_apenas=False):
    try:
        query = supabase.from_("turmas").select("*").order("nome")
        if ativas_apenas: query = query.eq("status", "Ativa")
        return pd.DataFrame(query.execute().data)
    except Exception: return pd.DataFrame()

def get_ocupacao_turmas(limite_padrao=40):
    try:
        res = supabase.from_("alunos").select("turma").neq("status", "Inativo").execute()
        df = pd.DataFrame(res.data)
        contagem = df["turma"].value_counts().to_dict() if not df.empty else {}
        turmas_ativas = [t["nome"] for t in supabase.from_("turmas").select("nome").eq("status", "Ativa").execute().data]
        ocupacao = {}
        for t in turmas_ativas:
            qtd = contagem.get(t, 0)
            vagas = limite_padrao - qtd
            status_cor = "🔴 LOTADA" if vagas <= 0 else ("🟡 ALERTA" if vagas <= 5 else "🟢 LIVRE")
            ocupacao[t] = {"qtd": qtd, "limite": limite_padrao, "vagas": vagas, "status": status_cor}
        return ocupacao
    except Exception: return {}

def adicionar_turma(nome, horario, dias_semana):
    try:
        check = supabase.from_("turmas").select("id").ilike("nome", nome.strip()).execute()
        if check.data: return False, "Já existe uma turma cadastrada com este exato nome."
        supabase.from_("turmas").insert({"nome": nome.strip(), "horario": horario.strip(), "dias_semana": dias_semana.strip(), "status": "Ativa"}).execute()
        return True, "Turma criada com sucesso!"
    except Exception as e: return False, f"Erro: {e}"

def atualizar_turma(turma_id, nome, horario, dias_semana, status):
    """Sincroniza os nomes usando o NOME ANTIGO como âncora."""
    try:
        res_antiga = supabase.from_("turmas").select("nome").eq("id", str(turma_id)).execute()
        nome_antigo = res_antiga.data[0]['nome'] if res_antiga.data else None
        supabase.from_("turmas").update({"nome": nome.strip(), "horario": horario.strip(), "dias_semana": dias_semana.strip(), "status": status}).eq("id", str(turma_id)).execute()
        if nome_antigo:
            supabase.from_("alunos").update({"turma": nome.strip()}).eq("turma", nome_antigo).execute()
            supabase.from_("diario_aulas").update({"turma": nome.strip()}).eq("turma", nome_antigo).execute()
        return True, "Turma atualizada e sincronizada."
    except Exception as e: return False, f"Erro: {e}"

def excluir_turma(turma_id):
    """QA Fix: Verifica ativamente a string do nome da turma nos alunos."""
    try:
        res_t = supabase.from_("turmas").select("nome").eq("id", str(turma_id)).execute()
        if not res_t.data: return False, "Turma não encontrada."
        nome_turma = res_t.data[0]['nome']

        res_a = supabase.from_("alunos").select("id").eq("turma", nome_turma).execute()
        if res_a.data and len(res_a.data) > 0:
            return False, f"Não é possível excluir! Existem {len(res_a.data)} aluno(s) vinculados a esta turma."

        supabase.from_("turmas").delete().eq("id", str(turma_id)).execute()
        return True, "Turma excluída."
    except Exception as e: return False, str(e)

# ==============================================================================
# 🚀 INSCRIÇÕES E MATRÍCULAS
# ==============================================================================
def salvar_pre_cadastro(nome, data_nasc, whatsapp, email):
    try:
        supabase.from_("pre_cadastros").insert({"nome": nome.upper().strip(), "data_nascimento": str(data_nasc) if data_nasc else None, "whatsapp": whatsapp, "email": email, "status": "Pendente"}).execute()
        return True, "Inscrição enviada!"
    except Exception as e: return False, str(e)

def get_pre_cadastros_pendentes():
    try: return supabase.from_("pre_cadastros").select("*").in_("status", ["Pendente", "Lista de Espera"]).execute().data
    except Exception: return []

def aprovar_inscricao_aluno(pre_cadastro_id, turma_selecionada):
    try:
        res_pre = supabase.from_("pre_cadastros").select("*").eq("id", pre_cadastro_id).execute()
        if not res_pre.data: return False, "Não encontrada."
        al = res_pre.data[0]
        novo_aluno = {
            "nome": al.get("nome", "").upper().strip(), "turma": turma_selecionada, "data_nascimento": al.get("data_nascimento"),
            "whatsapp": al.get("whatsapp", ""), "email": al.get("email", ""), "cpf": al.get("cpf", ""), "rg": al.get("rg", ""),
            "endereco": al.get("endereco", ""), "bairro": al.get("bairro", ""), "cep": al.get("cep", ""), "contato_emergencia": al.get("contato_emergencia", ""),
            "problemas_saude": al.get("problemas_saude", ""), "medicamentos": al.get("medicamentos", ""), "restricoes_fisicas": al.get("restricoes_fisicas", ""),
            "url_foto": al.get("url_foto"), "url_rg": al.get("url_rg"), "url_receituario": al.get("url_receituario"), "url_atestado_medico": al.get("url_atestado_medico"), "status": "Ativo",
        }
        supabase.from_("alunos").insert(novo_aluno).execute()
        supabase.from_("pre_cadastros").update({"status": "Aprovado"}).eq("id", pre_cadastro_id).execute()
        return True, f"Aluno matriculado na {turma_selecionada}!"
    except Exception as e: return False, str(e)

def rejeitar_inscricao_aluno(pre_cadastro_id):
    try:
        supabase.from_("pre_cadastros").update({"status": "Rejeitado"}).eq("id", pre_cadastro_id).execute()
        return True, "Arquivada."
    except Exception as e: return False, str(e)

# ==============================================================================
# GESTÃO DE ALUNOS E FREQUÊNCIA
# ==============================================================================
def buscar_alunos_geral(termo="", incluir_inativos=False):
    try:
        query = supabase.from_("alunos").select("*")
        if termo: query = query.ilike("nome", f"%{termo}%")
        if not incluir_inativos: query = query.neq("status", "Inativo")
        return pd.DataFrame(query.order("nome").execute().data)
    except Exception: return pd.DataFrame()

def alterar_status_aluno(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq("id", str(aluno_id)).execute()
        return True, f"Status alterado."
    except Exception as e: return False, str(e)

def get_alunos_por_turma(turma):
    try: return pd.DataFrame(supabase.from_("alunos").select("*").eq("turma", turma).neq("status", "Inativo").order("nome").execute().data)
    except Exception: return pd.DataFrame()

def get_presencas_dia(data_aula, lista_ids):
    if not lista_ids: return {}
    try: return {item["aluno_id"]: (item["status"] == "PRESENTE") for item in supabase.from_("frequencia").select("aluno_id, status").eq("data_aula", str(data_aula)).in_("aluno_id", lista_ids).execute().data}
    except Exception: return {}

def alternar_presenca(aluno_id, data_aula, presente, solicitante_email=""):
    try:
        d_aula = datetime.datetime.strptime(str(data_aula), "%Y-%m-%d").date() if isinstance(data_aula, str) else data_aula
        if (datetime.date.today() - d_aula).days > 10 and solicitante_email != ADMIN_MASTER:
            return False, "Bloqueada. Apenas Mestre."
    except Exception: pass
    status = "PRESENTE" if presente else "FALTA"
    try:
        res = supabase.from_("frequencia").select("id").eq("aluno_id", str(aluno_id)).eq("data_aula", str(data_aula)).execute()
        if res.data: supabase.from_("frequencia").update({"status": status}).eq("id", res.data[0]["id"]).execute()
        else: supabase.from_("frequencia").insert({"aluno_id": str(aluno_id), "data_aula": str(data_aula), "status": status}).execute()
        return True, "Atualizado."
    except Exception as e: return False, str(e)

def get_estatisticas_frequencia_aluno(aluno_id):
    try:
        res = supabase.from_("frequencia").select("status").eq("aluno_id", str(aluno_id)).execute()
        if not res.data: return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}
        total = len(res.data)
        presentes = sum(1 for r in res.data if r["status"] == "PRESENTE")
        return {"total": total, "presentes": presentes, "faltas": total - presentes, "percentual": (presentes / total) * 100 if total > 0 else 0.0}
    except Exception: return {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}

def atualizar_perfil_aluno_dict(aluno_id, dados_atualizados):
    try:
        supabase.from_("alunos").update(dados_atualizados).eq("id", str(aluno_id)).execute()
        return True, "Perfil atualizado no banco de dados."
    except Exception as e: return False, str(e)

def atualizar_perfil_aluno(aluno_id, nome, data_nasc, peso, altura, whats, email, url_foto, url_rg=None, url_rec=None, url_ate=None):
    try:
        dados = {"nome": nome.upper().strip(), "peso": peso, "altura": altura, "whatsapp": whats, "email": email, "url_foto": url_foto, "url_rg": url_rg, "url_receituario": url_rec, "url_atestado_medico": url_ate, "data_nascimento": str(data_nasc) if data_nasc else None}
        supabase.from_("alunos").update(dados).eq("id", str(aluno_id)).execute()
        return True, "Atualizado."
    except Exception as e: return False, str(e)

def atualizar_turma_aluno(aluno_id, nova_turma):
    try:
        supabase.from_("alunos").update({"turma": nova_turma}).eq("id", str(aluno_id)).execute()
        return True
    except: return False

def atualizar_aluno_completo(aluno_id, nome, turma, data_nasc, url_f):
    try:
        supabase.from_("alunos").update({"nome": nome.upper().strip(), "turma": turma, "data_nascimento": str(data_nasc) if data_nasc else None, "url_foto": url_f}).eq("id", str(aluno_id)).execute()
        return True
    except: return False

def cadastrar_novo_aluno(nome, turma, data_nasc=None, peso=0.0, altura=0.0, whats="", email="", url_f=None):
    try:
        supabase.from_("alunos").insert({"nome": nome.upper().strip(), "turma": turma, "data_nascimento": str(data_nasc) if data_nasc else None, "peso": peso, "altura": altura, "whatsapp": whats, "email": email, "url_foto": url_f, "status": "Ativo"}).execute()
        return True
    except: return False

def obter_resumo_aluno(aluno_id):
    try:
        return {"frequencias": len(supabase.from_("frequencia").select("id").eq("aluno_id", str(aluno_id)).execute().data or []), "prontuarios": len(supabase.from_("prontuario_avaliacoes").select("id").eq("aluno_id", str(aluno_id)).execute().data or []), "agendamentos": len(supabase.from_("agendamentos").select("id").eq("aluno_id", str(aluno_id)).execute().data or [])}
    except: return {"frequencias": 0, "prontuarios": 0, "agendamentos": 0}

def excluir_aluno_completo(aluno_id, solicitante_email):
    """QA Fix: Exclusão total em cascata (inclui atestados)."""
    if solicitante_email != ADMIN_MASTER: return False, "⚠️ ACESSO NEGADO."
    try:
        supabase.from_("agendamentos").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("prontuario_avaliacoes").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("frequencia").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("atestados_temporarios").delete().eq("aluno_id", str(aluno_id)).execute()
        supabase.from_("alunos").delete().eq("id", str(aluno_id)).execute()
        return True, "Excluídos."
    except Exception as e: return False, str(e)

def excluir_aluno(aluno_id, solicitante_email):
    """QA Fix: Redireciona para a exclusão completa para não deixar órfãos."""
    return excluir_aluno_completo(aluno_id, solicitante_email)

# ==============================================================================
# 🛠️ ASSISTENTE VISUAL DE REPARAÇÃO DE TURMAS
# ==============================================================================
def ferramenta_reparacao_turmas():
    st.markdown("### 🛠️ Assistente de Reparação de Turmas")
    st.info("Localiza alunos presos em nomes antigos de turmas e corrige a sincronia.")
    try: turmas_oficiais = [t['nome'] for t in supabase.table('turmas').select('nome').execute().data]
    except: return
    if not turmas_oficiais: return

    try: df_alunos = pd.DataFrame(supabase.table('alunos').select('id, nome, turma').execute().data)
    except: return
    if df_alunos.empty: return

    turmas_dos_alunos = df_alunos['turma'].unique()
    turmas_fantasmas = [t for t in turmas_dos_alunos if t not in turmas_oficiais and t is not None and str(t).strip() != ""]

    if not turmas_fantasmas:
        st.success("🎉 EXCELENTE! O seu banco de dados está 100% sincronizado. Nenhuma turma fantasma detetada.")
        return

    st.error(f"⚠️ Encontrámos {len(turmas_fantasmas)} turmas fantasmas!")
    for fantasma in turmas_fantasmas:
        qtd_alunos = len(df_alunos[df_alunos['turma'] == fantasma])
        with st.container(border=True):
            st.markdown(f"**Turma Antiga Detetada:** `{fantasma}`")
            st.caption(f"👥 Alunos invisíveis nesta turma: **{qtd_alunos}**")
            c_sel, c_btn = st.columns([2, 1], vertical_alignment="bottom")
            novo_nome_selecionado = c_sel.selectbox("Mover para:", turmas_oficiais, key=f"sel_{fantasma}")
            if c_btn.button("Sincronizar", key=f"btn_{fantasma}", type="primary", use_container_width=True):
                with st.spinner("A reparar..."):
                    try:
                        supabase.table('alunos').update({'turma': novo_nome_selecionado}).eq('turma', fantasma).execute()
                        supabase.table('diario_aulas').update({'turma': novo_nome_selecionado}).eq('turma', fantasma).execute()
                        st.success("Feito!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(str(e))