# ==============================================================================
# 🎨 MÓDULO: Seletor de Tema Dinâmico
# ⚙️ FUNÇÃO: Alternar entre Dark Mode e Light Mode via botão na tela (Injeção CSS)
# ==============================================================================
import streamlit as st

def renderizar_seletor_tema():
    """
    Gera um seletor (dropdown) para alternar o tema da interface dinamicamente.
    Utiliza a memória (session_state) para lembrar a escolha e injeta CSS.
    """
    st.markdown("### 🌗 Preferência de Visualização")

    # 1. Cria a variável na memória do navegador se for o primeiro acesso
    if "tema_operador" not in st.session_state:
        st.session_state.tema_operador = "Escuro" # Define o padrão que você gostou!

    # 2. Cria o seletor na tela
    tema_escolhido = st.selectbox(
        "Escolha o Tema do Sistema:",
        ["Claro", "Escuro"],
        index=0 if st.session_state.tema_operador == "Claro" else 1,
        help="Altera as cores de fundo e texto para maior conforto visual."
    )

    # 3. Se o operador mudar a opção, atualizamos a memória e recarregamos a tela
    if tema_escolhido != st.session_state.tema_operador:
        st.session_state.tema_operador = tema_escolhido
        st.rerun() # Força o Streamlit a recarregar o ecrã com as novas cores

    # 4. Injeção de CSS Dinâmica baseada na escolha
    if st.session_state.tema_operador == "Escuro":
        # CSS para o Modo Escuro (Tons de Grafite/Azul Escuro do Replit)
        css_tema = """
        <style>
            /* Fundo principal e cor da letra global */
            .stApp { background-color: #0E1117 !important; color: #F8FAFC !important; }

            /* Fundo da barra lateral (Sidebar) */
            .stSidebar { background-color: #1E293B !important; }

            /* Fundo dos painéis e bordas dos containers */
            div[data-testid="stVerticalBlockBorderWrapper"] { 
                background-color: #1E293B !important; 
                border-color: #334155 !important; 
            }

            /* Força os textos a ficarem claros */
            p, span, h1, h2, h3, h4, h5, h6, label { color: #F8FAFC !important; }
        </style>
        """
    else:
        # CSS para o Modo Claro (Fundo Branco/Gelo e texto Azul Escuro)
        css_tema = """
        <style>
            .stApp { background-color: #F8FAFC !important; color: #0A2540 !important; }
            .stSidebar { background-color: #FFFFFF !important; }
            div[data-testid="stVerticalBlockBorderWrapper"] { 
                background-color: #FFFFFF !important; 
                border-color: #E2E8F0 !important; 
            }
            p, span, h1, h2, h3, h4, h5, h6, label { color: #0A2540 !important; }
        </style>
        """

    # 5. Aplica a "mágica" escondida no HTML da página
    st.markdown(css_tema, unsafe_allow_html=True)