# ==============================================================================
# 📄 MÓDULO 1: db_core.py (Motor e Infraestrutura)
# ⚙️ Conexão Supabase, IA, SMTP e Autenticação.
# ==============================================================================

import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
import pandas as pd

# 🔐 DEFINIÇÃO DO SUPERUSUÁRIO
ADMIN_MASTER = "marcosbarbosa.am@gmail.com"

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

try:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ia_model = genai.GenerativeModel("gemini-1.5-flash")
    IA_ATIVA = True
except Exception as e:
    IA_ATIVA = False
    print(f"⚠️ IA Desativada. Motivo: {e}")

def revisar_texto_ia(texto):
    """Revisa gramática usando Gemini AI se disponível."""
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
# 🚀 MÓDULO DE AUTENTICAÇÃO DE USUÁRIOS E SMTP
# ==============================================================================
def autenticar_usuario(email, senha):
    try:
        res = supabase.from_("usuarios").select("*").eq("email", email.strip().lower()).eq("senha", senha).execute()
        if res.data: return True, res.data[0]
        return False, "E-mail ou senha incorretos."
    except Exception as e: return False, f"Erro no servidor: {str(e)}"

def cadastrar_usuario_sistema(nome, email, senha):
    try:
        res = supabase.from_("usuarios").select("id").eq("email", email.strip().lower()).execute()
        if res.data: return False, "Este e-mail já está cadastrado no sistema."
        dados = {"nome": nome.strip(), "email": email.strip().lower(), "senha": senha}
        supabase.from_("usuarios").insert(dados).execute()
        return True, "Usuário administrativo criado com sucesso!"
    except Exception as e: return False, f"Erro ao criar utilizador: {str(e)}"

def recuperar_senha_usuario(email_destino):
    try:
        res = supabase.from_("usuarios").select("senha, nome").eq("email", email_destino.strip().lower()).execute()
        if not res.data: return False, "Este e-mail não está cadastrado no Supabase!"
        senha_recuperada, nome_usuario = res.data[0]["senha"], res.data[0]["nome"]
        remetente, senha_app = "marcosbarbosa.am@gmail.com", "bmqzajtkikmuedpo"

        msg = MIMEMultipart()
        msg["From"] = f"Equipe MoveRight <{remetente}>"
        msg["To"] = email_destino.strip()
        msg["Subject"] = "🔐 Recuperação de Senha - MoveRight"
        corpo_email_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #333; background-color: #F8FAFC; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background-color: white; padding: 30px; border-radius: 12px; border-top: 5px solid #1E88E5; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <h2 style="color: #0A2540; margin-top: 0;">Recuperação de Acesso</h2>
        <p style="font-size: 15px;">Olá, <strong>{nome_usuario}</strong>!</p>
        <div style="background-color: #F1F5F9; padding: 15px; text-align: center; font-size: 22px; font-weight: 900; letter-spacing: 3px; border-radius: 8px; border: 1px dashed #CBD5E1; margin: 25px 0; color: #1E88E5;">{senha_recuperada}</div>
        </div></body></html>
        """
        msg.attach(MIMEText(corpo_email_html, "html"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado!"
    except Exception as e: return False, f"Falha no servidor de e-mail. Erro: {str(e)}"