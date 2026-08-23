"""Acesso administrativo seguro aos catálogos clínicos.

Este módulo só opera os três catálogos. Ele não lê nem escreve vínculos
clínicos individuais de alunos e mantém o cliente service-role isolado do
cliente padrão do aplicativo.
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
import re
import unicodedata
from typing import Any
import uuid

import streamlit as st
from supabase import Client, create_client


ADMIN_MASTER = "marcosbarbosa.am@gmail.com"

CATEGORIAS_CONDICAO = (
    "CARDIOVASCULAR",
    "MUSCULOESQUELETICA",
    "METABOLICA",
    "NEUROLOGICA",
    "RISCO_FUNCIONAL",
    "OUTRA",
)
NIVEIS_RESTRICAO = ("EVITAR", "REDUZIR", "ADAPTAR", "MONITORAR", "SEM_RESTRICAO")
_CHAVE_CONTROLE_AUDITORIA = "_controle_auditoria_catalogo"
_TAMANHO_PAGINA_AUDITORIA = 1000
_MAXIMO_PAGINAS_AUDITORIA = 100

_CATALOGOS: dict[str, dict[str, Any]] = {
    "condicoes": {
        "tabela": "catalogo_condicoes_clinicas",
        "entidade": "CATALOGO_CONDICAO",
        "rotulo": "condição clínica",
    },
    "restricoes": {
        "tabela": "catalogo_restricoes_movimento",
        "entidade": "CATALOGO_RESTRICAO",
        "rotulo": "restrição de movimento",
    },
    "adaptacoes": {
        "tabela": "catalogo_adaptacoes",
        "entidade": "CATALOGO_ADAPTACAO",
        "rotulo": "adaptação recomendada",
    },
}
_CATALOGOS_POR_ENTIDADE = {
    config["entidade"]: config for config in _CATALOGOS.values()
}


class CatalogoClinicoErro(Exception):
    """Erro seguro para apresentação na interface."""


class CatalogoClinicoAcessoNegado(CatalogoClinicoErro):
    """A sessão atual não pode administrar catálogos clínicos."""


def _email_da_sessao() -> str:
    return (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or st.session_state.get("email")
        or ""
    ).strip().lower()


def validar_acesso_catalogos_clinicos() -> str:
    """Valida a sessão antes de qualquer leitura de secret ou criação de cliente."""
    if (
        st.session_state.get("usuario_logado") is not True
        or st.session_state.get("perfil") != "SuperAdmin"
    ):
        raise CatalogoClinicoAcessoNegado(
            "Esta área é restrita ao administrador principal do sistema."
        )

    operador = _email_da_sessao()
    if operador != ADMIN_MASTER.lower():
        raise CatalogoClinicoAcessoNegado(
            "Esta área é restrita ao administrador principal do sistema."
        )
    return operador


def _valor_configuracao_backend(nome: str) -> str:
    """Lê uma configuração de servidor sem expor seu valor."""
    try:
        valor = st.secrets.get(nome)
    except Exception:
        valor = None
    if valor:
        return str(valor).strip()
    return os.environ.get(nome, "").strip()


def _credenciais_administrativas() -> tuple[str, str]:
    """Obtém as credenciais após a autorização feita pelo chamador."""
    return (
        _valor_configuracao_backend("SUPABASE_URL"),
        _valor_configuracao_backend("SUPABASE_SERVICE_ROLE_KEY"),
    )


@st.cache_resource(show_spinner=False)
def _criar_cliente_administrativo(url: str, service_role_key: str) -> Client:
    """Cria o cliente privilegiado exclusivamente no processo Streamlit."""
    return create_client(url, service_role_key)


def _cliente_administrativo() -> Client:
    """Obtém o cliente privilegiado somente após validar a sessão no backend."""
    validar_acesso_catalogos_clinicos()
    try:
        url, service_role_key = _credenciais_administrativas()
    except Exception as exc:
        raise CatalogoClinicoErro(
            "O serviço administrativo de catálogos não está disponível no momento."
        ) from exc

    if not url or not service_role_key:
        raise CatalogoClinicoErro(
            "O serviço administrativo de catálogos não está disponível no momento."
        )
    try:
        return _criar_cliente_administrativo(url, service_role_key)
    except Exception as exc:
        raise CatalogoClinicoErro(
            "O serviço administrativo de catálogos não está disponível no momento."
        ) from exc


def diagnosticar_backend_catalogos_clinicos() -> dict[str, bool]:
    """Retorna somente estados seguros, sem valores ou detalhes de exceção."""
    sessao_autenticada = st.session_state.get("usuario_logado") is True
    perfil_superadmin = st.session_state.get("perfil") == "SuperAdmin"
    email_admin_master = _email_da_sessao() == ADMIN_MASTER.lower()
    perfil_autorizado = (
        sessao_autenticada and perfil_superadmin and email_admin_master
    )
    diagnostico = {
        "supabase_url_configurada": False,
        "service_role_configurada": False,
        "sessao_autenticada": sessao_autenticada,
        "perfil_superadmin": perfil_superadmin,
        "email_admin_master": email_admin_master,
        "perfil_autorizado": perfil_autorizado,
        "cliente_administrativo_inicializado": False,
    }
    if not perfil_autorizado:
        return diagnostico

    try:
        url, service_role_key = _credenciais_administrativas()
    except Exception:
        return diagnostico
    diagnostico["supabase_url_configurada"] = bool(url)
    diagnostico["service_role_configurada"] = bool(service_role_key)
    if not url or not service_role_key:
        return diagnostico

    try:
        _cliente_administrativo()
    except Exception:
        return diagnostico
    diagnostico["cliente_administrativo_inicializado"] = True
    return diagnostico


def _config_catalogo(tipo: str) -> dict[str, Any]:
    config = _CATALOGOS.get(tipo)
    if not config:
        raise CatalogoClinicoErro("Tipo de catálogo inválido.")
    return config


def _texto_obrigatorio(valor: Any, campo: str) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise CatalogoClinicoErro(f"Informe {campo}.")
    return texto


def normalizar_codigo(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").upper().strip()
    codigo = re.sub(r"[^A-Z0-9]+", "_", texto).strip("_")
    if not codigo:
        raise CatalogoClinicoErro("Informe um código válido.")
    if len(codigo) > 80:
        raise CatalogoClinicoErro("O código deve ter no máximo 80 caracteres.")
    return codigo


def _texto_opcional(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _inteiro_positivo(valor: Any, campo: str) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError) as exc:
        raise CatalogoClinicoErro(f"Informe {campo} como número inteiro positivo.") from exc
    if numero <= 0:
        raise CatalogoClinicoErro(f"Informe {campo} como número inteiro positivo.")
    return numero


def _validar_payload(tipo: str, valores: dict[str, Any], incluir_codigo: bool) -> dict[str, Any]:
    _config_catalogo(tipo)
    payload: dict[str, Any] = {
        "nome_padrao": _texto_obrigatorio(valores.get("nome_padrao"), "o nome"),
    }
    if incluir_codigo:
        payload["codigo"] = normalizar_codigo(valores.get("codigo"))

    if tipo == "condicoes":
        categoria = _texto_obrigatorio(valores.get("categoria"), "a categoria").upper()
        if categoria not in CATEGORIAS_CONDICAO:
            raise CatalogoClinicoErro("Selecione uma categoria clínica válida.")
        exige_revisao = bool(valores.get("exige_revisao_periodica", False))
        payload.update(
            {
                "categoria": categoria,
                "grupo": _texto_obrigatorio(valores.get("grupo"), "o grupo"),
                "descricao_operacional": _texto_opcional(
                    valores.get("descricao_operacional")
                ),
                "exige_revisao_periodica": exige_revisao,
                "intervalo_revisao_dias": (
                    _inteiro_positivo(
                        valores.get("intervalo_revisao_dias"),
                        "o intervalo de revisão",
                    )
                    if exige_revisao
                    else None
                ),
            }
        )
    elif tipo == "restricoes":
        nivel = _texto_opcional(valores.get("nivel_padrao_sugerido"))
        if nivel:
            nivel = nivel.upper()
            if nivel not in NIVEIS_RESTRICAO:
                raise CatalogoClinicoErro("Selecione um nível sugerido válido.")
        payload.update(
            {
                "categoria_movimento": _texto_opcional(
                    valores.get("categoria_movimento")
                ),
                "descricao_simples_para_aluno": _texto_opcional(
                    valores.get("descricao_simples_para_aluno")
                ),
                "exige_validacao_clinica": bool(
                    valores.get("exige_validacao_clinica", True)
                ),
                "nivel_padrao_sugerido": nivel,
            }
        )
    else:
        payload.update(
            {
                "categoria_adaptacao": _texto_opcional(
                    valores.get("categoria_adaptacao")
                ),
                "descricao_operacional": _texto_opcional(
                    valores.get("descricao_operacional")
                ),
                "descricao_simples_para_aluno": _texto_opcional(
                    valores.get("descricao_simples_para_aluno")
                ),
            }
        )
    return payload


def _com_controle_auditoria(valor: dict[str, Any], status: str) -> dict[str, Any]:
    resultado = dict(valor)
    resultado[_CHAVE_CONTROLE_AUDITORIA] = {
        "status": status,
        "registrado_em": datetime.now(UTC).isoformat(),
    }
    return resultado


def _reservar_auditoria(
    cliente: Client,
    entidade: str,
    registro_id: str,
    acao: str,
    operador: str,
    anterior: dict[str, Any] | None,
    novo_previsto: dict[str, Any],
) -> str:
    """Cria uma reserva durável antes da mutação do catálogo."""
    resposta = (
        cliente.table("historico_revisoes_clinicas")
        .insert(
            {
                "entidade": entidade,
                "registro_id": registro_id,
                "acao": acao,
                "valor_anterior": anterior,
                "valor_novo": _com_controle_auditoria(novo_previsto, "PENDENTE"),
                "operador": operador,
            }
        )
        .execute()
    )
    auditoria = (resposta.data or [None])[0]
    if not auditoria or not auditoria.get("id"):
        raise CatalogoClinicoErro(
            "A alteração não foi realizada porque a auditoria não pôde ser iniciada."
        )
    return str(auditoria["id"])


def _finalizar_auditoria(
    cliente: Client,
    auditoria_id: str,
    valor_novo: dict[str, Any],
    status: str,
) -> None:
    resposta = (
        cliente.table("historico_revisoes_clinicas")
        .update({"valor_novo": _com_controle_auditoria(valor_novo, status)})
        .eq("id", auditoria_id)
        .execute()
    )
    if not resposta.data:
        raise CatalogoClinicoErro(
            "A alteração foi registrada com auditoria pendente de reconciliação."
        )


def _marcar_auditoria_sem_mutacao(
    cliente: Client,
    auditoria_id: str,
    valor_previsto: dict[str, Any],
    status: str,
) -> None:
    """Tenta classificar a reserva; se falhar, ela permanece PENDENTE."""
    try:
        _finalizar_auditoria(cliente, auditoria_id, valor_previsto, status)
    except Exception:
        pass


def _valor_sem_controle_auditoria(valor: Any) -> dict[str, Any]:
    resultado = dict(valor) if isinstance(valor, dict) else {}
    resultado.pop(_CHAVE_CONTROLE_AUDITORIA, None)
    return resultado


def _normalizar_valor_comparacao(valor: Any) -> Any:
    if isinstance(valor, str) and ("T" in valor or "+" in valor):
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return valor
    return valor


def _corresponde_ao_previsto(
    previsto: dict[str, Any], observado: dict[str, Any] | None
) -> bool:
    if not observado:
        return False
    ignorar = {"criado_em", "atualizado_em"}
    return all(
        _normalizar_valor_comparacao(observado.get(campo))
        == _normalizar_valor_comparacao(valor)
        for campo, valor in previsto.items()
        if campo not in ignorar
    )


def _chave_ordem_auditoria(historico: dict[str, Any]) -> tuple[datetime, str]:
    criado_em = str(historico.get("criado_em") or "")
    try:
        data = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
    except ValueError:
        data = datetime.min.replace(tzinfo=UTC)
    return data, str(historico.get("id") or "")


def _auditoria_posterior_confiavel(
    candidata: dict[str, Any], pendente: dict[str, Any]
) -> bool:
    controle = (
        candidata.get("valor_novo", {}).get(_CHAVE_CONTROLE_AUDITORIA, {})
        if isinstance(candidata.get("valor_novo"), dict)
        else {}
    )
    return (
        _chave_ordem_auditoria(candidata) > _chave_ordem_auditoria(pendente)
        and controle.get("status") in {"CONCLUIDA", "CONCLUIDA_RECONCILIADA"}
    )


def reconciliar_auditorias_pendentes() -> dict[str, int]:
    """Reconcilia reservas pendentes com valores efetivamente persistidos.

    A rotina é executada ao abrir a área administrativa. Casos ambíguos
    permanecem PENDENTES e são informados na interface, nunca ocultados.
    """
    cliente = _cliente_administrativo()
    try:
        historicos: list[dict[str, Any]] = []
        cursor_criado_em: str | None = None
        cursor_id: str | None = None
        for _pagina_numero in range(_MAXIMO_PAGINAS_AUDITORIA):
            consulta = (
                cliente.table("historico_revisoes_clinicas")
                .select("*")
                .in_("entidade", tuple(_CATALOGOS_POR_ENTIDADE))
                .order("criado_em", desc=True)
                .order("id", desc=True)
                .limit(_TAMANHO_PAGINA_AUDITORIA)
            )
            if cursor_criado_em is not None and cursor_id is not None:
                consulta = consulta.or_(
                    f"criado_em.lt.{cursor_criado_em},"
                    f"and(criado_em.eq.{cursor_criado_em},id.lt.{cursor_id})"
                )
            resposta = consulta.execute()
            pagina = list(resposta.data or [])
            historicos.extend(pagina)
            if len(pagina) < _TAMANHO_PAGINA_AUDITORIA:
                break
            ultimo = pagina[-1]
            cursor_criado_em = str(ultimo.get("criado_em") or "")
            cursor_id = str(ultimo.get("id") or "")
            if not cursor_criado_em or not cursor_id:
                raise CatalogoClinicoErro(
                    "Uma auditoria não possui cursor válido. "
                    "A contagem não foi apresentada parcialmente."
                )
        else:
            raise CatalogoClinicoErro(
                "O volume de auditorias excedeu o limite de conferência. "
                "A contagem não foi apresentada parcialmente."
            )
    except CatalogoClinicoErro:
        raise
    except Exception as exc:
        raise _falha_supabase("verificar as auditorias pendentes", exc) from exc

    pendentes = [
        historico
        for historico in historicos
        if (
            isinstance(historico.get("valor_novo"), dict)
            and historico["valor_novo"]
            .get(_CHAVE_CONTROLE_AUDITORIA, {})
            .get("status")
            == "PENDENTE"
        )
    ]
    reconciliadas = 0
    ainda_pendentes = 0

    for pendente in pendentes:
        config = _CATALOGOS_POR_ENTIDADE.get(pendente.get("entidade"))
        registro_id = pendente.get("registro_id")
        auditoria_id = pendente.get("id")
        if not config or not registro_id or not auditoria_id:
            ainda_pendentes += 1
            continue

        previsto = _valor_sem_controle_auditoria(pendente.get("valor_novo"))
        try:
            atual_resposta = (
                cliente.table(config["tabela"])
                .select("*")
                .eq("id", registro_id)
                .limit(1)
                .execute()
            )
            atual = (atual_resposta.data or [None])[0]
        except Exception:
            ainda_pendentes += 1
            continue

        valor_efetivo = atual if _corresponde_ao_previsto(previsto, atual) else None
        if valor_efetivo is None:
            for historico_posterior in historicos:
                if (
                    historico_posterior.get("registro_id") == registro_id
                    and historico_posterior.get("id") != auditoria_id
                    and _auditoria_posterior_confiavel(
                        historico_posterior, pendente
                    )
                    and _corresponde_ao_previsto(
                        previsto, historico_posterior.get("valor_anterior")
                    )
                ):
                    valor_efetivo = historico_posterior.get("valor_anterior")
                    break

        if valor_efetivo is not None:
            try:
                _finalizar_auditoria(
                    cliente,
                    str(auditoria_id),
                    valor_efetivo,
                    "CONCLUIDA_RECONCILIADA",
                )
                reconciliadas += 1
            except Exception:
                ainda_pendentes += 1
        elif pendente.get("acao") == "CRIACAO" and atual is None:
            try:
                _finalizar_auditoria(
                    cliente,
                    str(auditoria_id),
                    previsto,
                    "FALHA_SEM_MUTACAO_RECONCILIADA",
                )
                reconciliadas += 1
            except Exception:
                ainda_pendentes += 1
        else:
            ainda_pendentes += 1

    return {
        "encontradas": len(pendentes),
        "reconciliadas": reconciliadas,
        "pendentes": ainda_pendentes,
    }


def _falha_supabase(acao: str, exc: Exception) -> CatalogoClinicoErro:
    """Não propaga URL, headers, chaves ou mensagens brutas do fornecedor."""
    return CatalogoClinicoErro(f"Não foi possível {acao}. Tente novamente.")


def listar_itens_catalogo(tipo: str, busca: str = "", status: str = "Todos") -> list[dict[str, Any]]:
    """Lista somente um dos três catálogos administrativos."""
    config = _config_catalogo(tipo)
    cliente = _cliente_administrativo()
    try:
        resposta = (
            cliente.table(config["tabela"])
            .select("*")
            .order("ativo", desc=True)
            .order("nome_padrao")
            .execute()
        )
    except Exception as exc:
        raise _falha_supabase("carregar os itens do catálogo", exc) from exc

    itens = list(resposta.data or [])
    termo = str(busca or "").strip().casefold()
    if status == "Ativos":
        itens = [item for item in itens if item.get("ativo") is True]
    elif status == "Inativos":
        itens = [item for item in itens if item.get("ativo") is False]
    if termo:
        campos = ("codigo", "nome_padrao", "categoria", "grupo", "categoria_movimento", "categoria_adaptacao")
        itens = [
            item
            for item in itens
            if any(termo in str(item.get(campo) or "").casefold() for campo in campos)
        ]
    return itens


def criar_item_catalogo(tipo: str, valores: dict[str, Any]) -> dict[str, Any]:
    """Cria um item de catálogo e registra a auditoria correspondente."""
    config = _config_catalogo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    registro_id = str(uuid.uuid4())
    payload = {"id": registro_id, **_validar_payload(tipo, valores, incluir_codigo=True)}
    payload.update(
        {
            "ativo": True,
            "revisado_por": operador,
            "revisado_em": datetime.now(UTC).isoformat(),
        }
    )
    try:
        auditoria_id = _reservar_auditoria(
            cliente,
            config["entidade"],
            registro_id,
            "CRIACAO",
            operador,
            None,
            payload,
        )
    except CatalogoClinicoErro:
        raise
    except Exception as exc:
        raise _falha_supabase("iniciar a auditoria da alteração", exc) from exc

    try:
        resposta = cliente.table(config["tabela"]).insert(payload).execute()
        item = (resposta.data or [None])[0]
        if not item:
            raise CatalogoClinicoErro("Não foi possível cadastrar o item.")
        _finalizar_auditoria(cliente, auditoria_id, item, "CONCLUIDA")
        return item
    except CatalogoClinicoErro as exc:
        if "auditoria pendente" not in str(exc).lower():
            _marcar_auditoria_sem_mutacao(
                cliente, auditoria_id, payload, "FALHA_SEM_MUTACAO"
            )
        raise
    except Exception as exc:
        _marcar_auditoria_sem_mutacao(
            cliente, auditoria_id, payload, "FALHA_SEM_MUTACAO"
        )
        raise _falha_supabase(f"cadastrar a {config['rotulo']}", exc) from exc


def atualizar_item_catalogo(
    tipo: str, item_id: str, valores: dict[str, Any]
) -> dict[str, Any]:
    """Atualiza apenas metadados seguros; o código permanece imutável."""
    config = _config_catalogo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    try:
        anterior_resposta = (
            cliente.table(config["tabela"]).select("*").eq("id", item_id).limit(1).execute()
        )
        anterior = (anterior_resposta.data or [None])[0]
        if not anterior:
            raise CatalogoClinicoErro("Item de catálogo não encontrado.")

        payload = _validar_payload(tipo, valores, incluir_codigo=False)
        payload.update(
            {
                "revisado_por": operador,
                "revisado_em": datetime.now(UTC).isoformat(),
            }
        )
        previsto = {**anterior, **payload}
        auditoria_id = _reservar_auditoria(
            cliente,
            config["entidade"],
            item_id,
            "ATUALIZACAO",
            operador,
            anterior,
            previsto,
        )
        consulta = cliente.table(config["tabela"]).update(payload).eq("id", item_id)
        if anterior.get("atualizado_em"):
            consulta = consulta.eq("atualizado_em", anterior["atualizado_em"])
        resposta = consulta.execute()
        item = (resposta.data or [None])[0]
        if not item:
            _marcar_auditoria_sem_mutacao(
                cliente, auditoria_id, previsto, "CANCELADA_POR_CONFLITO"
            )
            raise CatalogoClinicoErro(
                "O item foi alterado por outra sessão. Recarregue antes de salvar."
            )
        _finalizar_auditoria(cliente, auditoria_id, item, "CONCLUIDA")
        return item
    except CatalogoClinicoErro:
        raise
    except Exception as exc:
        raise _falha_supabase(f"atualizar a {config['rotulo']}", exc) from exc


def alterar_ativo_item_catalogo(tipo: str, item_id: str, ativar: bool) -> dict[str, Any]:
    """Ativa ou inativa sem exclusão física."""
    config = _config_catalogo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    try:
        anterior_resposta = (
            cliente.table(config["tabela"]).select("*").eq("id", item_id).limit(1).execute()
        )
        anterior = (anterior_resposta.data or [None])[0]
        if not anterior:
            raise CatalogoClinicoErro("Item de catálogo não encontrado.")

        novo_status = bool(ativar)
        if anterior.get("ativo") is novo_status:
            return anterior
        payload = {
            "ativo": novo_status,
            "revisado_por": operador,
            "revisado_em": datetime.now(UTC).isoformat(),
        }
        previsto = {**anterior, **payload}
        auditoria_id = _reservar_auditoria(
            cliente,
            config["entidade"],
            item_id,
            "ATIVACAO" if novo_status else "INATIVACAO",
            operador,
            anterior,
            previsto,
        )
        consulta = cliente.table(config["tabela"]).update(payload).eq("id", item_id)
        if anterior.get("atualizado_em"):
            consulta = consulta.eq("atualizado_em", anterior["atualizado_em"])
        resposta = consulta.execute()
        item = (resposta.data or [None])[0]
        if not item:
            _marcar_auditoria_sem_mutacao(
                cliente, auditoria_id, previsto, "CANCELADA_POR_CONFLITO"
            )
            raise CatalogoClinicoErro(
                "O item foi alterado por outra sessão. Recarregue antes de mudar o status."
            )
        _finalizar_auditoria(cliente, auditoria_id, item, "CONCLUIDA")
        return item
    except CatalogoClinicoErro:
        raise
    except Exception as exc:
        raise _falha_supabase(f"alterar o status da {config['rotulo']}", exc) from exc