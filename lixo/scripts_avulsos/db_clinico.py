# ==============================================================================
# 📄 MÓDULO 3: db_clinico.py (Operação de Campo)
# ⚙️ Mídias, Diários, Prontuários, Agendamentos e CRM.
# ==============================================================================

import pandas as pd
import datetime
import uuid
import re
from db_core import supabase, revisar_texto_ia

# ==============================================================================
# GESTÃO DE MÍDIAS E DIÁRIO
# ==============================================================================
def upload_midia(file_bytes, file_name, mime_type, bucket="diario_midias_imbra"):
    try:
        nome_u = f"{uuid.uuid4()}.{file_name.split('.')[-1]}"
        supabase.storage.from_(bucket).upload(file=file_bytes, path=nome_u, file_options={"content-type": mime_type})
        return supabase.storage.from_(bucket).get_public_url(nome_u)
    except Exception: return None

def get_diario_dia(data, turma):
    try: return supabase.from_("diario_aulas").select("*").eq("data_aula", str(data)).eq("turma", turma).execute().data[0]
    except Exception: return None

def get_diarios_periodo(data_inicio, data_fim, turma):
    try:
        match = re.search(r"(0[789]|1[012])", str(turma))
        hora_busca = match.group(1) if match else str(turma).split(" - ")[0].strip()
        return supabase.from_("diario_aulas").select("*").gte("data_aula", str(data_inicio)).lte("data_aula", str(data_fim)).ilike("turma", f"%{hora_busca}%").order("data_aula").execute().data
    except Exception: return []

def salvar_diario(data, turma, obj, exercicios, url_foto_g, midias, foco_clinico="", relatos=""):
    try:
        dados_diario = {"data_aula": str(data), "turma": turma, "objetivo_geral": obj, "exercicios_executados": exercicios, "url_foto_grupo": url_foto_g, "foco_clinico_social": foco_clinico, "relatos_melhora": relatos}
        res = supabase.from_("diario_aulas").select("id").eq("data_aula", str(data)).eq("turma", turma).execute()
        if res.data: d_id = res.data[0]["id"]; supabase.from_("diario_aulas").update(dados_diario).eq("id", d_id).execute()
        else: d_id = supabase.from_("diario_aulas").insert(dados_diario).execute().data[0]["id"]

        if midias and len(midias) > 0:
            for m in midias: supabase.from_("diario_midias").insert({"diario_aula_id": d_id, "url_midia": m.get("url"), "descricao_objetivo": m.get("descricao"), "tipo": m.get("tipo", "foto")}).execute()
        return True, "Sucesso"
    except Exception as e: return False, str(e)

def get_midias_diario(diario_id):
    try: return supabase.from_("diario_midias").select("*").eq("diario_aula_id", diario_id).execute().data
    except: return []

def excluir_midia_diario(midia_id):
    try: supabase.from_("diario_midias").delete().eq("id", midia_id).execute(); return True
    except: return False

def atualizar_legenda_midia(midia_id, legenda):
    try: supabase.from_("diario_midias").update({"descricao_objetivo": legenda}).eq("id", midia_id).execute(); return True
    except: return False

# ==============================================================================
# 🩺 PRONTUÁRIOS, RELATÓRIOS E AGENDAMENTOS
# ==============================================================================
def salvar_avaliacao_prontuario(aluno_id, peso, altura, dor, tug, sim_d, sim_e, obs="", bristol=None, urina=None, borg=None, aval_id=None):
    try:
        dados = {"aluno_id": str(aluno_id), "data_avaliacao": datetime.date.today().isoformat(), "peso": peso, "altura": altura, "nivel_dor": dor, "tug_segundos": tug, "simetria_dir": sim_d, "simetria_esq": sim_e, "observacoes": revisar_texto_ia(obs) or obs, "bristol": bristol, "urina": urina, "borg": borg}
        if aval_id: supabase.from_("prontuario_avaliacoes").update(dados).eq("id", aval_id).execute()
        else: supabase.from_("prontuario_avaliacoes").insert(dados).execute()
        return True, "Sucesso"
    except Exception as e: return False, str(e)

def get_avaliacoes_aluno(aluno_id):
    try: return pd.DataFrame(supabase.from_("prontuario_avaliacoes").select("*").eq("aluno_id", str(aluno_id)).order("data_avaliacao", desc=True).execute().data or [])
    except: return pd.DataFrame()

def excluir_avaliacao_prontuario(aval_id):
    try: supabase.from_("prontuario_avaliacoes").delete().eq("id", aval_id).execute(); return True, "Excluído."
    except Exception as e: return False, str(e)

def get_relatorio_periodo(di, df, turma_filtro="Ambas"):
    try:
        query = supabase.from_("alunos").select("id, nome, turma, whatsapp").neq("status", "Inativo")
        if turma_filtro and turma_filtro != "Ambas": query = query.eq("turma", turma_filtro)
        df_a = pd.DataFrame(query.execute().data)
        df_f = pd.DataFrame(supabase.from_("frequencia").select("*").gte("data_aula", str(di)).lte("data_aula", str(df)).execute().data)
        return pd.merge(df_f, df_a, left_on="aluno_id", right_on="id") if not df_f.empty else df_a
    except: return pd.DataFrame()

def get_historico_aulas_aluno(aluno_id):
    try:
        turma_aluno = supabase.from_("alunos").select("turma").eq("id", str(aluno_id)).execute().data[0]["turma"]
        datas_presente = [r["data_aula"] for r in supabase.from_("frequencia").select("data_aula").eq("aluno_id", str(aluno_id)).eq("status", "PRESENTE").order("data_aula", desc=True).execute().data]
        match = re.search(r"(0[789]|1[012])", str(turma_aluno))
        hora_busca = match.group(1) if match else str(turma_aluno).split(" - ")[0].strip()
        mapa_diarios = {d["data_aula"]: d for d in supabase.from_("diario_aulas").select("data_aula, objetivo_geral, exercicios_executados, foco_clinico_social, relatos_melhora").ilike("turma", f"%{hora_busca}%").in_("data_aula", datas_presente).execute().data}
        return [{"data_aula": dt, "objetivo_geral": mapa_diarios.get(dt, {}).get("objetivo_geral", "⚠️ Sem diário."), "exercicios_executados": mapa_diarios.get(dt, {}).get("exercicios_executados", ""), "foco_clinico_social": mapa_diarios.get(dt, {}).get("foco_clinico_social", ""), "relatos_melhora": mapa_diarios.get(dt, {}).get("relatos_melhora", "")} for dt in datas_presente]
    except: return []

def get_alunos_atrasados(dias_limite=90):
    try:
        df_alunos = pd.DataFrame(supabase.from_("alunos").select("id, nome, turma, whatsapp").neq("status", "Inativo").execute().data)
        if df_alunos.empty: return []
        df_avals = pd.DataFrame(supabase.from_("prontuario_avaliacoes").select("aluno_id, data_avaliacao").execute().data)
        atrasados = []
        hoje = datetime.date.today()
        for _, aluno in df_alunos.iterrows():
            if not df_avals.empty and aluno["id"] in df_avals["aluno_id"].values:
                try: dias_passados = (hoje - datetime.datetime.strptime(df_avals[df_avals["aluno_id"] == aluno["id"]]["data_avaliacao"].max(), "%Y-%m-%d").date()).days
                except: dias_passados = 0
                if dias_passados >= dias_limite: atrasados.append({"id": aluno["id"], "nome": aluno["nome"], "turma": aluno["turma"], "whatsapp": aluno.get("whatsapp", ""), "dias": dias_passados, "ultima_data": datetime.datetime.strptime(df_avals[df_avals["aluno_id"] == aluno["id"]]["data_avaliacao"].max(), "%Y-%m-%d").date().strftime("%d/%m/%Y"), "status": "Atrasado"})
            else: atrasados.append({"id": aluno["id"], "nome": aluno["nome"], "turma": aluno["turma"], "whatsapp": aluno.get("whatsapp", ""), "dias": 9999, "ultima_data": "Nunca", "status": "Novo"})
        return sorted(atrasados, key=lambda x: x["dias"], reverse=True)
    except: return []

def criar_agendamento(aluno_id, data_agendamento, horario, motivo):
    try: supabase.from_("agendamentos").insert({"aluno_id": aluno_id, "data_agendamento": str(data_agendamento), "horario": str(horario), "motivo": str(motivo), "status": "Pendente"}).execute(); return True, "Sucesso"
    except Exception as e: return False, str(e)

def get_agendamentos_pendentes(limite=None):
    try:
        agora = datetime.datetime.now()
        ativos = []
        for ag in supabase.from_("agendamentos").select("id, data_agendamento, horario, motivo, aluno_id, alunos(nome, turma)").eq("status", "Pendente").gte("data_agendamento", str(datetime.date.today())).order("data_agendamento").order("horario").execute().data:
            try:
                if agora > datetime.datetime.strptime(f"{ag['data_agendamento']} {str(ag['horario'])[:5]}", "%Y-%m-%d %H:%M") + datetime.timedelta(minutes=60): supabase.from_("agendamentos").update({"status": "Concluído"}).eq("id", ag["id"]).execute()
                else: ativos.append(ag)
            except: ativos.append(ag)
        return ativos[:limite] if limite else ativos
    except: return []

def concluir_ou_cancelar_agendamento(agendamento_id, novo_status="Concluído"):
    try: supabase.from_("agendamentos").update({"status": novo_status}).eq("id", agendamento_id).execute(); return True
    except: return False

def verificar_conflito_agendamento(data, horario):
    return supabase.from_("agendamentos").select("id, alunos(nome)").eq("data_agendamento", str(data)).eq("horario", horario).eq("status", "Pendente").execute().data

# ==============================================================================
# CRM E ATESTADOS TEMPORÁRIOS
# ==============================================================================
def get_crm_templates():
    try: return pd.DataFrame(supabase.from_("crm_templates").select("*").order("titulo").execute().data)
    except: return pd.DataFrame()

def atualizar_crm_template(gatilho, nova_mensagem):
    try: supabase.from_("crm_templates").update({"mensagem": nova_mensagem.strip(), "atualizado_em": datetime.datetime.now().isoformat()}).eq("gatilho", gatilho).execute(); return True, "Sucesso"
    except Exception as e: return False, str(e)

def get_template_seguro_db(gatilho, nome_aluno):
    try: msg = supabase.from_("crm_templates").select("mensagem").eq("gatilho", gatilho).execute().data[0]["mensagem"]; return msg.replace("{nome}", str(nome_aluno).split()[0].capitalize() if nome_aluno else "")
    except: return f"Olá {str(nome_aluno).split()[0].capitalize() if nome_aluno else ''}, temos uma mensagem!"

def salvar_atestado_temporario(aluno_id, data_registro, motivo, url_documento):
    try: supabase.table("atestados_temporarios").insert({"aluno_id": str(aluno_id), "data_registro": str(data_registro), "motivo": str(motivo).strip(), "url_documento": str(url_documento)}).execute(); return True, "Sucesso"
    except Exception as e: return False, str(e)

def get_atestados_temporarios(aluno_id):
    try: df = pd.DataFrame(supabase.table("atestados_temporarios").select("*").eq("aluno_id", str(aluno_id)).order("data_registro", desc=True).execute().data); return df if not df.empty else None
    except: return None