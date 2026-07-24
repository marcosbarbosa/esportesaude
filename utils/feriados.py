"""
utils/feriados.py
Feriados e datas comemorativas de São Paulo — Nacional, Estadual, Municipal e Comemorações.
Usado pelo tab_admin (grid de dias) e tab_niver (PDF de aniversariantes).
"""
import datetime

NACIONAL   = "Nacional"
ESTADUAL   = "Estadual SP"
MUNICIPAL  = "Municipal SP"
COMEMORA   = "Comemoração"


def _pascoa(ano: int) -> datetime.date:
    """Algoritmo de Butcher para cálculo da data da Páscoa."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(ano, mes, dia)


def _segundo_domingo(ano: int, mes: int) -> datetime.date:
    """Retorna o 2º domingo do mês/ano."""
    d = datetime.date(ano, mes, 1)
    domingos = 0
    while True:
        if d.weekday() == 6:
            domingos += 1
            if domingos == 2:
                return d
        d += datetime.timedelta(days=1)


def obter_feriados_sp(anos=None, incluir_comemoracoes: bool = True) -> dict:
    """
    Retorna dict {datetime.date: {"nome": str, "tipo": str, "emoji": str}}.
    Se `anos` for None, usa o ano corrente ± 1.
    """
    if anos is None:
        hoje = datetime.date.today()
        anos = {hoje.year - 1, hoje.year, hoje.year + 1}

    resultado: dict[datetime.date, dict] = {}

    for ano in anos:
        p = _pascoa(ano)
        td = datetime.timedelta

        # ── Feriados Nacionais fixos ───────────────────────────────────────────
        nacionais_fixos = [
            (1,  1,  "Ano Novo",                        "🎆"),
            (4,  21, "Tiradentes",                      "🇧🇷"),
            (5,  1,  "Dia do Trabalhador",               "🔧"),
            (9,  7,  "Independência do Brasil",          "🇧🇷"),
            (10, 12, "Nossa Senhora Aparecida",          "🙏"),
            (11, 2,  "Finados",                          "🕯️"),
            (11, 15, "Proclamação da República",         "🇧🇷"),
            (11, 20, "Consciência Negra",                "✊"),
            (12, 25, "Natal",                            "🎄"),
        ]
        for mes, dia, nome, emoji in nacionais_fixos:
            resultado[datetime.date(ano, mes, dia)] = {"nome": nome, "tipo": NACIONAL, "emoji": emoji}

        # ── Feriados Nacionais móveis ──────────────────────────────────────────
        resultado[p - td(days=48)] = {"nome": "Carnaval (2ª)",          "tipo": NACIONAL, "emoji": "🎭"}
        resultado[p - td(days=47)] = {"nome": "Carnaval (3ª)",          "tipo": NACIONAL, "emoji": "🎭"}
        resultado[p - td(days=2)]  = {"nome": "Sexta-feira Santa",      "tipo": NACIONAL, "emoji": "✝️"}
        resultado[p]               = {"nome": "Páscoa",                 "tipo": NACIONAL, "emoji": "🐣"}
        resultado[p + td(days=60)] = {"nome": "Corpus Christi",         "tipo": NACIONAL, "emoji": "✝️"}

        # ── Feriados Estaduais SP ──────────────────────────────────────────────
        resultado[datetime.date(ano, 1, 25)] = {"nome": "Aniversário de São Paulo", "tipo": ESTADUAL, "emoji": "🏙️"}
        resultado[datetime.date(ano, 7,  9)] = {"nome": "Revolução Constitucionalista", "tipo": ESTADUAL, "emoji": "🏛️"}

        # ── Feriados Municipais São Paulo ──────────────────────────────────────
        resultado[datetime.date(ano, 1, 25)] = {"nome": "Aniversário de São Paulo", "tipo": ESTADUAL, "emoji": "🏙️"}

        if not incluir_comemoracoes:
            continue

        # ── Datas Comemorativas (sem ponto facultativo, mas dignas de atenção) ─
        comemorativas = [
            (1,  13, "Dia Mundial do Rock",              "🎸"),
            (2,  14, "Dia dos Namorados (internacional)","💝"),
            (3,   8, "Dia Internacional da Mulher",      "👩"),
            (4,   7, "Dia Mundial da Saúde",             "🏥"),
            (4,  22, "Dia da Terra",                     "🌎"),
            (6,   5, "Dia Mundial do Meio Ambiente",     "🌿"),
            (6,  12, "Dia dos Namorados",                "💕"),
            (6,  13, "Santo Antônio — Festa Junina",     "🎪"),
            (6,  24, "São João",                         "🎆"),
            (7,  20, "Dia do Amigo",                     "🤝"),
            (7,  26, "Dia dos Avós",                     "👴👵"),
            (8,  25, "Dia do Folclore",                  "🎭"),
            (9,  15, "Dia do Cliente",                   "😊"),
            (9,  21, "Dia Internacional da Paz / Alzheimer", "🕊️"),
            (10,  1, "Dia Internacional do Idoso",       "🧓"),
            (10,  4, "Dia dos Animais / São Francisco",  "🐾"),
            (10, 15, "Dia dos Professores",              "👩‍🏫"),
            (10, 31, "Halloween",                        "🎃"),
            (11,  1, "Dia de Todos os Santos",           "🙏"),
            (12,  1, "Dia Mundial da AIDS",              "🎗️"),
            (12,  5, "Dia Mundial do Voluntário",        "🤲"),
        ]
        for mes, dia, nome, emoji in comemorativas:
            dt = datetime.date(ano, mes, dia)
            if dt not in resultado:
                resultado[dt] = {"nome": nome, "tipo": COMEMORA, "emoji": emoji}

        # Datas variáveis (domingo específico)
        try:
            resultado[_segundo_domingo(ano, 5)] = {"nome": "Dia das Mães",       "tipo": COMEMORA, "emoji": "🌸"}
            resultado[_segundo_domingo(ano, 8)] = {"nome": "Dia dos Pais",       "tipo": COMEMORA, "emoji": "👨"}
        except Exception:
            pass

    return resultado


def obter_feriados_periodo(
    data_ini: datetime.date,
    data_fim: datetime.date,
    incluir_comemoracoes: bool = True,
) -> list[dict]:
    """
    Retorna lista de dicts ordenada por data:
      [{"data": date, "nome": str, "tipo": str, "emoji": str}, ...]
    apenas com datas dentro do intervalo [data_ini, data_fim].
    """
    anos = set(range(data_ini.year, data_fim.year + 1))
    todos = obter_feriados_sp(anos, incluir_comemoracoes)
    resultado = []
    for dt, info in todos.items():
        if data_ini <= dt <= data_fim:
            resultado.append({"data": dt, **info})
    return sorted(resultado, key=lambda x: x["data"])


def obter_feriados_mes(
    mes: int,
    ano: int,
    incluir_comemoracoes: bool = True,
) -> list[dict]:
    """
    Retorna lista de dicts com todos os feriados/comemorações do mês/ano.
    """
    data_ini = datetime.date(ano, mes, 1)
    ultimo = 28
    while True:
        try:
            datetime.date(ano, mes, ultimo + 1)
            ultimo += 1
        except ValueError:
            break
    data_fim = datetime.date(ano, mes, ultimo)
    return obter_feriados_periodo(data_ini, data_fim, incluir_comemoracoes)


def tipo_badge(tipo: str) -> str:
    """Retorna uma cor de fundo (CSS) para o badge de tipo de feriado."""
    return {
        NACIONAL:  "#DBEAFE",   # azul
        ESTADUAL:  "#EDE9FE",   # violeta
        MUNICIPAL: "#E0F2FE",   # ciano
        COMEMORA:  "#FEF9C3",   # amarelo-claro
    }.get(tipo, "#F3F4F6")


def tipo_cor_texto(tipo: str) -> str:
    """Retorna cor de texto CSS para o tipo de feriado."""
    return {
        NACIONAL:  "#1E40AF",
        ESTADUAL:  "#5B21B6",
        MUNICIPAL: "#0369A1",
        COMEMORA:  "#92400E",
    }.get(tipo, "#374151")
