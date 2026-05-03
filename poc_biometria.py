# ==============================================================================
# 📄 ARQUIVO: poc_biometria.py
# 🎯 FUNÇÃO: Prova de Conceito - Reconhecimento Facial para Frequência
# ==============================================================================
import streamlit as st
import face_recognition
import numpy as np
from PIL import Image, ImageDraw

st.set_page_config(page_title="PoC Biometria", page_icon="🤖", layout="wide")

st.markdown("""
    <div style='background-color: #F8FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #1E88E5;'>
        <h2 style='color: #0F172A; margin: 0;'>🤖 Motor de Reconhecimento Facial (PoC)</h2>
        <p style='color: #64748B; margin: 0;'>Teste de validação para automatização de frequência do MoveRight.</p>
    </div>
    <br>
""", unsafe_allow_html=True)

# --- COLUNA 1: O "BANCO DE DADOS" ---
c1, c2 = st.columns([1, 2], gap="large")

with c1:
    st.markdown("### 1️⃣ Rostos Conhecidos (Alunos)")
    st.caption("Faça o upload das fotos de perfil individuais. O nome do ficheiro (ex: maria.jpg) será usado como nome do aluno.")

    arquivos_conhecidos = st.file_uploader("Upload Perfis", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

    known_encodings = []
    known_names = []

    if arquivos_conhecidos:
        with st.spinner("A treinar a IA com os rostos..."):
            for file in arquivos_conhecidos:
                try:
                    img = Image.open(file).convert('RGB')
                    img_array = np.array(img)
                    # Extrai o "código matemático" do rosto
                    encodings = face_recognition.face_encodings(img_array)

                    if encodings:
                        known_encodings.append(encodings[0])
                        # Pega o nome do ficheiro sem a extensão
                        nome_aluno = file.name.rsplit('.', 1)[0].upper()
                        known_names.append(nome_aluno)
                        st.success(f"✅ {nome_aluno} registado.")
                    else:
                        st.error(f"❌ Nenhum rosto claro em: {file.name}")
                except Exception as e:
                    st.error(f"Erro a ler {file.name}: {e}")

# --- COLUNA 2: A FOTO DA AULA ---
with c2:
    st.markdown("### 2️⃣ Foto de Grupo (Chamada)")
    st.caption("Faça o upload da foto tirada no final da aula no parque.")

    foto_turma = st.file_uploader("Upload Foto da Aula", type=["jpg", "jpeg", "png"])

    if foto_turma and known_encodings:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 INICIAR VARREDURA FACIAL", use_container_width=True, type="primary"):
            with st.spinner("A analisar a foto de grupo e a procurar alunos... Isso pode demorar uns segundos."):

                # Prepara a imagem de grupo
                img_turma = Image.open(foto_turma).convert('RGB')
                img_turma_array = np.array(img_turma)

                # Encontra TODOS os rostos na foto de grupo
                face_locations = face_recognition.face_locations(img_turma_array)
                face_encodings = face_recognition.face_encodings(img_turma_array, face_locations)

                # Prepara a ferramenta de desenho
                draw = ImageDraw.Draw(img_turma)
                alunos_encontrados = []

                # Compara cada rosto da multidão com o nosso banco de dados
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.55)
                    nome = "Desconhecido"

                    # Se encontrou match, descobre quem é o mais parecido
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            nome = known_names[best_match_index]
                            if nome not in alunos_encontrados:
                                alunos_encontrados.append(nome)

                            # Desenha o quadrado verde e o nome para alunos reconhecidos
                            draw.rectangle(((left, top), (right, bottom)), outline="#10B981", width=4)
                            draw.text((left, bottom + 10), nome, fill="#10B981")
                        else:
                            # Quadrado vermelho para pessoas não cadastradas
                            draw.rectangle(((left, top), (right, bottom)), outline="#EF4444", width=2)

                # Limpeza da ferramenta de desenho
                del draw

                # Exibe o resultado visual
                st.image(img_turma, caption="Resultado do Scanner Facial", use_container_width=True)

                # Exibe o relatório
                st.markdown("---")
                st.markdown(f"### 🎉 Frequência Sugerida ({len(alunos_encontrados)} alunos)")
                for aluno in alunos_encontrados:
                    st.markdown(f"✅ **{aluno}** presente")