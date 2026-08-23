"""Tela SuperAdmin para manutenção dos catálogos clínicos."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from utils.catalogos_clinicos_admin import (
    CATEGORIAS_CONDICAO,
    NIVEIS_RESTRICAO,
    CatalogoClinicoAcessoNegado,
    CatalogoClinicoErro,
    alterar_ativo_item_catalogo,
    atualizar_item_catalogo,
    criar_item_catalogo,
    diagnosticar_backend_catalogos_clinicos,
    listar_itens_catalogo,
    reconciliar_auditorias_pendentes,
    validar_acesso_catalogos_clinicos,
)


_CONFIG_TIPOS = {
    "condicoes": {
        "titulo": "Condições clínicas",
        "singular": "condição clínica",
        "plural": "condições clínicas",
        "coluna_categoria": "categoria",
    },
    "restricoes": {
        "titulo": "Restrições de movimento",
        "singular": "restrição de movimento",
        "plural": "restrições de movimento",
        "coluna_categoria": "categoria_movimento",
    },
    "adaptacoes": {
        "titulo": "Adaptações recomendadas",
        "singular": "adaptação recomendada",
        "plural": "adaptações recomendadas",
        "coluna_categoria": "categoria_adaptacao",
    },
}

_ROTULOS_DIAGNOSTICO = (
    ("SUPABASE_URL configurada", "supabase_url_configurada"),
    ("SERVICE_ROLE configurada", "service_role_configurada"),
    ("Sessão autenticada", "sessao_autenticada"),
    ("Perfil SuperAdmin", "perfil_superadmin"),
    ("E-mail ADMIN_MASTER", "email_admin_master"),
    ("Perfil autorizado", "perfil_autorizado"),
    (
        "Cliente administrativo",
        "cliente_administrativo_inicializado",
    ),
)


def _renderizar_diagnostico_backend(diagnostico: dict[str, bool]) -> None:
    cliente_inicializado = diagnostico["cliente_administrativo_inicializado"]
    with st.expander(
        "Diagnóstico seguro do backend",
        expanded=not cliente_inicializado,
    ):
        st.caption(
            "Somente a presença das configurações e o estado da autorização "
            "são exibidos. Nenhum valor ou detalhe técnico é apresentado."
        )
        for rotulo, chave in _ROTULOS_DIAGNOSTICO:
            if chave == "cliente_administrativo_inicializado":
                estado = "inicializado" if diagnostico[chave] else "não inicializado"
            else:
                estado = "sim" if diagnostico[chave] else "não"
            st.write(f"{rotulo}: **{estado}**")


def _formatar_revisao(item: dict[str, Any]) -> str:
    data = str(item.get("revisado_em") or "").replace("T", " ")[:16]
    operador = item.get("revisado_por") or "—"
    return f"{data or '—'} · {operador}"


def _linhas_tabela(tipo: str, itens: list[dict[str, Any]]) -> pd.DataFrame:
    config = _CONFIG_TIPOS[tipo]
    return pd.DataFrame(
        [
            {
                "Código": item.get("codigo", "—"),
                "Nome": item.get("nome_padrao", "—"),
                "Categoria / grupo": (
                    f"{item.get(config['coluna_categoria']) or '—'}"
                    + (
                        f" · {item.get('grupo')}"
                        if tipo == "condicoes" and item.get("grupo")
                        else ""
                    )
                ),
                "Status": "Ativo" if item.get("ativo") else "Inativo",
                "Última revisão": _formatar_revisao(item),
            }
            for item in itens
        ]
    )


def _campos_formulario(tipo: str, existente: dict[str, Any] | None) -> dict[str, Any]:
    prefixo = f"catalogo_{tipo}_{existente['id']}" if existente else f"catalogo_{tipo}_novo"
    valores: dict[str, Any] = {}
    if existente:
        st.text_input(
            "Código",
            value=existente.get("codigo", ""),
            disabled=True,
            key=f"{prefixo}_codigo_fixo",
            help="O código é estável e não pode ser alterado após o cadastro.",
        )
    else:
        valores["codigo"] = st.text_input(
            "Código",
            key=f"{prefixo}_codigo",
            help="Será normalizado em maiúsculas, sem acentos e com sublinhados.",
        )
    valores["nome_padrao"] = st.text_input(
        "Nome",
        value=existente.get("nome_padrao", "") if existente else "",
        key=f"{prefixo}_nome",
    )

    if tipo == "condicoes":
        categoria_atual = existente.get("categoria") if existente else CATEGORIAS_CONDICAO[0]
        indice_categoria = (
            CATEGORIAS_CONDICAO.index(categoria_atual)
            if categoria_atual in CATEGORIAS_CONDICAO
            else 0
        )
        valores["categoria"] = st.selectbox(
            "Categoria",
            CATEGORIAS_CONDICAO,
            index=indice_categoria,
            key=f"{prefixo}_categoria",
        )
        valores["grupo"] = st.text_input(
            "Grupo",
            value=existente.get("grupo", "") if existente else "",
            key=f"{prefixo}_grupo",
        )
        valores["descricao_operacional"] = st.text_area(
            "Descrição operacional",
            value=existente.get("descricao_operacional", "") if existente else "",
            key=f"{prefixo}_descricao",
        )
        valores["exige_revisao_periodica"] = st.checkbox(
            "Exige revisão periódica",
            value=bool(existente.get("exige_revisao_periodica")) if existente else False,
            key=f"{prefixo}_exige_revisao",
        )
        valores["intervalo_revisao_dias"] = st.number_input(
            "Intervalo de revisão (dias)",
            min_value=1,
            value=int(existente.get("intervalo_revisao_dias") or 365)
            if existente
            else 365,
            disabled=not valores["exige_revisao_periodica"],
            key=f"{prefixo}_intervalo",
        )
    elif tipo == "restricoes":
        valores["categoria_movimento"] = st.text_input(
            "Categoria de movimento",
            value=existente.get("categoria_movimento", "") if existente else "",
            key=f"{prefixo}_categoria_movimento",
        )
        valores["descricao_simples_para_aluno"] = st.text_area(
            "Descrição simples para o aluno",
            value=existente.get("descricao_simples_para_aluno", "") if existente else "",
            key=f"{prefixo}_descricao_aluno",
        )
        valores["exige_validacao_clinica"] = st.checkbox(
            "Exige validação clínica",
            value=bool(existente.get("exige_validacao_clinica", True))
            if existente
            else True,
            key=f"{prefixo}_exige_validacao",
        )
        opcoes_nivel = ("",) + NIVEIS_RESTRICAO
        nivel_atual = existente.get("nivel_padrao_sugerido") if existente else ""
        indice_nivel = opcoes_nivel.index(nivel_atual) if nivel_atual in opcoes_nivel else 0
        valores["nivel_padrao_sugerido"] = st.selectbox(
            "Nível padrão sugerido",
            opcoes_nivel,
            index=indice_nivel,
            format_func=lambda valor: valor or "Sem sugestão",
            key=f"{prefixo}_nivel",
        )
    else:
        valores["categoria_adaptacao"] = st.text_input(
            "Categoria de adaptação",
            value=existente.get("categoria_adaptacao", "") if existente else "",
            key=f"{prefixo}_categoria_adaptacao",
        )
        valores["descricao_operacional"] = st.text_area(
            "Descrição operacional",
            value=existente.get("descricao_operacional", "") if existente else "",
            key=f"{prefixo}_descricao_operacional",
        )
        valores["descricao_simples_para_aluno"] = st.text_area(
            "Descrição simples para o aluno",
            value=existente.get("descricao_simples_para_aluno", "") if existente else "",
            key=f"{prefixo}_descricao_aluno",
        )
    return valores


def _executar_mutacao(acao, mensagem: str) -> bool:
    try:
        acao()
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return False
    st.success(mensagem)
    st.rerun()
    return True


def _renderizar_formulario_novo(tipo: str) -> None:
    config = _CONFIG_TIPOS[tipo]
    with st.expander(f"➕ Cadastrar {config['singular']}", expanded=False):
        valores = _campos_formulario(tipo, None)
        if st.button(
            f"Cadastrar {config['singular']}",
            type="primary",
            key=f"catalogo_{tipo}_criar",
        ):
            _executar_mutacao(
                lambda: criar_item_catalogo(tipo, valores),
                f"{config['singular'].capitalize()} cadastrada com sucesso.",
            )


def _renderizar_edicao(tipo: str, itens: list[dict[str, Any]]) -> None:
    if not itens:
        return
    config = _CONFIG_TIPOS[tipo]
    opcoes = {f"{item.get('codigo')} — {item.get('nome_padrao')}": item for item in itens}
    escolha = st.selectbox(
        f"Selecionar {config['singular']} para editar",
        options=tuple(opcoes),
        key=f"catalogo_{tipo}_selecionado",
    )
    item = opcoes[escolha]

    with st.expander(f"Editar {item.get('nome_padrao')}", expanded=False):
        valores = _campos_formulario(tipo, item)
        coluna_salvar, coluna_status = st.columns(2)
        if coluna_salvar.button(
            "Salvar metadados",
            type="primary",
            key=f"catalogo_{tipo}_{item['id']}_salvar",
        ):
            _executar_mutacao(
                lambda: atualizar_item_catalogo(tipo, item["id"], valores),
                "Metadados atualizados com sucesso.",
            )

        novo_status = not bool(item.get("ativo"))
        acao_status = "ativar" if novo_status else "inativar"
        if coluna_status.button(
            f"{'Ativar' if novo_status else 'Inativar'} item",
            key=f"catalogo_{tipo}_{item['id']}_pedir_status",
        ):
            st.session_state[f"catalogo_confirmar_{tipo}_{item['id']}"] = True
            st.rerun()

        confirmacao = f"catalogo_confirmar_{tipo}_{item['id']}"
        if st.session_state.get(confirmacao):
            st.warning(
                f"Confirma {acao_status} **{item.get('nome_padrao')}**? "
                "O item não será excluído permanentemente."
            )
            confirmar, cancelar = st.columns(2)
            if confirmar.button(
                f"Confirmar {acao_status}",
                type="primary",
                key=f"catalogo_{tipo}_{item['id']}_confirmar_status",
            ):
                sucesso = _executar_mutacao(
                    lambda: alterar_ativo_item_catalogo(tipo, item["id"], novo_status),
                    f"Item {acao_status}do com sucesso.",
                )
                if sucesso:
                    st.session_state.pop(confirmacao, None)
            if cancelar.button(
                "Cancelar",
                key=f"catalogo_{tipo}_{item['id']}_cancelar_status",
            ):
                st.session_state.pop(confirmacao, None)
                st.rerun()


def _renderizar_aba(tipo: str) -> None:
    config = _CONFIG_TIPOS[tipo]
    st.subheader(config["titulo"])
    busca_coluna, filtro_coluna = st.columns([3, 1])
    busca = busca_coluna.text_input(
        "Pesquisar por código, nome ou categoria",
        key=f"catalogo_{tipo}_busca",
    )
    status = filtro_coluna.selectbox(
        "Status",
        ("Todos", "Ativos", "Inativos"),
        key=f"catalogo_{tipo}_status",
    )
    try:
        itens = listar_itens_catalogo(tipo, busca, status)
    except CatalogoClinicoErro as exc:
        st.error(str(exc))
        return

    st.caption(f"{len(itens)} {config['plural']} encontrada(s).")
    if itens:
        st.dataframe(_linhas_tabela(tipo, itens), hide_index=True, use_container_width=True)
        _renderizar_edicao(tipo, itens)
    else:
        st.info("Nenhum item corresponde aos filtros informados.")
    _renderizar_formulario_novo(tipo)


def tela_catalogos_clinicos_admin() -> None:
    """Ponto de entrada para a aba Config, com barreira backend explícita."""
    try:
        validar_acesso_catalogos_clinicos()
    except CatalogoClinicoAcessoNegado as exc:
        st.warning(str(exc))
        return

    st.title("Catálogos Clínicos e Segurança")
    st.info(
        "Mudanças nos catálogos não criam automaticamente condições, "
        "restrições, adaptações ou bloqueios para alunos."
    )
    st.caption(
        "Os itens podem ser ativados ou inativados, mas não são excluídos "
        "permanentemente. O código de cada item é imutável após o cadastro."
    )
    diagnostico = diagnosticar_backend_catalogos_clinicos()
    _renderizar_diagnostico_backend(diagnostico)
    if not diagnostico["cliente_administrativo_inicializado"]:
        st.warning(
            "O serviço administrativo de catálogos não está disponível no momento."
        )
        return

    try:
        reconciliacao = reconciliar_auditorias_pendentes()
    except CatalogoClinicoErro as exc:
        st.warning(str(exc))
    else:
        if reconciliacao["pendentes"]:
            st.warning(
                f"Existem {reconciliacao['pendentes']} auditoria(s) pendente(s) "
                "de revisão. Nenhuma pendência foi ocultada."
            )
        elif reconciliacao["reconciliadas"]:
            st.caption(
                f"{reconciliacao['reconciliadas']} auditoria(s) pendente(s) "
                "foram reconciliadas com os valores persistidos."
            )

    aba_condicoes, aba_restricoes, aba_adaptacoes = st.tabs(
        ("Condições clínicas", "Restrições de movimento", "Adaptações recomendadas")
    )
    with aba_condicoes:
        _renderizar_aba("condicoes")
    with aba_restricoes:
        _renderizar_aba("restricoes")
    with aba_adaptacoes:
        _renderizar_aba("adaptacoes")