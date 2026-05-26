# ==============================================================================
# 📄 utils/niver_automatico.py
# ⚙️  Motor de Automação de Aniversários — E-mail + Z-API + Status Parabenizado
# ==============================================================================

import datetime
import urllib.parse
import smtplib
import requests
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ──────────────────────────────────────────────────────────────────────────────
# 1. CONFIG — leitura/gravação via configuracoes_sistema (Supabase)
# ──────────────────────────────────────────────────────────────────────────────
_CHAVES = [
    "niver_emails_destino",      # JSON list de strings
    "niver_email_remetente",     # smtp from
    "niver_email_senha_app",     # senha app Gmail
    "niver_email_habilitado",    # "1" / "0"
    "niver_zapi_instance",       # ex: "1234ABCD"
    "niver_zapi_token",          # token Z-API
    "niver_zapi_client_token",   # client token Z-API
    "niver_zapi_habilitado",     # "1" / "0"
    "niver_zapi_horario",        # "08:00"
    "niver_mensagem_padrao",     # texto com {nome}
    "niver_aviso_dias",          # int: janela de aviso em dias (0 = só hoje)
]


@st.cache_data(ttl=60, show_spinner=False)
def _ler_cfg_niver() -> dict:
    """Lê todas as chaves de aniversário da tabela configuracoes_sistema."""
    from database import supabase
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("chave,valor")
            .in_("chave", _CHAVES)
            .execute()
        )
        return {r["chave"]: r["valor"] for r in (res.data or [])}
    except Exception:
        return {}


def _salvar_cfg_niver(chave: str, valor: str) -> None:
    """Upsert de uma chave de configuração."""
    from database import supabase
    try:
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        _ler_cfg_niver.clear()
    except Exception as e:
        st.error(f"Erro ao salvar config '{chave}': {e}")


def salvar_config_niver(dados: dict) -> None:
    """Salva múltiplas chaves de configuração de aniversários."""
    for chave, valor in dados.items():
        _salvar_cfg_niver(chave, str(valor))


def get_config_niver() -> dict:
    """Retorna configuração atual com defaults."""
    cfg = _ler_cfg_niver()
    return {
        "emails_destino":   _parse_emails(cfg.get("niver_emails_destino", "[]")),
        "email_remetente":  cfg.get("niver_email_remetente", ""),
        "email_senha_app":  cfg.get("niver_email_senha_app", ""),
        "email_habilitado": cfg.get("niver_email_habilitado", "0") == "1",
        "zapi_instance":    cfg.get("niver_zapi_instance", ""),
        "zapi_token":       cfg.get("niver_zapi_token", ""),
        "zapi_client_token":cfg.get("niver_zapi_client_token", ""),
        "zapi_habilitado":  cfg.get("niver_zapi_habilitado", "0") == "1",
        "zapi_horario":     cfg.get("niver_zapi_horario", "08:00"),
        "aviso_dias":       int(cfg.get("niver_aviso_dias", "0") or "0"),
        "mensagem_padrao":  cfg.get(
            "niver_mensagem_padrao",
            "Olá {nome}! 🎂 Feliz Aniversário! O time do Esporte e Saúde deseja a você muita saúde, disposição e muitos anos de vida ativa! 🎉🏃"
        ),
    }


def _parse_emails(raw: str) -> list:
    import json
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [e.strip() for e in val if e.strip()]
    except Exception:
        pass
    # fallback: separados por vírgula
    return [e.strip() for e in raw.split(",") if e.strip()]


# ──────────────────────────────────────────────────────────────────────────────
# 2. STATUS PARABENIZADO — leitura/gravação
# ──────────────────────────────────────────────────────────────────────────────

def _chave_parabenizado(aluno_id: str, ano: int) -> str:
    return f"niver_parab_{aluno_id}_{ano}"


def marcar_parabenizado(aluno_id: str, operador: str = "") -> bool:
    """Marca aluno como parabenizado neste ano. Retorna True se ok."""
    from database import supabase
    ano = datetime.date.today().year
    chave = _chave_parabenizado(aluno_id, ano)
    valor = datetime.datetime.now().isoformat()
    if operador:
        valor += f"|{operador}"
    try:
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": valor}, on_conflict="chave"
        ).execute()
        # limpa cache para refletir imediatamente
        _ler_parabenizados_ano.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao marcar parabenizado: {e}")
        return False


def desmarcar_parabenizado(aluno_id: str) -> bool:
    """Remove o status parabenizado do ano atual."""
    from database import supabase
    ano = datetime.date.today().year
    chave = _chave_parabenizado(aluno_id, ano)
    try:
        supabase.table("configuracoes_sistema").delete().eq("chave", chave).execute()
        _ler_parabenizados_ano.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao desmarcar parabenizado: {e}")
        return False


@st.cache_data(ttl=30, show_spinner=False)
def _ler_parabenizados_ano() -> dict:
    """Retorna {aluno_id: timestamp_str} dos parabenizados no ano atual."""
    from database import supabase
    ano = datetime.date.today().year
    prefixo = f"niver_parab_%_{ano}"
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("chave,valor")
            .like("chave", prefixo)
            .execute()
        )
        result = {}
        for r in (res.data or []):
            # chave = niver_parab_{uuid}_{ano}
            partes = r["chave"].split("_")
            # reconstruir uuid: partes[2] até partes[-2]
            if len(partes) >= 4:
                uid = "_".join(partes[2:-1])
                result[uid] = r["valor"]
        return result
    except Exception:
        return {}


def is_parabenizado(aluno_id: str) -> bool:
    parab = _ler_parabenizados_ano()
    return str(aluno_id) in parab


def get_parabenizados_dict() -> dict:
    return _ler_parabenizados_ano()


# ──────────────────────────────────────────────────────────────────────────────
# 3. LINK WHATSAPP COM MENSAGEM PERSONALIZADA
# ──────────────────────────────────────────────────────────────────────────────

def montar_link_whatsapp(numero: str, mensagem: str) -> str | None:
    """Retorna URL wa.me com texto codificado ou None."""
    from utils.texto import formatar_whatsapp_numero
    num = formatar_whatsapp_numero(numero)
    if not num:
        return None
    texto_enc = urllib.parse.quote(mensagem)
    return f"https://wa.me/{num}?text={texto_enc}"


def personalizar_mensagem(template: str, nome: str) -> str:
    primeiro = nome.strip().split()[0].title() if nome.strip() else nome
    return template.replace("{nome}", primeiro)


# ──────────────────────────────────────────────────────────────────────────────
# 4. DISPARO DE E-MAIL
# ──────────────────────────────────────────────────────────────────────────────

def enviar_email_aniversariantes(df_hoje, cfg: dict | None = None) -> tuple[bool, str]:
    """
    Envia e-mail com lista de aniversariantes para os endereços configurados.
    df_hoje: DataFrame com colunas nome, dia, mes, whatsapp, turma
    Retorna (sucesso, mensagem)
    """
    if cfg is None:
        cfg = get_config_niver()

    emails = cfg["emails_destino"]
    remetente = cfg["email_remetente"]
    senha = cfg["email_senha_app"]

    if not emails:
        return False, "Nenhum e-mail de destino configurado."
    if not remetente or not senha:
        return False, "Remetente ou senha de app não configurados."
    if df_hoje is None or len(df_hoje) == 0:
        return False, "Nenhum aniversariante hoje."

    template = cfg["mensagem_padrao"]
    hoje_str = datetime.date.today().strftime("%d/%m/%Y")

    # Montar HTML dos aniversariantes
    linhas_html = ""
    for _, r in df_hoje.iterrows():
        nome = str(r.get("nome", "")).strip()
        turma = str(r.get("turma", "") or "").strip()
        wap = r.get("whatsapp", "")
        msg_pessoal = personalizar_mensagem(template, nome)
        link = montar_link_whatsapp(str(wap), msg_pessoal) if wap else None

        btn = (
            f'<a href="{link}" style="background:#25D366;color:white;padding:6px 14px;'
            f'border-radius:6px;text-decoration:none;font-size:12px;font-weight:700;">💬 Enviar WhatsApp</a>'
            if link else '<span style="color:#94A3B8;font-size:12px;">Sem WhatsApp</span>'
        )
        linhas_html += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;">
            <strong>{nome.upper()}</strong>
            {f'<br><span style="color:#64748B;font-size:12px;">📍 {turma}</span>' if turma else ''}
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;text-align:center;">
            🎂 {int(r.get('dia',0)):02d}/{int(r.get('mes',0)):02d}
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;text-align:center;">
            {btn}
          </td>
        </tr>"""

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#1E293B;max-width:600px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#0A2540,#1a3a5c);padding:24px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="color:white;margin:0;">🎂 Aniversariantes de Hoje</h2>
        <p style="color:rgba(255,255,255,.7);margin:6px 0 0;font-size:13px;">{hoje_str}</p>
      </div>
      <div style="background:#F8FAFC;padding:20px;border-radius:0 0 12px 12px;border:1px solid #E2E8F0;">
        <p style="color:#475569;font-size:13px;">
          Olá! Seguem os alunos que fazem aniversário <strong>hoje</strong>.
          Clique no botão para abrir o WhatsApp já com a mensagem preparada.
        </p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">
          <thead>
            <tr style="background:#0A2540;">
              <th style="padding:10px 12px;color:white;text-align:left;font-size:12px;">Aluno</th>
              <th style="padding:10px 12px;color:white;text-align:center;font-size:12px;">Data</th>
              <th style="padding:10px 12px;color:white;text-align:center;font-size:12px;">Ação</th>
            </tr>
          </thead>
          <tbody>{linhas_html}</tbody>
        </table>
        <p style="color:#94A3B8;font-size:11px;margin-top:20px;text-align:center;">
          IMBRA · MoveRight · Sistema de Gestão Inteligente
        </p>
      </div>
    </body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎂 {len(df_hoje)} aniversariante(s) hoje — {hoje_str}"
        msg["From"] = remetente
        msg["To"] = ", ".join(emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, emails, msg.as_string())

        return True, f"E-mail enviado para: {', '.join(emails)}"
    except Exception as e:
        return False, f"Erro ao enviar e-mail: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# 5. DISPARO Z-API (WhatsApp automático)
# ──────────────────────────────────────────────────────────────────────────────

def disparar_zapi(numero: str, mensagem: str, cfg: dict) -> tuple[bool, str]:
    """Envia mensagem via Z-API para um número."""
    instance = cfg.get("zapi_instance", "").strip()
    token = cfg.get("zapi_token", "").strip()
    client_token = cfg.get("zapi_client_token", "").strip()

    if not instance or not token:
        return False, "Instância ou token Z-API não configurados."

    from utils.texto import formatar_whatsapp_numero
    num = formatar_whatsapp_numero(numero)
    if not num:
        return False, "Número inválido."

    url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-text"
    headers = {"Content-Type": "application/json"}
    if client_token:
        headers["Client-Token"] = client_token

    payload = {"phone": num, "message": mensagem}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            return True, "Enviado via Z-API"
        return False, f"Z-API retornou {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Erro Z-API: {e}"


def disparar_zapi_aniversariantes(df_hoje, cfg: dict | None = None) -> list[dict]:
    """
    Envia mensagem de aniversário via Z-API para todos de df_hoje.
    Retorna lista de {nome, sucesso, msg}
    """
    if cfg is None:
        cfg = get_config_niver()

    template = cfg["mensagem_padrao"]
    resultados = []
    for _, r in df_hoje.iterrows():
        nome = str(r.get("nome", "")).strip()
        wap = str(r.get("whatsapp", "") or "").strip()
        if not wap:
            resultados.append({"nome": nome, "sucesso": False, "msg": "Sem WhatsApp"})
            continue
        mensagem = personalizar_mensagem(template, nome)
        ok, msg = disparar_zapi(wap, mensagem, cfg)
        resultados.append({"nome": nome, "sucesso": ok, "msg": msg})
    return resultados
