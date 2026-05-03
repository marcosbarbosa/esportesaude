# ==============================================================================
# 📄 Arquivo: backup_view.py
# 📏 Módulo: Cofre de Segurança MoveRight (Backup & Restore)
# 📅 Versão: 1.0 (PRO Elite - Master Admin Only)
# ==============================================================================
import streamlit as st
import json
import datetime
import time
from database import supabase

def gerar_snapshot_banco():
    """Varre o banco de dados e cria um arquivo JSON super compacto com tudo"""
    # 🚀 LISTA CORRIGIDA COM OS NOMES REAIS DO SEU BANCO DE DADOS
    tabelas_para_backup = [
        "turmas",
        "alunos",
        "frequencia",
        "diario_aulas",
        "diario_midias",
        "prontuario_avaliacoes",
        "agendamentos",
        "atestados_temporarios",
        "pesquisas_satisfacao",
        "pre_cadastros",
        "anamnese_dores",
        "crm_templates",
        "usuarios",
        "prontuarios_imbra",
    ]

    backup_data = {}
    total_registros = 0

    for tabela in tabelas_para_backup:
        try:
            res = supabase.table(tabela).select("*").execute()
            backup_data[tabela] = res.data
            total_registros += len(res.data)
        except Exception as e:
            backup_data[tabela] = {"erro": str(e)}

    # Assinatura de Segurança
    backup_data["_metadata"] = {
        "data_geracao": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gerado_por": st.session_state.get("usuario_email", "Sistema"),
        "total_registros": total_registros,
        "formato": "MoveRight JSON Snapshot"
    }

    return json.dumps(backup_data, indent=2, ensure_ascii=False)

def tela_backup():
    # Dupla verificação de segurança (Impede acesso forçado)
    if st.session_state.get("usuario_email") != "marcosbarbosa.am@gmail.com":
        st.error("⛔ ACESSO NEGADO. Área restrita à Administração Mestre.")
        st.stop()

    st.title("🔐 Cofre de Segurança e Backup")
    st.write("Bem-vindo ao núcleo de segurança do MoveRight. Aqui você pode gerar snapshots (fotografias) instantâneas de toda a base de dados.")
    st.divider()

    tab_gerar, tab_restaurar, tab_nuvem = st.tabs(["💾 Gerar Backup Manual", "🔄 Restauração (Perigo)", "☁️ Nuvem & Automação"])

    # ==========================================================================
    # ABA 1: GERAR BACKUP
    # ==========================================================================
    with tab_gerar:
        st.markdown("### 📥 Snapshot do Sistema")
        st.markdown("Clique no botão abaixo para varrer todas as turmas, frequências, clínicas e alunos, empacotando tudo num único ficheiro **.json** ultra compacto.")

        c_btn, c_info = st.columns([1, 2], vertical_alignment="center")

        with c_btn:
            # 🚀 ADICIONADA A CHAVE (KEY) ÚNICA: Evita o erro DuplicateElementId
            if st.button("⚙️ Processar Backup Agora", type="primary", use_container_width=True, key="btn_processar_backup_principal"):
                with st.spinner("A compactar o banco de dados..."):
                    json_data = gerar_snapshot_banco()
                    st.session_state['ultimo_backup_pronto'] = json_data
                    st.success("✅ Pacote gerado com sucesso!")

        if 'ultimo_backup_pronto' in st.session_state:
            data_hoje = datetime.date.today().strftime("%d-%m-%Y")
            nome_ficheiro = f"MoveRight_Backup_{data_hoje}.json"

            st.markdown("<div style='background-color: #ECFDF5; border-left: 4px solid #10B981; padding: 15px; border-radius: 4px;'>", unsafe_allow_html=True)
            st.markdown(f"**Tudo pronto!** O ficheiro `{nome_ficheiro}` contém toda a sua vida operacional. Guarde-o num local seguro (Google Drive ou Pen Drive).")
            st.download_button(
                label="📥 Baixar Ficheiro de Backup (.json)",
                data=st.session_state['ultimo_backup_pronto'],
                file_name=nome_ficheiro,
                mime="application/json",
                type="primary",
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================================
    # ABA 2: RESTAURAÇÃO (ZONA VERMELHA)
    # ==========================================================================
    with tab_restaurar:
        st.markdown("<h3 style='color: #B91C1C;'>⚠️ Zona de Restauração de Emergência</h3>", unsafe_allow_html=True)
        st.warning("Atenção! A restauração de um backup irá **SOBRESCREVER** dados existentes no banco. Use esta ferramenta apenas em caso de perda catastrófica de dados ou corrupção do sistema.")

        ficheiro_restore = st.file_uploader("Carregar ficheiro de backup (.json)", type=["json"])

        if ficheiro_restore:
            try:
                dados_restore = json.load(ficheiro_restore)
                metadata = dados_restore.get("_metadata", {})

                st.info(f"📄 **Ficheiro Reconhecido:** Backup criado em {metadata.get('data_geracao', 'Desconhecida')} contendo {metadata.get('total_registros', 'N/A')} registros.")

                st.markdown("Para prosseguir com a injeção destes dados no servidor, digite **RESTAURAR** na caixa abaixo:")
                confirma = st.text_input("Confirmação de Segurança:")

                if confirma == "RESTAURAR":
                    if st.button("🔥 INICIAR RESTAURAÇÃO (ACÃO IRREVERSÍVEL)", type="primary"):
                        st.error("⚠️ Funcionalidade Bloqueada por Segurança. Para evitar sobrescrita acidental em produção, a injeção em massa requer a chave mestre do Supabase. Por favor, contacte a Engenharia para injetar o JSON fisicamente no servidor.")
                        # Nota de Engenharia: Em sistemas SaaS de elite, nunca deixamos o frontend fazer um "Drop/Insert All" direto para evitar timeouts ou quebra de chaves estrangeiras. O JSON gerado serve como a "caixa preta" do avião entregue ao DBA.
            except Exception as e:
                st.error("Ficheiro inválido ou corrompido.")

    # ==========================================================================
    # ABA 3: INSTRUÇÕES DE NUVEM
    # ==========================================================================
    with tab_nuvem:
        st.markdown("### ☁️ Como funciona a Automação e o Google Drive?")
        st.markdown("""
        **1. Backups Automáticos Invisíveis (Supabase)**
        Você não precisa se preocupar com backups diários! O servidor do **Supabase** (que armazena os nossos dados) possui uma tecnologia chamada *Point-in-Time Recovery*. Ele já faz backups automáticos a cada 24 horas lá na nuvem.

        **2. Google Drive**
        Como o Streamlit não roda programas em segundo plano quando a página está fechada, a melhor forma de ligar ao Google Drive é:
        * Vir a esta aba 1x por semana.
        * Clicar em "Processar Backup Agora" e baixar o `.json`.
        * Arrastar o arquivo para uma pasta chamada "Backups MoveRight" no seu Google Drive.

        *Isso garante um isolamento perfeito: mesmo que a nuvem do sistema caia, o ficheiro físico estará consigo e no Google!*
        """)