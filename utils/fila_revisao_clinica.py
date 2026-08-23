"""Fila administrativa para revisão humana de informações clínicas.

Este módulo não infere diagnósticos, não classifica texto legado e não altera
campos de ``alunos``. Ele somente cria e revisa vínculos clínicos estruturados
quando um SuperAdmin autorizado faz uma escolha explícita.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from utils.catalogos_clinicos_admin import (
    CatalogoClinicoAcessoNegado,
    CatalogoClinicoErro,
    _cliente_administrativo,
    validar_acesso_catalogos_clinicos,
)


class FilaRevisaoClinicaErro(CatalogoClinicoErro):
    """Erro seguro para apresentação na fila de revisão clínica."""


TIPOS_FILA: dict[str, dict[str, str]] = {
    "condicao": {
        "rotulo": "Condição clínica",
        "tabela": "aluno_condicoes_clinicas",
        "tabela_catalogo": "catalogo_condicoes_clinicas",
        "campo_catalogo": "condicao_id",
        "campo_status": "status_revisao",
        "campo_fonte": "fonte_informacao",
        "campo_legado": "problemas_saude",
        "entidade": "ALUNO_CONDICAO",
        "campos_lista": (
            "id,aluno_id,condicao_id,status_revisao,fonte_informacao,"
            "responsavel_validacao,ativo,criado_em,atualizado_em"
        ),
    },
    "restricao": {
        "rotulo": "Restrição de movimento",
        "tabela": "aluno_restricoes_fisicas",
        "tabela_catalogo": "catalogo_restricoes_movimento",
        "campo_catalogo": "restricao_id",
        "campo_status": "status_revisao",
        "campo_fonte": "fonte_informacao",
        "campo_legado": "restricoes_fisicas",
        "entidade": "ALUNO_RESTRICAO",
        "campos_lista": (
            "id,aluno_id,restricao_id,status_revisao,fonte_informacao,"
            "responsavel_validacao,ativo,criado_em,atualizado_em"
        ),
    },
    "adaptacao": {
        "rotulo": "Adaptação recomendada",
        "tabela": "aluno_adaptacoes_recomendadas",
        "tabela_catalogo": "catalogo_adaptacoes",
        "campo_catalogo": "adaptacao_id",
        "campo_status": "status",
        "campo_fonte": "",
        "campo_legado": "tags_saude",
        "entidade": "ALUNO_ADAPTACAO",
        "campos_lista": (
            "id,aluno_id,adaptacao_id,status,revisado_por,revisado_em,"
            "ativo,criado_em,atualizado_em"
        ),
    },
}

_ESTADOS_FILA = {"PENDENTE", "SUGERIDO_POR_MIGRACAO"}
_CHAVE_CONTROLE_AUDITORIA = "_controle_auditoria_fila_clinica"
_MARCADOR_ORIGEM_LEGADA = "[ORIGEM_LEGADA_REVISAO]"
_LIMITE_PAGINA_FONTES = 50
_LIMITE_PAGINA_FILA = 25
_TAMANHO_PAGINA_AUDITORIA = 1000
_MAXIMO_PAGINAS_AUDITORIA = 100
_CONFIG_POR_ENTIDADE = {
    config["entidade"]: config for config in TIPOS_FILA.values()
}


def _config_tipo(tipo: str) -> dict[str, str]:
    config = TIPOS_FILA.get(str(tipo or "").strip().lower())
    if not config:
        raise FilaRevisaoClinicaErro("Tipo de revisão clínica inválido.")
    return config


def referencia_protegida(aluno_id: Any) -> str:
    """Cria uma referência estável sem expor nome, e-mail ou UUID completo."""
    texto = str(aluno_id or "").replace("-", "").upper()
    return f"ALU-{texto[-8:]}" if len(texto) >= 8 else "ALU-PROTEGIDO"


def _texto_obrigatorio(valor: Any, campo: str) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise FilaRevisaoClinicaErro(f"Informe {campo}.")
    return texto


def _texto_opcional(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _falha(acao: str, exc: Exception) -> FilaRevisaoClinicaErro:
    return FilaRevisaoClinicaErro(
        f"Não foi possível {acao} no momento. Tente novamente."
    )


def _controle(valor: dict[str, Any], status: str) -> dict[str, Any]:
    resultado = dict(valor)
    resultado[_CHAVE_CONTROLE_AUDITORIA] = {
        "status": status,
        "registrado_em": datetime.now(UTC).isoformat(),
    }
    return resultado


def _reservar_auditoria(
    cliente: Any,
    *,
    entidade: str,
    aluno_id: str,
    registro_id: str,
    operador: str,
    anterior: dict[str, Any] | None,
    previsto: dict[str, Any],
) -> str:
    resposta = (
        cliente.table("historico_revisoes_clinicas")
        .insert(
            {
                "aluno_id": aluno_id,
                "entidade": entidade,
                "registro_id": registro_id,
                "acao": "REVISAO",
                "valor_anterior": anterior,
                "valor_novo": _controle(previsto, "PENDENTE"),
                "operador": operador,
            }
        )
        .execute()
    )
    registro = (resposta.data or [None])[0]
    if not registro or not registro.get("id"):
        raise FilaRevisaoClinicaErro(
            "A alteração não foi realizada porque a auditoria não pôde ser iniciada."
        )
    return str(registro["id"])


def _finalizar_auditoria(
    cliente: Any, auditoria_id: str, valor_novo: dict[str, Any], status: str
) -> None:
    try:
        resposta = (
            cliente.table("historico_revisoes_clinicas")
            .update({"valor_novo": _controle(valor_novo, status)})
            .eq("id", auditoria_id)
            .execute()
        )
    except Exception as exc:
        raise FilaRevisaoClinicaErro(
            "A alteração foi registrada com auditoria pendente de reconciliação."
        ) from exc
    if not resposta.data:
        raise FilaRevisaoClinicaErro(
            "A alteração foi registrada com auditoria pendente de reconciliação."
        )


def _buscar_registro(cliente: Any, tabela: str, registro_id: str) -> dict[str, Any]:
    resposta = cliente.table(tabela).select("*").eq("id", registro_id).limit(1).execute()
    registro = (resposta.data or [None])[0]
    if not registro:
        raise FilaRevisaoClinicaErro("O item da fila não foi encontrado.")
    return registro


def _buscar_catalogo(
    cliente: Any,
    config: dict[str, str],
    catalogo_id: str,
    *,
    exigir_ativo: bool,
) -> dict[str, Any]:
    consulta = (
        cliente.table(config["tabela_catalogo"])
        .select("id,codigo,nome_padrao,ativo")
        .eq("id", catalogo_id)
    )
    if exigir_ativo:
        consulta = consulta.eq("ativo", True)
    resposta = consulta.limit(1).execute()
    item = (resposta.data or [None])[0]
    if not item:
        mensagem = (
            "Escolha um item ativo do catálogo antes de continuar."
            if exigir_ativo
            else "O item de catálogo associado não foi encontrado."
        )
        raise FilaRevisaoClinicaErro(mensagem)
    return item


def _buscar_catalogo_ativo(
    cliente: Any, config: dict[str, str], catalogo_id: str
) -> dict[str, Any]:
    return _buscar_catalogo(
        cliente, config, catalogo_id, exigir_ativo=True
    )


def _ler_texto_legado(cliente: Any, aluno_id: str, config: dict[str, str]) -> str:
    campo = config["campo_legado"]
    resposta = (
        cliente.table("alunos")
        .select(f"id,{campo}")
        .eq("id", aluno_id)
        .limit(1)
        .execute()
    )
    aluno = (resposta.data or [None])[0]
    if not aluno:
        raise FilaRevisaoClinicaErro("A referência protegida não foi encontrada.")
    texto = _texto_opcional(aluno.get(campo))
    if not texto:
        raise FilaRevisaoClinicaErro(
            "Não há informação legada disponível para o tipo selecionado."
        )
    return texto


def _verificar_fonte_legada(
    cliente: Any, aluno_id: str, config: dict[str, str]
) -> None:
    campo = config["campo_legado"]
    resposta = (
        cliente.table("alunos")
        .select("id")
        .eq("id", aluno_id)
        .neq(campo, "")
        .limit(1)
        .execute()
    )
    if not resposta.data:
        raise FilaRevisaoClinicaErro(
            "Não há informação legada disponível para o tipo selecionado."
        )


def _compor_contexto_legado(
    aluno_id: str,
    campo_origem: str,
    observacao: str | None,
) -> str:
    partes = [
        _MARCADOR_ORIGEM_LEGADA,
        f"Fonte protegida: {referencia_protegida(aluno_id)} · {campo_origem}",
        "O texto original permanece somente na fonte legada.",
    ]
    if observacao:
        partes.extend(("Observação do revisor:", observacao))
    return "\n".join(partes)


def _anexar_observacao(atual: Any, observacao: str) -> str:
    anterior = str(atual or "").strip()
    if not anterior:
        return observacao
    return f"{anterior}\n\nRevisão humana: {observacao}"


def listar_catalogo_ativo(tipo: str) -> list[dict[str, Any]]:
    """Retorna apenas itens ativos; não lê nem modifica dados de alunos."""
    config = _config_tipo(tipo)
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    try:
        resposta = (
            cliente.table(config["tabela_catalogo"])
            .select("id,codigo,nome_padrao,ativo")
            .eq("ativo", True)
            .order("nome_padrao")
            .execute()
        )
        return list(resposta.data or [])
    except Exception as exc:
        raise _falha("consultar o catálogo clínico", exc) from exc


def listar_fontes_legadas(
    pagina: int = 0, limite: int = _LIMITE_PAGINA_FONTES
) -> list[dict[str, Any]]:
    """Lista referências e tipo de fonte, sem nomes e sem escrever em ``alunos``."""
    if not isinstance(pagina, int) or pagina < 0:
        raise FilaRevisaoClinicaErro("Página de consulta inválida.")
    if not isinstance(limite, int) or not 1 <= limite <= _LIMITE_PAGINA_FONTES:
        raise FilaRevisaoClinicaErro("Limite de consulta inválido.")
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    fontes: list[dict[str, Any]] = []
    try:
        inicio = pagina * limite
        for tipo, config in TIPOS_FILA.items():
            # A consulta devolve somente o ID. O texto é buscado separadamente
            # apenas quando o administrador pede para abrir uma fonte específica.
            resposta = (
                cliente.table("alunos")
                .select("id")
                .neq(config["campo_legado"], "")
                .order("id")
                .range(inicio, inicio + limite - 1)
                .execute()
            )
            for aluno in resposta.data or []:
                aluno_id = str(aluno.get("id") or "")
                if not aluno_id:
                    continue
                fontes.append(
                    {
                        "aluno_id": aluno_id,
                        "referencia_protegida": referencia_protegida(aluno_id),
                        "tipo": tipo,
                        "origem": "REGISTRO_LEGADO",
                        "campo_origem": config["campo_legado"],
                    }
                )
    except Exception as exc:
        raise _falha("consultar as fontes legadas", exc) from exc
    return fontes


def obter_texto_fonte_legada(tipo: str, aluno_id: str) -> str:
    """Lê uma única fonte após seleção explícita, sem cache ou consulta em massa."""
    config = _config_tipo(tipo)
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    try:
        return _ler_texto_legado(
            cliente, _texto_obrigatorio(aluno_id, "a referência protegida"), config
        )
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("consultar o contexto legado protegido", exc) from exc


def _origem_do_item(config: dict[str, str], item: dict[str, Any]) -> str:
    if config["campo_fonte"]:
        return str(item.get(config["campo_fonte"]) or "NÃO INFORMADA")
    observacao = str(item.get("observacao_operacional") or "")
    return "REGISTRO_LEGADO" if _MARCADOR_ORIGEM_LEGADA in observacao else "NÃO INFORMADA"


def _observacao_do_item(config: dict[str, str], item: dict[str, Any]) -> str:
    if config["rotulo"] == "Condição clínica":
        return str(item.get("observacao_contextual") or "")
    if config["rotulo"] == "Restrição de movimento":
        return str(
            item.get("observacao_contextual")
            or item.get("observacao_original")
            or item.get("texto_original_legado")
            or ""
        )
    return str(item.get("observacao_operacional") or "")


def _resumo_ultima_revisao(
    cliente: Any, registro_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Busca somente operador/data da revisão mais recente, sem JSON clínico."""
    ids = tuple(dict.fromkeys(item for item in registro_ids if item))
    if not ids:
        return {}
    resultado: dict[str, dict[str, Any]] = {}
    for pagina in range(_MAXIMO_PAGINAS_AUDITORIA):
        inicio = pagina * _TAMANHO_PAGINA_AUDITORIA
        resposta = (
            cliente.table("historico_revisoes_clinicas")
            .select("id,registro_id,operador,criado_em")
            .in_("registro_id", ids)
            .in_("entidade", tuple(_CONFIG_POR_ENTIDADE))
            .eq("acao", "REVISAO")
            .order("criado_em", desc=True)
            .order("id", desc=True)
            .range(inicio, inicio + _TAMANHO_PAGINA_AUDITORIA - 1)
            .execute()
        )
        lote = list(resposta.data or [])
        for revisao in lote:
            registro_id = str(revisao.get("registro_id") or "")
            if registro_id and registro_id not in resultado:
                resultado[registro_id] = revisao
        if len(lote) < _TAMANHO_PAGINA_AUDITORIA:
            return resultado
    raise FilaRevisaoClinicaErro(
        "O volume de revisões excedeu o limite de conferência da fila."
    )


def listar_itens_fila(
    tipo: str | None = None,
    status: str | None = None,
    origem: str | None = None,
    responsavel: str | None = None,
    pagina: int = 0,
    limite: int = _LIMITE_PAGINA_FILA,
) -> list[dict[str, Any]]:
    """Normaliza os vínculos pendentes sem trazer identificação pessoal do aluno."""
    tipos = (str(tipo).lower(),) if tipo else tuple(TIPOS_FILA)
    configs = [_config_tipo(item) for item in tipos]
    if status and status not in _ESTADOS_FILA:
        raise FilaRevisaoClinicaErro("Status de fila inválido.")
    if not isinstance(pagina, int) or pagina < 0:
        raise FilaRevisaoClinicaErro("Página de consulta inválida.")
    if not isinstance(limite, int) or not 1 <= limite <= _LIMITE_PAGINA_FILA:
        raise FilaRevisaoClinicaErro("Limite de consulta inválido.")
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    itens_por_config: list[tuple[dict[str, str], list[dict[str, Any]]]] = []
    try:
        inicio = pagina * limite
        for config in configs:
            estados = ("PENDENTE", "SUGERIDO_POR_MIGRACAO")
            if config["rotulo"] == "Adaptação recomendada":
                estados = ("PENDENTE",)
            consulta = (
                cliente.table(config["tabela"])
                .select(config["campos_lista"])
                .eq("ativo", True)
                .order("criado_em", desc=True)
                .range(inicio, inicio + limite - 1)
            )
            consulta = (
                consulta.eq(config["campo_status"], status)
                if status
                else consulta.in_(config["campo_status"], estados)
            )
            itens_por_config.append((config, list(consulta.execute().data or [])))
    except Exception as exc:
        raise _falha("consultar a fila de revisão", exc) from exc

    resultado: list[dict[str, Any]] = []
    try:
        revisoes = _resumo_ultima_revisao(
            cliente,
            [
                str(item.get("id") or "")
                for _, itens in itens_por_config
                for item in itens
            ],
        )
        for config, itens in itens_por_config:
            catalogo_ids = [
                str(item.get(config["campo_catalogo"]) or "") for item in itens
                if item.get(config["campo_catalogo"])
            ]
            catalogo = (
                cliente.table(config["tabela_catalogo"])
                .select("id,codigo,nome_padrao")
                .in_("id", catalogo_ids)
                .execute()
                .data
                if catalogo_ids
                else []
            )
            catalogo_por_id = {str(item.get("id")): item for item in catalogo or []}
            for item in itens:
                item_id = str(item.get("id") or "")
                revisao = revisoes.get(item_id, {})
                item_catalogo = catalogo_por_id.get(
                    str(item.get(config["campo_catalogo"]) or ""), {}
                )
                responsavel_item = (
                    item.get("responsavel_validacao")
                    or item.get("revisado_por")
                    or revisao.get("operador")
                    or ""
                )
                estado = str(item.get(config["campo_status"]) or "")
                linha = {
                    "id": item_id,
                    "tipo": next(
                        chave for chave, valor in TIPOS_FILA.items() if valor == config
                    ),
                    "tipo_rotulo": config["rotulo"],
                    "referencia_protegida": referencia_protegida(item.get("aluno_id")),
                    "aluno_id": str(item.get("aluno_id") or ""),
                    "status": estado,
                    "origem": _origem_do_item(config, item),
                    "sugestao": (
                        f"{item_catalogo.get('codigo') or '—'} — "
                        f"{item_catalogo.get('nome_padrao') or 'Item indisponível'}"
                    ),
                    "catalogo_id": str(item.get(config["campo_catalogo"]) or ""),
                    "responsavel_revisao": responsavel_item or "—",
                    "data_revisao": (
                        item.get("revisado_em")
                        or revisao.get("criado_em")
                        or None
                    ),
                    "atualizado_em": item.get("atualizado_em"),
                    "criado_em": item.get("criado_em"),
                }
                if status and linha["status"] != status:
                    continue
                if origem and linha["origem"].casefold() != origem.casefold():
                    continue
                if responsavel and responsavel.casefold() not in str(
                    linha["responsavel_revisao"]
                ).casefold():
                    continue
                resultado.append(linha)
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("organizar a fila de revisão", exc) from exc
    return sorted(resultado, key=lambda item: str(item.get("criado_em") or ""), reverse=True)


def obter_detalhe_item_fila(tipo: str, registro_id: str) -> dict[str, Any]:
    """Busca contexto de um único item explicitamente aberto pelo administrador."""
    config = _config_tipo(tipo)
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    try:
        item = _buscar_registro(
            cliente, config["tabela"], _texto_obrigatorio(registro_id, "o item da fila")
        )
        estado = str(item.get(config["campo_status"]) or "")
        if estado not in _ESTADOS_FILA:
            raise FilaRevisaoClinicaErro(
                "Este item já foi revisado ou não está mais disponível na fila."
            )
        item_catalogo = _buscar_catalogo(
            cliente,
            config,
            str(item.get(config["campo_catalogo"]) or ""),
            exigir_ativo=False,
        )
        sufixo_catalogo = "" if item_catalogo.get("ativo") is True else " (inativo)"
        historico = (
            cliente.table("historico_revisoes_clinicas")
            .select("operador,criado_em")
            .eq("registro_id", registro_id)
            .eq("acao", "REVISAO")
            .order("criado_em", desc=True)
            .limit(1)
            .execute()
        )
        ultima_revisao = (historico.data or [None])[0] or {}
        return {
            "id": str(item.get("id") or ""),
            "tipo": tipo,
            "tipo_rotulo": config["rotulo"],
            "referencia_protegida": referencia_protegida(item.get("aluno_id")),
            "aluno_id": str(item.get("aluno_id") or ""),
            "status": estado,
            "origem": _origem_do_item(config, item),
            "sugestao": (
                f"{item_catalogo.get('codigo') or '—'} — "
                f"{item_catalogo.get('nome_padrao') or 'Item indisponível'}"
                f"{sufixo_catalogo}"
            ),
            "catalogo_id": str(item.get(config["campo_catalogo"]) or ""),
            "responsavel_revisao": (
                item.get("responsavel_validacao")
                or item.get("revisado_por")
                or ultima_revisao.get("operador")
                or "—"
            ),
            "data_revisao": item.get("revisado_em") or ultima_revisao.get("criado_em"),
            "observacao": _observacao_do_item(config, item),
            "atualizado_em": item.get("atualizado_em"),
            "criado_em": item.get("criado_em"),
        }
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("consultar o detalhe protegido da revisão", exc) from exc


def _valor_sem_controle(valor: Any) -> dict[str, Any]:
    resultado = dict(valor) if isinstance(valor, dict) else {}
    resultado.pop(_CHAVE_CONTROLE_AUDITORIA, None)
    return resultado


def _registro_corresponde_ao_previsto(
    previsto: dict[str, Any], observado: dict[str, Any] | None
) -> bool:
    if not observado:
        return False
    ignorar = {"criado_em", "atualizado_em"}
    return all(
        observado.get(campo) == valor
        for campo, valor in previsto.items()
        if campo not in ignorar
    )


def reconciliar_auditorias_fila_pendentes() -> dict[str, int]:
    """Finaliza reservas cujo vínculo já foi persistido após uma falha incerta."""
    validar_acesso_catalogos_clinicos()
    cliente = _cliente_administrativo()
    pendencias: list[dict[str, Any]] = []
    try:
        for pagina in range(_MAXIMO_PAGINAS_AUDITORIA):
            inicio = pagina * _TAMANHO_PAGINA_AUDITORIA
            resposta = (
                cliente.table("historico_revisoes_clinicas")
                .select("id,entidade,registro_id,valor_novo,criado_em")
                .in_("entidade", tuple(_CONFIG_POR_ENTIDADE))
                .contains(
                    "valor_novo",
                    {_CHAVE_CONTROLE_AUDITORIA: {"status": "PENDENTE"}},
                )
                .order("criado_em", desc=True)
                .order("id", desc=True)
                .range(inicio, inicio + _TAMANHO_PAGINA_AUDITORIA - 1)
                .execute()
            )
            lote = list(resposta.data or [])
            pendencias.extend(lote)
            if len(lote) < _TAMANHO_PAGINA_AUDITORIA:
                break
        else:
            raise FilaRevisaoClinicaErro(
                "O volume de auditorias pendentes excedeu o limite de conferência."
            )
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("verificar as auditorias pendentes da fila", exc) from exc

    reconciliadas = 0
    ainda_pendentes = 0
    for auditoria in pendencias:
        config = _CONFIG_POR_ENTIDADE.get(str(auditoria.get("entidade") or ""))
        auditoria_id = str(auditoria.get("id") or "")
        registro_id = str(auditoria.get("registro_id") or "")
        previsto = _valor_sem_controle(auditoria.get("valor_novo"))
        if not config or not auditoria_id or not registro_id:
            ainda_pendentes += 1
            continue
        try:
            resposta = (
                cliente.table(config["tabela"])
                .select("*")
                .eq("id", registro_id)
                .limit(1)
                .execute()
            )
            observado = (resposta.data or [None])[0]
            if not _registro_corresponde_ao_previsto(previsto, observado):
                ainda_pendentes += 1
                continue
            _finalizar_auditoria(
                cliente,
                auditoria_id,
                observado,
                "CONCLUIDA_RECONCILIADA",
            )
            reconciliadas += 1
        except Exception:
            ainda_pendentes += 1
    return {
        "encontradas": len(pendencias),
        "reconciliadas": reconciliadas,
        "pendentes": ainda_pendentes,
    }


def criar_candidato_de_fonte_legada(
    tipo: str,
    aluno_id: str,
    catalogo_id: str,
    observacao: str | None = None,
    nivel_orientacao: str = "MONITORAR",
) -> dict[str, Any]:
    """Cria candidato somente após seleção humana de item ativo do catálogo."""
    config = _config_tipo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    aluno_id = _texto_obrigatorio(aluno_id, "a referência protegida")
    catalogo_id = _texto_obrigatorio(catalogo_id, "um item do catálogo")
    observacao = _texto_opcional(observacao)
    cliente = _cliente_administrativo()
    try:
        _verificar_fonte_legada(cliente, aluno_id, config)
        _buscar_catalogo_ativo(cliente, config, catalogo_id)
        duplicado = (
            cliente.table(config["tabela"])
            .select("id")
            .eq("aluno_id", aluno_id)
            .eq(config["campo_catalogo"], catalogo_id)
            .eq("ativo", True)
            .limit(1)
            .execute()
        )
        if duplicado.data:
            raise FilaRevisaoClinicaErro(
                "Já existe um vínculo clínico ativo para esta seleção."
            )
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("preparar o candidato para revisão", exc) from exc

    registro_id = str(uuid.uuid4())
    contexto = _compor_contexto_legado(
        aluno_id, config["campo_legado"], observacao
    )
    payload: dict[str, Any] = {
        "id": registro_id,
        "aluno_id": aluno_id,
        config["campo_catalogo"]: catalogo_id,
        "ativo": True,
        "criado_por": operador,
    }
    if tipo == "condicao":
        payload.update(
            {
                "status": "NAO_INFORMADO",
                "fonte_informacao": "REGISTRO_LEGADO",
                "status_revisao": "SUGERIDO_POR_MIGRACAO",
                "observacao_contextual": contexto,
            }
        )
    elif tipo == "restricao":
        nivel = str(nivel_orientacao or "").upper()
        if nivel not in {"EVITAR", "REDUZIR", "ADAPTAR", "MONITORAR", "SEM_RESTRICAO"}:
            raise FilaRevisaoClinicaErro("Selecione um nível de orientação válido.")
        payload.update(
            {
                "fonte_informacao": "REGISTRO_LEGADO",
                "status_revisao": "SUGERIDO_POR_MIGRACAO",
                "nivel_orientacao": nivel,
                "observacao_original": contexto,
            }
        )
    else:
        payload.update({"status": "PENDENTE", "observacao_operacional": contexto})

    try:
        auditoria_id = _reservar_auditoria(
            cliente,
            entidade=config["entidade"],
            aluno_id=aluno_id,
            registro_id=registro_id,
            operador=operador,
            anterior=None,
            previsto=payload,
        )
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("iniciar a auditoria da sugestão", exc) from exc
    try:
        resposta = cliente.table(config["tabela"]).insert(payload).execute()
        registro = (resposta.data or [None])[0]
        if not registro:
            raise FilaRevisaoClinicaErro(
                "O resultado da criação é incerto e a auditoria permanece pendente."
            )
        _finalizar_auditoria(cliente, auditoria_id, registro, "CONCLUIDA")
        return registro
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise FilaRevisaoClinicaErro(
            "O resultado da criação é incerto e a auditoria permanece pendente "
            "de reconciliação."
        ) from exc


def _mutar_item(
    tipo: str,
    registro_id: str,
    atualizado_em: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    config = _config_tipo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    registro_id = _texto_obrigatorio(registro_id, "o item da fila")
    atualizado_em = _texto_obrigatorio(atualizado_em, "a versão atual do item")
    cliente = _cliente_administrativo()
    try:
        anterior = _buscar_registro(cliente, config["tabela"], registro_id)
        if str(anterior.get(config["campo_status"]) or "") not in _ESTADOS_FILA:
            raise FilaRevisaoClinicaErro(
                "Este item já foi revisado ou não está mais disponível na fila."
            )
        if str(anterior.get("atualizado_em") or "") != atualizado_em:
            raise FilaRevisaoClinicaErro(
                "O item foi alterado por outra sessão. Recarregue antes de salvar."
            )
        previsto = {**anterior, **payload}
        auditoria_id = _reservar_auditoria(
            cliente,
            entidade=config["entidade"],
            aluno_id=str(anterior.get("aluno_id") or ""),
            registro_id=registro_id,
            operador=operador,
            anterior=anterior,
            previsto=previsto,
        )
        resposta = (
            cliente.table(config["tabela"])
            .update(payload)
            .eq("id", registro_id)
            .eq("atualizado_em", atualizado_em)
            .execute()
        )
        registro = (resposta.data or [None])[0]
        if not registro:
            raise FilaRevisaoClinicaErro(
                "O resultado da atualização é incerto e a auditoria permanece "
                "pendente de reconciliação. Recarregue antes de tentar novamente."
            )
        _finalizar_auditoria(cliente, auditoria_id, registro, "CONCLUIDA")
        return registro
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("registrar a revisão clínica", exc) from exc


def revisar_item_fila(
    tipo: str,
    registro_id: str,
    atualizado_em: str,
    decisao: str,
    observacao: str,
) -> dict[str, Any]:
    """Valida ou rejeita explicitamente um candidato ainda na fila."""
    decisao = str(decisao or "").upper()
    if decisao not in {"VALIDADO", "REJEITADO"}:
        raise FilaRevisaoClinicaErro("Escolha validar ou rejeitar o item.")
    nota = _texto_obrigatorio(observacao, "a observação da revisão")
    config = _config_tipo(tipo)
    operador = validar_acesso_catalogos_clinicos()
    if tipo == "adaptacao":
        payload = {
            "status": decisao,
            "revisado_por": operador,
            "revisado_em": datetime.now(UTC).isoformat(),
        }
    else:
        payload = {
            "status_revisao": decisao,
            "responsavel_validacao": operador,
        }
    # A observação é anexada somente ao vínculo estruturado, jamais à tabela legada.
    cliente = _cliente_administrativo()
    try:
        anterior = _buscar_registro(cliente, config["tabela"], registro_id)
        campo_observacao = (
            "observacao_operacional"
            if tipo == "adaptacao"
            else "observacao_contextual"
        )
        if tipo == "restricao" and not anterior.get(campo_observacao):
            campo_observacao = "observacao_original"
        payload[campo_observacao] = _anexar_observacao(
            anterior.get(campo_observacao), nota
        )
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("preparar a revisão clínica", exc) from exc
    return _mutar_item(tipo, registro_id, atualizado_em, payload)


def corrigir_item_fila(
    tipo: str,
    registro_id: str,
    atualizado_em: str,
    catalogo_id: str,
    observacao: str,
) -> dict[str, Any]:
    """Corrige a seleção humana, mantendo o item pendente para nova validação."""
    # A autorização precisa ocorrer antes de criar o cliente ou consultar
    # catálogo/vínculo, mesmo que _mutar_item também repita a barreira.
    validar_acesso_catalogos_clinicos()
    config = _config_tipo(tipo)
    nota = _texto_obrigatorio(observacao, "a observação da correção")
    catalogo_id = _texto_obrigatorio(catalogo_id, "um item ativo do catálogo")
    cliente = _cliente_administrativo()
    try:
        _buscar_catalogo_ativo(cliente, config, catalogo_id)
        anterior = _buscar_registro(cliente, config["tabela"], registro_id)
        campo_observacao = (
            "observacao_operacional"
            if tipo == "adaptacao"
            else "observacao_contextual"
        )
        if tipo == "restricao" and not anterior.get(campo_observacao):
            campo_observacao = "observacao_original"
        payload = {
            config["campo_catalogo"]: catalogo_id,
            config["campo_status"]: "PENDENTE",
            campo_observacao: _anexar_observacao(anterior.get(campo_observacao), nota),
        }
    except FilaRevisaoClinicaErro:
        raise
    except Exception as exc:
        raise _falha("preparar a correção", exc) from exc
    return _mutar_item(tipo, registro_id, atualizado_em, payload)