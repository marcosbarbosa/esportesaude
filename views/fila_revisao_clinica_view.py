"""Tela SuperAdmin da fila de revisão clínica humana."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from utils.catalogos_clinicos_admin import CatalogoClinicoAcessoNegado, CatalogoClinicoErro
from utils.fila_revisao_clinica import (
    TIPOS_FILA,
    corrigir_item_fila,
    criar_candidato_de_fonte_legada,
    listar_catalogo_ativo,
    listar_fontes_legadas,
    listar_itens_fila,
    obter_detalhe_item_fila,
    obter_texto_fonte_legada,
    reconciliar_auditorias_fila_pendentes,
    revisar_item_fila,
)


_ROTULOS_TIPO = {chave: dados["rotulo"] for chave, dados in TIPOS_FILA.items()}


def _linhas_fila(itens: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Referência protegida": item["referencia_protegida"],
                "Tipo": item["tipo_rotulo"],
                "Status": item["status"],
                "Origem": item["origem"],
                "Sugestão humana": item["sugestao"],
                "Responsável pela revisão": item["responsavel_revisao"],
                "Data da revisão": str(item.get("data_revisao") or "—")[:16].replace(
                    "T", " "
                ),
            }
            for item in itens
        ]
    )


def _executar_mutacao(acao, sucesso: str) -> None:
    try:
        acao()
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return
    st.success(sucesso)
    st.rerun()


def _catalogo_para_tipo(tipo: str) -> dict[str, str]:
    itens = listar_catalogo_ativo(tipo)
    return {
        f"{item.get('codigo') or '—'} — {item.get('nome_padrao') or 'Sem nome'}": str(
            item["id"]
        )
        for item in itens
    }


def _renderizar_detalhe_e_revisao(item: dict[str, Any]) -> None:
    st.markdown("---")
    st.subheader(f"Revisar {item['referencia_protegida']}")
    st.caption(
        "Esta sugestão não é diagnóstico validado. Validar ou rejeitar exige "
        "uma decisão humana registrada em auditoria."
    )
    st.write(f"**Tipo:** {item['tipo_rotulo']}")
    st.write(f"**Sugestão humana:** {item['sugestao']}")
    st.write(f"**Origem:** {item['origem']}")
    with st.expander("Ver contexto e observações protegidos", expanded=False):
        st.caption(
            "O conteúdo abaixo é confidencial, não é exportado e não é usado "
            "para gerar sugestões automáticas."
        )
        st.text(item.get("observacao") or "Nenhuma observação registrada.")

    chave_base = f"fila_revisao_{item['tipo']}_{item['id']}"
    observacao = st.text_area(
        "Observação obrigatória da revisão",
        key=f"{chave_base}_observacao",
        help="Será preservada no vínculo clínico estruturado e na auditoria.",
    )
    coluna_validar, coluna_rejeitar = st.columns(2)
    if coluna_validar.button("Validar item", type="primary", key=f"{chave_base}_validar"):
        st.session_state[f"{chave_base}_confirmar"] = "VALIDADO"
        st.rerun()
    if coluna_rejeitar.button("Rejeitar item", key=f"{chave_base}_rejeitar"):
        st.session_state[f"{chave_base}_confirmar"] = "REJEITADO"
        st.rerun()

    decisao = st.session_state.get(f"{chave_base}_confirmar")
    if decisao:
        acao_rotulo = "validar" if decisao == "VALIDADO" else "rejeitar"
        st.warning(
            f"Confirma {acao_rotulo} esta sugestão? A ação não altera a fonte "
            "legada e deixa uma trilha de auditoria."
        )
        confirmar, cancelar = st.columns(2)
        if confirmar.button(
            f"Confirmar {acao_rotulo}", type="primary", key=f"{chave_base}_confirmar_acao"
        ):
            _executar_mutacao(
                lambda: revisar_item_fila(
                    item["tipo"],
                    item["id"],
                    str(item.get("atualizado_em") or ""),
                    decisao,
                    observacao,
                ),
                f"Item {acao_rotulo}do com sucesso.",
            )
            st.session_state.pop(f"{chave_base}_confirmar", None)
        if cancelar.button("Cancelar", key=f"{chave_base}_cancelar"):
            st.session_state.pop(f"{chave_base}_confirmar", None)
            st.rerun()

    with st.expander("Corrigir sugestão e manter pendente", expanded=False):
        try:
            opcoes = _catalogo_para_tipo(item["tipo"])
        except CatalogoClinicoErro as exc:
            st.error(str(exc))
            return
        if not opcoes:
            st.warning("Não há item ativo disponível neste catálogo.")
            return
        escolha = st.selectbox(
            "Nova seleção humana do catálogo",
            tuple(opcoes),
            key=f"{chave_base}_correcao_catalogo",
        )
        nota_correcao = st.text_area(
            "Observação obrigatória da correção",
            key=f"{chave_base}_correcao_observacao",
        )
        if st.button("Confirmar correção", key=f"{chave_base}_corrigir"):
            _executar_mutacao(
                lambda: corrigir_item_fila(
                    item["tipo"],
                    item["id"],
                    str(item.get("atualizado_em") or ""),
                    opcoes[escolha],
                    nota_correcao,
                ),
                "Sugestão corrigida e mantida como pendente para nova validação.",
            )


def _renderizar_fila() -> None:
    st.subheader("Itens pendentes de revisão humana")
    col_tipo, col_status, col_origem, col_responsavel, col_pagina = st.columns(5)
    tipo_opcao = col_tipo.selectbox(
        "Tipo",
        ("Todos",) + tuple(_ROTULOS_TIPO.values()),
        key="fila_revisao_filtro_tipo",
    )
    status = col_status.selectbox(
        "Status", ("Todos", "PENDENTE", "SUGERIDO_POR_MIGRACAO"), key="fila_revisao_filtro_status"
    )
    origem = col_origem.text_input("Origem", key="fila_revisao_filtro_origem")
    responsavel = col_responsavel.text_input(
        "Responsável", key="fila_revisao_filtro_responsavel"
    )
    pagina = col_pagina.number_input(
        "Página", min_value=1, value=1, step=1, key="fila_revisao_pagina_itens"
    )
    tipo = next(
        (chave for chave, rotulo in _ROTULOS_TIPO.items() if rotulo == tipo_opcao),
        None,
    )
    try:
        itens = listar_itens_fila(
            tipo=tipo,
            status=None if status == "Todos" else status,
            origem=origem or None,
            responsavel=responsavel or None,
            pagina=int(pagina) - 1,
        )
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return
    st.caption(f"{len(itens)} item(ns) na fila. Nenhum dado clínico é exportado por esta tela.")
    if not itens:
        st.info("Nenhum item corresponde aos filtros selecionados.")
        return
    st.dataframe(_linhas_fila(itens), hide_index=True, use_container_width=True)
    opcoes = {
        f"{item['referencia_protegida']} · {item['tipo_rotulo']} · {item['sugestao']}": item
        for item in itens
    }
    escolha = st.selectbox("Selecionar item para revisão", tuple(opcoes), key="fila_revisao_item")
    item_resumo = opcoes[escolha]
    chave_aberto = "fila_revisao_item_aberto"
    if st.button("Abrir item protegido para revisão", key="fila_revisao_abrir_item"):
        st.session_state[chave_aberto] = (item_resumo["tipo"], item_resumo["id"])
        st.rerun()
    if st.session_state.get(chave_aberto) == (
        item_resumo["tipo"],
        item_resumo["id"],
    ):
        try:
            item_detalhado = obter_detalhe_item_fila(
                item_resumo["tipo"], item_resumo["id"]
            )
        except CatalogoClinicoErro as exc:
            st.error(str(exc))
            return
        _renderizar_detalhe_e_revisao(item_detalhado)


def _renderizar_fontes_legadas() -> None:
    st.subheader("Fontes legadas em modo somente leitura")
    st.info(
        "Esta área mostra apenas referências protegidas. O texto legado não é "
        "classificado, não gera sugestões automáticas e não é exportado."
    )
    pagina = st.number_input(
        "Página de fontes", min_value=1, value=1, step=1, key="fila_revisao_pagina_fontes"
    )
    try:
        fontes = listar_fontes_legadas(pagina=int(pagina) - 1)
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return
    if not fontes:
        st.info("Nenhuma fonte legada foi encontrada nesta página.")
        return
    resumo = pd.DataFrame(
        [
            {
                "Referência protegida": fonte["referencia_protegida"],
                "Tipo disponível": _ROTULOS_TIPO[fonte["tipo"]],
                "Campo de origem": fonte["campo_origem"],
            }
            for fonte in fontes
        ]
    )
    st.dataframe(resumo, hide_index=True, use_container_width=True)
    opcoes = {
        f"{fonte['referencia_protegida']} · {_ROTULOS_TIPO[fonte['tipo']]}": fonte
        for fonte in fontes
    }
    escolha = st.selectbox(
        "Selecionar fonte para criar candidato", tuple(opcoes), key="fila_revisao_fonte"
    )
    fonte = opcoes[escolha]
    chave_fonte_aberta = "fila_revisao_fonte_aberta"
    if st.button(
        "Consultar contexto legado protegido",
        key=f"fila_revisao_abrir_fonte_{fonte['aluno_id']}_{fonte['tipo']}",
    ):
        st.session_state[chave_fonte_aberta] = (fonte["tipo"], fonte["aluno_id"])
        st.rerun()
    if st.session_state.get(chave_fonte_aberta) == (
        fonte["tipo"],
        fonte["aluno_id"],
    ):
        try:
            texto_legado = obter_texto_fonte_legada(
                fonte["tipo"], fonte["aluno_id"]
            )
        except CatalogoClinicoErro as exc:
            st.error(str(exc))
            return
        with st.expander("Contexto legado protegido", expanded=True):
            st.caption(
                "A consulta é individual, somente leitura e não representa "
                "diagnóstico, restrição ou adaptação validada."
            )
            st.text(texto_legado)

    st.markdown("#### Criar sugestão humana")
    st.caption(
        "Escolha manualmente o item do catálogo. Nenhum campo é preenchido ou "
        "selecionado automaticamente a partir do texto legado."
    )
    try:
        opcoes_catalogo = _catalogo_para_tipo(fonte["tipo"])
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return
    if not opcoes_catalogo:
        st.warning("Não há item ativo neste catálogo para uma escolha humana.")
        return
    catalogo_escolhido = st.selectbox(
        "Item ativo do catálogo",
        tuple(opcoes_catalogo),
        key=f"fila_revisao_catalogo_{fonte['aluno_id']}_{fonte['tipo']}",
    )
    nivel = "MONITORAR"
    if fonte["tipo"] == "restricao":
        nivel = st.selectbox(
            "Nível de orientação escolhido pelo revisor",
            ("MONITORAR", "EVITAR", "REDUZIR", "ADAPTAR", "SEM_RESTRICAO"),
            key=f"fila_revisao_nivel_{fonte['aluno_id']}",
        )
    observacao = st.text_area(
        "Observação da criação (opcional)",
        key=f"fila_revisao_criar_observacao_{fonte['aluno_id']}_{fonte['tipo']}",
    )
    if st.button(
        "Criar candidato para revisão",
        type="primary",
        key=f"fila_revisao_criar_{fonte['aluno_id']}_{fonte['tipo']}",
    ):
        _executar_mutacao(
            lambda: criar_candidato_de_fonte_legada(
                fonte["tipo"],
                fonte["aluno_id"],
                opcoes_catalogo[catalogo_escolhido],
                observacao,
                nivel,
            ),
            "Candidato criado. Ele permanece pendente até uma validação humana.",
        )


def tela_fila_revisao_clinica() -> None:
    """Ponto de entrada da aba SuperAdmin da fila de revisão clínica."""
    try:
        from utils.catalogos_clinicos_admin import validar_acesso_catalogos_clinicos

        validar_acesso_catalogos_clinicos()
    except CatalogoClinicoAcessoNegado as exc:
        st.warning(str(exc))
        return

    st.title("Fila de Revisão Clínica")
    st.caption(
        "Acesso restrito ao administrador principal. Os dados legados são "
        "consultados somente como contexto e nunca equivalem a diagnóstico validado."
    )
    try:
        reconciliacao = reconciliar_auditorias_fila_pendentes()
    except CatalogoClinicoErro as exc:
        st.warning(str(exc))
    else:
        if reconciliacao["pendentes"]:
            st.warning(
                f"Existem {reconciliacao['pendentes']} auditoria(s) da fila "
                "pendente(s) de conferência. Nenhuma pendência foi ocultada."
            )
        elif reconciliacao["reconciliadas"]:
            st.caption(
                f"{reconciliacao['reconciliadas']} auditoria(s) da fila foram "
                "reconciliadas com os vínculos persistidos."
            )
    aba_fila, aba_fontes = st.tabs(
        ("📋 Fila pendente", "🔎 Fontes legadas protegidas")
    )
    with aba_fila:
        _renderizar_fila()
    with aba_fontes:
        _renderizar_fontes_legadas()