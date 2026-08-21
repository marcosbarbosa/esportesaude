import io
import unittest
from unittest.mock import patch

import gerador_pdf
import matplotlib.pyplot as plt

from gerador_pdf import (
    contar_focos_tecnicos_dossie,
    criar_documento_aluno_pdf,
    filtrar_historico_canonico_dossie,
    gerar_grafico_assiduidade_dossie,
    gerar_grafico_evolucao_mensal_dossie,
    gerar_grafico_foco_tecnico_dossie,
    preparar_evolucao_mensal_dossie,
    resumir_assiduidade_dossie,
)


class DossieEvolucaoTests(unittest.TestCase):
    def test_resumo_separa_presenca_falta_e_justificativa(self):
        resumo = resumir_assiduidade_dossie([
            {"data_aula": "2026-04-01", "status": "PRESENTE"},
            {"data_aula": "2026-04-02", "status": "FALTA"},
            {"data_aula": "2026-04-03", "status": "JUSTIFICADA"},
            {"data_aula": "invalida", "status": "PRESENTE"},
            {"data_aula": "2026-04-04", "status": "PENDENTE"},
        ])

        self.assertEqual(resumo["total"], 3)
        self.assertEqual(resumo["presentes"], 1)
        self.assertEqual(resumo["faltas"], 1)
        self.assertEqual(resumo["justificadas"], 1)
        self.assertAlmostEqual(resumo["percentual"], 100 / 3)

    def test_evolucao_e_focos_cobrem_os_cinco_segmentos(self):
        evolucao = preparar_evolucao_mensal_dossie([
            {"data_aula": "2026-04-01", "status": "PRESENTE"},
            {"data_aula": "2026-04-08", "status": "PRESENTE"},
            {"data_aula": "2026-05-02", "status": "PRESENTE"},
            {"data_aula": "2026-05-04", "status": "FALTA"},
        ])
        focos = contar_focos_tecnicos_dossie([
            {
                "exercicios_executados": (
                    "Remada, agachamento, prancha e exercício de equilíbrio"
                ),
                "objetivo_geral": "Ativação da lombar",
                "foco_clinico_social": "",
            }
        ])

        self.assertEqual(evolucao["labels"], ["Abr/26", "Mai/26"])
        self.assertEqual(evolucao["valores"], [2, 1])
        self.assertEqual(set(focos), {"Ombro", "Joelho", "Lombar", "Core", "Coordenacao"})
        self.assertTrue(all(valor == 1 for valor in focos.values()))

    def test_historico_tecnico_respeita_datas_canonicas_de_presenca(self):
        historico = [
            {"data_aula": "2026-04-01", "exercicios_executados": "Prancha"},
            {"data_aula": "2026-04-08", "exercicios_executados": "Agachamento"},
        ]
        serie_canonica = [
            {"data_aula": "2026-04-01", "status": "PRESENTE"},
            {"data_aula": "2026-04-08", "status": "FALTA"},
        ]

        filtrado = filtrar_historico_canonico_dossie(historico, serie_canonica)

        self.assertEqual([aula["data_aula"] for aula in filtrado], ["2026-04-01"])
        self.assertEqual(contar_focos_tecnicos_dossie(filtrado)["Core"], 1)
        self.assertEqual(contar_focos_tecnicos_dossie(filtrado)["Joelho"], 0)

    def test_graficos_retornam_buffers_e_fecham_figuras(self):
        resumo = {
            "presentes": 8, "faltas": 1, "justificadas": 1,
            "percentual": 80.0, "tem_dados": True,
        }
        evolucao = {"labels": ["Abr/26", "Mai/26"], "valores": [4, 5], "tendencia": [4.5, 4.5]}
        focos = {"Ombro": 2, "Joelho": 1, "Lombar": 1, "Core": 3, "Coordenacao": 2}

        for buffer in (
            gerar_grafico_assiduidade_dossie(resumo),
            gerar_grafico_evolucao_mensal_dossie(evolucao),
            gerar_grafico_foco_tecnico_dossie(focos),
        ):
            self.assertIsInstance(buffer, io.BytesIO)
            self.assertGreater(len(buffer.getvalue()), 1000)
            buffer.close()
        self.assertEqual(plt.get_fignums(), [])

    def test_pdf_e_gerado_sem_historico_ou_foto(self):
        aluno = {
            "id": "aluno-teste", "nome": "Maria Teste", "turma": "09H - A",
            "status": "Ativo", "data_nascimento": "1955-06-12",
        }
        with (
            patch("database.get_registros_pa", return_value=[]),
            patch("database.get_atestados_temporarios", return_value=None),
            patch("database.buscar_historico_dores", return_value=[]),
            patch("database.get_frequencia_aluno_serie", return_value=[]),
            patch("gerador_pdf._buscar_temperaturas_historicas", return_value={}),
        ):
            resultado = criar_documento_aluno_pdf(
                aluno, [], [], {"total": 0, "presentes": 0, "faltas": 0, "percentual": 0.0}
            )

        self.assertTrue(resultado.startswith(b"%PDF"))
        self.assertGreater(len(resultado), 10_000)

    def test_pdf_e_gerado_com_status_mistos_e_avaliacoes(self):
        aluno = {
            "id": "aluno-misto", "nome": "Joana Evolução", "turma": "09H - A",
            "status": "Ativo", "data_nascimento": "1953-02-10", "peso": 64, "altura": 1.57,
        }
        serie = [
            {"data_aula": "2026-04-01", "status": "PRESENTE"},
            {"data_aula": "2026-04-08", "status": "FALTA"},
            {"data_aula": "2026-05-01", "status": "JUSTIFICADA"},
            {"data_aula": "2026-05-08", "status": "PRESENTE"},
        ]
        historico = [{
            "data_aula": "2026-05-08",
            "objetivo_geral": "Equilíbrio e coordenação",
            "exercicios_executados": "Remada, agachamento, prancha e equilíbrio",
            "foco_clinico_social": "Core e lombar",
            "relatos_melhora": "Boa adaptação.",
        }]
        avaliacoes = [{"dor_nivel": 2, "escala_borg": 4}, {"dor_nivel": 5}]
        pa = [{"sistolica": 120, "diastolica": 80, "classificacao": "normal", "data": "2026-05-08"}]

        with (
            patch("database.get_registros_pa", return_value=pa),
            patch("database.get_atestados_temporarios", return_value=None),
            patch("database.buscar_historico_dores", return_value=[]),
            patch("database.get_frequencia_aluno_serie", return_value=serie),
            patch("gerador_pdf._buscar_temperaturas_historicas", return_value={}),
        ):
            resultado = criar_documento_aluno_pdf(aluno, avaliacoes, historico, {})

        self.assertTrue(resultado.startswith(b"%PDF"))
        self.assertGreater(len(resultado), 50_000)
        self.assertEqual(plt.get_fignums(), [])

    def test_pdf_mostra_fallback_quando_grafico_falha(self):
        aluno = {"id": "aluno-fallback", "nome": "Lia", "turma": "09H", "status": "Ativo"}
        with (
            patch("database.get_registros_pa", return_value=[]),
            patch("database.get_atestados_temporarios", return_value=None),
            patch("database.buscar_historico_dores", return_value=[]),
            patch("database.get_frequencia_aluno_serie", return_value=[]),
            patch("gerador_pdf.gerar_grafico_assiduidade_dossie", side_effect=RuntimeError("falha simulada")),
            patch(
                "gerador_pdf._desenhar_fallback_grafico",
                wraps=gerador_pdf._desenhar_fallback_grafico,
            ) as fallback,
        ):
            resultado = criar_documento_aluno_pdf(aluno, [], [], {})

        self.assertTrue(resultado.startswith(b"%PDF"))
        fallback.assert_any_call(
            unittest.mock.ANY, 12, unittest.mock.ANY, 88, 63,
            "Assiduidade indisponível", unittest.mock.ANY,
        )

    def test_pdf_inclui_legenda_para_estagio_2(self):
        aluno = {"id": "aluno-pa", "nome": "Paulo", "turma": "09H", "status": "Ativo"}
        pa = [{
            "sistolica": 145,
            "diastolica": 92,
            "classificacao": "estagio2",
            "data": "2026-05-08",
        }]
        with (
            patch("database.get_registros_pa", return_value=pa),
            patch("database.get_atestados_temporarios", return_value=None),
            patch("database.buscar_historico_dores", return_value=[]),
            patch("database.get_frequencia_aluno_serie", return_value=[]),
            patch("gerador_pdf._buscar_temperaturas_historicas", return_value={}),
        ):
            resultado = criar_documento_aluno_pdf(aluno, [], [], {})

        self.assertTrue(resultado.startswith(b"%PDF"))
        self.assertGreater(len(resultado), 10_000)

    def test_dossie_completo_mostra_analise_e_plano_antes_do_historico(self):
        aluno = {
            "id": "aluno-ordem",
            "nome": "Celia",
            "turma": "09H",
            "status": "Ativo",
            "tags_saude": "Artrose/Artrite/Condromalacia",
        }
        serie = [{"data_aula": "2026-05-08", "status": "PRESENTE"}]
        historico = [{
            "data_aula": "2026-05-08",
            "exercicios_executados": "Remada com supervisao",
        }]
        textos = []
        cell_original = gerador_pdf.PDF.cell

        def capturar_texto(pdf, *args, **kwargs):
            texto = args[2] if len(args) >= 3 else kwargs.get("txt", "")
            if isinstance(texto, str):
                textos.append(texto)
            return cell_original(pdf, *args, **kwargs)

        with (
            patch("database.get_registros_pa", return_value=[]),
            patch("database.get_atestados_temporarios", return_value=None),
            patch("database.buscar_historico_dores", return_value=[]),
            patch("database.get_frequencia_aluno_serie", return_value=serie),
            patch("gerador_pdf._buscar_temperaturas_historicas", return_value={}),
            patch.object(gerador_pdf.PDF, "cell", new=capturar_texto),
        ):
            resultado = criar_documento_aluno_pdf(
                aluno, [], historico, {}, incluir_cadastro=True
            )

        self.assertTrue(resultado.startswith(b"%PDF"))
        indice_interesse = next(
            i for i, texto in enumerate(textos)
            if "INTERESSE E DESEJO" in texto
        )
        indice_analise = next(
            i for i, texto in enumerate(textos)
            if "8. Foco Tecnico - Analise Consolidada e Orientacoes" in texto
        )
        indice_plano = next(
            i for i, texto in enumerate(textos)
            if "9. SEU PLANO DE EVOLUÇÃO PARA O PRÓXIMO CICLO" in texto
        )
        indice_dicas = next(
            i for i, texto in enumerate(textos)
            if "RECOMENDACOES / DICAS PARA O PROFESSOR" in texto
        )
        indice_perfil = next(
            i for i, texto in enumerate(textos)
            if "1. Perfil Pessoal" in texto
        )
        self.assertLess(indice_interesse, indice_analise)
        self.assertLess(indice_analise, indice_perfil)
        self.assertLess(indice_plano, indice_dicas)
        self.assertLess(indice_dicas, indice_perfil)

if __name__ == "__main__":
    unittest.main()