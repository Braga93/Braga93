#!/usr/bin/env python3
"""Gera os gráficos do perfil em SVG, nas cores do tema: dourado sobre preto.

Uso:
    python scripts/gerar_graficos.py          busca os dados reais na API do GitHub
    python scripts/gerar_graficos.py --demo   usa dados de exemplo (só para testar o visual)

No GitHub Actions, o GITHUB_TOKEN é lido do ambiente. Os gráficos de linguagens
e o resumo contam apenas repositórios públicos.
"""
import argparse
import json
import math
import os
import random
import textwrap
import urllib.request
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

DONO = "Braga93"
PASTA_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# Projetos em destaque. Para trocar a vitrine, edite esta lista.
DESTAQUES = [
    {
        "arquivo": "projeto_braga_effects_library.svg",
        "nome": "braga_effects_library",
        "descricao": "Biblioteca aberta de efeitos CSS e utilitários JavaScript em português, "
                     "criada para quem está começando e não sabe por onde partir.",
        "tags": ["CSS", "JavaScript", "npm", "MIT"],
    },
    {
        "arquivo": "projeto_nike_site_js.svg",
        "nome": "nike_site_js",
        "descricao": "Réplica autoral de uma página de loja de tênis, com login e cadastro "
                     "simulados. Meu primeiro portfólio, que cresce junto comigo.",
        "tags": ["HTML", "CSS", "JavaScript"],
    },
]

# Paleta do perfil
OURO = "#c9a84c"
FUNDO = "#0d0d0d"
BORDA = "#2a2a2a"
TEXTO = "#cccccc"
TEXTO_FRACO = "#888888"
NIVEIS = ["#161616", "#3a2f12", "#6b5620", "#a68a3a", "#c9a84c"]
# Cores da rosca de linguagens: ouro, sangue, osso, ouro escuro e ardósia
CORES_ROSCA = [OURO, "#8e2b2b", "#e3d9bd", "#7a6428", "#4f5b66"]
FONTE = "'IM Fell English SC', Georgia, 'Times New Roman', serif"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# ----------------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------------
def requisitar(url, corpo=None):
    cabecalhos = {"Accept": "application/vnd.github+json", "User-Agent": "gerar-graficos-perfil"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    if corpo is not None:
        cabecalhos["Content-Type"] = "application/json"
    pedido = urllib.request.Request(url, data=corpo, headers=cabecalhos)
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return json.load(resposta)


def buscar_dados():
    repos, pagina = [], 1
    while True:
        lote = requisitar(f"https://api.github.com/users/{DONO}/repos?type=owner&per_page=100&page={pagina}")
        repos += lote
        if len(lote) < 100:
            break
        pagina += 1
    proprios = [r for r in repos if not r["fork"] and not r["private"]]

    # O repositório do perfil guarda só este script e as imagens, então não entra na conta de linguagens.
    linguagens = {}
    for repo in proprios:
        if repo["name"].lower() == DONO.lower():
            continue
        for nome, bytes_ in requisitar(repo["languages_url"]).items():
            linguagens[nome] = linguagens.get(nome, 0) + bytes_

    dados = {
        "repos": len(proprios),
        "linguagens": linguagens,
        "dias": None,
        "commits": None,
        "total": None,
    }

    # O calendário de contribuições só existe na API GraphQL. Se falhar, o resto continua.
    consulta = (
        "query($login:String!){user(login:$login){contributionsCollection{"
        "totalCommitContributions contributionCalendar{totalContributions "
        "weeks{contributionDays{date contributionCount}}}}}}"
    )
    try:
        corpo = json.dumps({"query": consulta, "variables": {"login": DONO}}).encode()
        colecao = requisitar("https://api.github.com/graphql", corpo)["data"]["user"]["contributionsCollection"]
        calendario = colecao["contributionCalendar"]
        dados["dias"] = [
            (d["date"], d["contributionCount"])
            for semana in calendario["weeks"]
            for d in semana["contributionDays"]
        ]
        dados["commits"] = colecao["totalCommitContributions"]
        dados["total"] = calendario["totalContributions"]
    except Exception as erro:  # noqa: BLE001
        print(f"AVISO: não foi possível ler o calendário de contribuições ({erro}).")
    return dados


def dados_demo():
    """Dados inventados, só para conferir o visual. Nunca vão para o perfil."""
    random.seed(7)
    hoje = date.today()
    dias = []
    for i in range(365):
        dia = hoje - timedelta(days=364 - i)
        opcoes = [0, 0, 0, 1, 2, 3, 5, 8, 12] if i > 200 else [0, 0, 0, 0, 0, 1, 2]
        dias.append((dia.isoformat(), random.choice(opcoes)))
    return {
        "repos": 7,
        "linguagens": {"CSS": 52000, "HTML": 41000, "JavaScript": 33000, "Shell": 1500},
        "dias": dias,
        "commits": 58,
        "total": sum(n for _, n in dias),
    }


def sequencias(dias):
    """Retorna (sequência atual, maior sequência), em dias com contribuição."""
    maior = atual = 0
    for _, n in dias:
        atual = atual + 1 if n > 0 else 0
        maior = max(maior, atual)
    ao_fim = 0
    for posicao, (_, n) in enumerate(reversed(dias)):
        if n > 0:
            ao_fim += 1
        elif posicao == 0:
            continue  # hoje ainda sem contribuição não quebra a sequência
        else:
            break
    return ao_fim, maior


# ----------------------------------------------------------------------------
# Desenho
# ----------------------------------------------------------------------------
def moldura(largura, altura, titulo, corpo, descricao):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" role="img" aria-label="{escape(descricao)}">
<title>{escape(descricao)}</title>
<style>
text {{ font-family: {FONTE}; }}
.t {{ fill: {OURO}; font-size: 15px; letter-spacing: 1.5px; }}
.n {{ fill: {TEXTO}; font-size: 13px; }}
.f {{ fill: {TEXTO_FRACO}; font-size: 11px; }}
.g {{ fill: {OURO}; font-size: 30px; }}
.o {{ fill: {OURO}; font-size: 11px; }}
</style>
<rect x="0.5" y="0.5" width="{largura - 1}" height="{altura - 1}" rx="8" fill="{FUNDO}" stroke="{BORDA}"/>
<text x="20" y="30" class="t">◈ {escape(titulo)}</text>
<line x1="20" y1="42" x2="{largura - 20}" y2="42" stroke="{OURO}" stroke-opacity="0.35"/>
{corpo}
</svg>
"""


def percentual(valor):
    return f"{valor:.1f}".replace(".", ",") + "%"


def cartao_linguagens(linguagens):
    principais = sorted(linguagens.items(), key=lambda p: p[1], reverse=True)[:5]
    mostradas = sum(v for _, v in principais) or 1
    cx, cy, raio, espessura = 400, 120, 44, 16
    circunferencia = 2 * math.pi * raio
    folga = 2 if len(principais) > 1 else 0

    legenda = []
    arcos = [f'<circle cx="{cx}" cy="{cy}" r="{raio}" fill="none" stroke="#161616" stroke-width="{espessura}"/>']
    comeco = 0.0
    for i, (nome, valor) in enumerate(principais):
        parte = valor / mostradas
        y = 72 + i * 24
        legenda.append(
            f'<circle cx="26" cy="{y + 5}" r="5" fill="{CORES_ROSCA[i]}"/>'
            f'<text x="40" y="{y + 10}" class="n">{escape(nome)}</text>'
            f'<text x="250" y="{y + 10}" class="f" text-anchor="end">{percentual(parte * 100)}</text>'
        )
        comprimento = parte * circunferencia
        visivel = max(comprimento - folga, 0.5)
        arcos.append(
            f'<circle cx="{cx}" cy="{cy}" r="{raio}" fill="none" stroke="{CORES_ROSCA[i]}" '
            f'stroke-width="{espessura}" stroke-dasharray="{visivel:.2f} {circunferencia - visivel:.2f}" '
            f'stroke-dashoffset="{-comeco:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        comeco += comprimento
    if not principais:
        legenda.append('<text x="20" y="90" class="f">Ainda não há código público para analisar.</text>')
    return moldura(495, 195, "Arsenal em uso · Linguagens", "\n".join(legenda + arcos),
                   "Linguagens mais usadas nos repositórios públicos")


def cartao_resumo(dados):
    atual = maior = "—"
    commits = "—"
    if dados["dias"]:
        a, m = sequencias(dados["dias"])
        atual, maior = str(a), str(m)
    if dados["commits"] is not None:
        commits = str(dados["commits"])
    itens = [
        (20, 90, str(dados["repos"]), "repositórios públicos"),
        (260, 90, commits, "commits no último ano"),
        (20, 150, atual, "dias seguidos agora"),
        (260, 150, maior, "maior sequência (dias)"),
    ]
    corpo = "\n".join(
        f'<text x="{x}" y="{y}" class="g">{escape(valor)}</text>'
        f'<text x="{x}" y="{y + 18}" class="f">{escape(rotulo)}</text>'
        for x, y, valor, rotulo in itens
    )
    return moldura(495, 195, "Registro da Caçada", corpo, "Resumo das contribuições no GitHub")


def cartao_atividade(dados):
    dias = dados["dias"]
    celula, vao = 11, 3
    passo = celula + vao
    x0, y0 = 20, 78
    primeiro = datetime.strptime(dias[0][0], "%Y-%m-%d").date()
    deslocamento = (primeiro.weekday() + 1) % 7  # domingo = 0
    maximo = max((n for _, n in dias), default=0) or 1

    def nivel(n):
        if n == 0:
            return 0
        razao = n / maximo
        return 1 if razao <= 0.25 else 2 if razao <= 0.5 else 3 if razao <= 0.75 else 4

    quadrados, rotulos, ultimo_mes = [], [], None
    for i, (texto, n) in enumerate(dias):
        dia = datetime.strptime(texto, "%Y-%m-%d").date()
        coluna, linha = (i + deslocamento) // 7, (i + deslocamento) % 7
        x, y = x0 + coluna * passo, y0 + linha * passo
        quadrados.append(
            f'<rect x="{x}" y="{y}" width="{celula}" height="{celula}" rx="2" fill="{NIVEIS[nivel(n)]}">'
            f"<title>{n} contribuições em {dia.strftime('%d/%m/%Y')}</title></rect>"
        )
        if dia.month != ultimo_mes and dia.day <= 7:
            rotulos.append(f'<text x="{x}" y="{y0 - 8}" class="f">{MESES[dia.month - 1]}</text>')
            ultimo_mes = dia.month
    colunas = (len(dias) + deslocamento + 6) // 7
    largura = x0 * 2 + colunas * passo
    y_legenda = y0 + 7 * passo + 16
    legenda = "".join(
        f'<rect x="{largura - 20 - 5 * 14 + k * 14}" y="{y_legenda - 10}" width="11" height="11" rx="2" fill="{cor}"/>'
        for k, cor in enumerate(NIVEIS)
    )
    legenda += (f'<text x="{largura - 20 - 5 * 14 - 8}" y="{y_legenda}" class="f" text-anchor="end">menos</text>'
                f'<text x="{largura - 20 + 4}" y="{y_legenda}" class="f">mais</text>')
    corpo = "\n".join(rotulos + quadrados) + legenda
    total = dados["total"] if dados["total"] is not None else sum(n for _, n in dias)
    return moldura(largura + 30, y_legenda + 22, f"Contribuições · {total} no último ano",
                   corpo, "Calendário de contribuições dos últimos 12 meses")


def cartao_projeto(projeto):
    linhas = textwrap.wrap(projeto["descricao"], width=54)[:3]
    corpo = [f'<text x="20" y="{70 + i * 20}" class="n">{escape(l)}</text>' for i, l in enumerate(linhas)]
    x = 20
    for tag in projeto["tags"]:
        largura = len(tag) * 7 + 18
        corpo.append(
            f'<rect x="{x}" y="138" width="{largura}" height="20" rx="10" fill="none" stroke="{OURO}" stroke-opacity="0.5"/>'
            f'<text x="{x + largura / 2}" y="152" class="o" text-anchor="middle">{escape(tag)}</text>'
        )
        x += largura + 8
    return moldura(410, 175, projeto["nome"], "\n".join(corpo), f"Projeto em destaque: {projeto['nome']}")


# ----------------------------------------------------------------------------
def escrever(nome, conteudo):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho = os.path.join(PASTA_SAIDA, nome)
    with open(caminho, "w", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(conteudo)
    print("gerado:", nome)


def main():
    analisador = argparse.ArgumentParser()
    analisador.add_argument("--demo", action="store_true", help="usa dados de exemplo")
    args = analisador.parse_args()
    dados = dados_demo() if args.demo else buscar_dados()

    escrever("linguagens.svg", cartao_linguagens(dados["linguagens"]))
    escrever("resumo.svg", cartao_resumo(dados))
    if dados["dias"]:
        escrever("atividade.svg", cartao_atividade(dados))
    else:
        print("AVISO: atividade.svg não foi atualizado (sem dados do calendário).")
    for projeto in DESTAQUES:
        escrever(projeto["arquivo"], cartao_projeto(projeto))


if __name__ == "__main__":
    main()
