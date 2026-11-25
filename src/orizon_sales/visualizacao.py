"""Interface em português brasileiro para os oito módulos comerciais."""

import pandas as pd
import plotly.express as px
import streamlit as st

from .analise import (
    CAMPOS_FILTRO, Filtros, crescimento, curva_abc, desempenho, filtrar_dimensoes,
    no_periodo, resultado_operacional, resumo, sazonalidade,
)
from .demonstracao import carregar_demonstracao
from .qualidade import FIM, INICIO


CORES = ("#0A776C", "#4460A8", "#D69B46", "#A44164", "#5B7290")
MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
ROTULOS = {
    "bruto": "Faturamento bruto", "liquido": "Faturamento líquido", "lucro": "Lucro bruto",
    "margem": "Margem bruta", "ticket": "Ticket médio", "pedidos": "Pedidos",
    "clientes": "Clientes ativos", "frequencia": "Compras por cliente", "mensal": "Crescimento mensal",
    "anual": "Crescimento anual", "desconto": "Descontos", "tributo": "Tributos",
    "custo": "Custo da mercadoria", "filial": "Filial", "categoria": "Categoria",
    "produto": "Produto", "vendedor": "Vendedor", "segmento": "Segmento", "cliente": "Cliente",
    "sku": "SKU", "classe": "Classe ABC", "acumulado": "Receita acumulada", "mes": "Mês",
    "media": "Média de faturamento líquido", "observacoes": "Meses observados",
}
FILTRO_ROTULOS = {
    "filiais": "Filiais", "categorias": "Categorias", "produtos": "Produtos",
    "vendedores": "Vendedores", "segmentos": "Segmentos", "clientes": "Clientes",
}
TABELAS = {
    "clientes": "Clientes", "fornecedores": "Fornecedores", "categorias": "Categorias",
    "produtos": "Produtos", "filiais": "Filiais", "vendedores": "Vendedores",
    "pedidos": "Pedidos", "itens_venda": "Itens de venda", "despesas": "Despesas",
}
REGRAS = {
    "valor_fora_do_dominio": "Valor fora do domínio", "espacos_externos": "Espaços externos",
    "data_invalida": "Data inválida", "data_fora_da_janela": "Data fora da janela",
    "duplicata_exata": "Duplicata exata", "duplicata_conflitante": "Duplicata conflitante",
    "referencia_inexistente": "Referência inexistente", "inteiro_invalido": "Inteiro inválido",
    "valor_ausente": "Valor ausente",
}
MONETARIOS = {"bruto", "liquido", "lucro", "ticket", "desconto", "tributo", "custo", "media"}
PERCENTUAIS = {"margem", "mensal", "anual", "acumulado"}
CSS = """
<style>
.block-container {max-width: 1320px; padding-top: 2.4rem; padding-bottom: 2.5rem;}
section[data-testid="stSidebar"] {border-right: 1px solid #DDE6EE;}
.orz-hero {background: linear-gradient(110deg,#132540,#1A4056); color: #F7FBFF;
           padding: clamp(1rem,3vw,2rem); border-radius: 1rem; margin-bottom: .8rem;}
.orz-hero h1 {color: #FFFFFF; padding: .15rem 0; font-size: clamp(1.75rem,5vw,2.6rem);
              line-height: 1.2; letter-spacing: -.035em;}
.orz-hero p {color: #DDE8F0; margin-bottom: 0;}
.orz-hero .orz-marca {color: #9BE3D6; letter-spacing: .085em; font-size: .82rem; font-weight: 700;}
[data-testid="stMetric"] {background: white; border: 1px solid #DDE6EE;
                         border-radius: .85rem; padding: .9rem;}
.st-key-orz-cards [data-testid="stHorizontalBlock"] {
  display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,11rem),1fr));
}
.st-key-orz-cards [data-testid="stColumn"] {width:100% !important; min-width:0;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums; font-size:1.125rem;}
[data-testid="stAppDeployButton"] {display:none;}
[data-testid="stMetricLabel"] p {white-space: normal;}
@media (max-width: 640px) {
  .block-container {padding-left: 1rem; padding-right: 1rem;}
  .st-key-orz-cards [data-testid="stHorizontalBlock"] {display:grid; grid-template-columns: repeat(2,minmax(0,1fr));}
  [data-testid="stMetricValue"] {font-size:clamp(.78rem,3.6vw,1.05rem);}
}
</style>
"""


def numero(valor, casas=0):
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:,.{casas}f}".translate(str.maketrans(".,", ",."))


def reais(valor):
    return "—" if valor is None or pd.isna(valor) else f"R$ {numero(valor / 100, 2)}"


def percentual(valor):
    return "—" if valor is None or pd.isna(valor) else f"{numero(valor * 100, 1)}%"


def formatar(campo, valor):
    if campo in MONETARIOS:
        return reais(valor)
    if campo in PERCENTUAIS:
        return percentual(valor)
    return numero(valor, 2 if campo == "frequencia" else 0)


@st.cache_resource(show_spinner="Preparando a base comercial fictícia…")
def base_em_cache(raiz, assinatura):
    """Recarrega a base quando os manifestos locais mudam."""
    return carregar_demonstracao(raiz)


def carregar_base(raiz):
    arquivos = (
        raiz / "dados/processamento/base_padrao/manifesto.json",
        raiz / "dados/relatorios/base_padrao/perfil.json",
    )
    assinatura = tuple(arquivo.stat().st_mtime_ns if arquivo.is_file() else None for arquivo in arquivos)
    return base_em_cache(str(raiz), assinatura)


def cards(pares):
    with st.container(key="orz-cards"):
        for coluna, (rotulo, valor) in zip(st.columns(len(pares)), pares, strict=True):
            coluna.metric(rotulo, valor)


def cards_resumo(totais, campos):
    cards([(ROTULOS[campo], formatar(campo, totais[campo])) for campo in campos])


def tabela_exibicao(tabela, campos, adicionais=None):
    adicionais = adicionais or {}
    dados = tabela[campos].copy()
    for campo in dados:
        if campo in MONETARIOS | PERCENTUAIS | {"pedidos", "clientes", "observacoes"}:
            dados[campo] = dados[campo].map(lambda valor: formatar(campo, valor))
    st.dataframe(dados.rename(columns={**ROTULOS, **adicionais}), hide_index=True, use_container_width=True)


def plotar(figura, altura=330):
    figura.update_layout(
        height=altura, margin=dict(l=12, r=12, t=16, b=12), separators=",.",
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color="#15263C", size=14),
        hoverlabel=dict(bgcolor="#15263C", font_color="#FFFFFF"),
        legend=dict(orientation="h", y=1.03, yanchor="bottom", title_text=""),
    )
    figura.update_xaxes(gridcolor="#E5EBF1", zerolinecolor="#C8D4E0")
    figura.update_yaxes(gridcolor="#E5EBF1", zerolinecolor="#C8D4E0")
    st.plotly_chart(figura, use_container_width=True, config={"displayModeBar": False})


def serie_mensal(evolucao):
    serie = evolucao.copy()
    serie["Período"] = serie["mes"].map(lambda mes: f"{mes[5:]}/{mes[:4]}")
    serie["Receita (R$)"] = serie["liquido"] / 100
    serie["Valor"] = serie["liquido"].map(reais)
    fig = px.area(serie, x="Período", y="Receita (R$)", color_discrete_sequence=[CORES[0]],
                  custom_data=["Valor"])
    fig.update_traces(hovertemplate="%{x}<br>%{customdata[0]}<extra></extra>",
                      fillcolor="rgba(10,119,108,.13)")
    fig.update_xaxes(title=None, type="category", nticks=10)
    plotar(fig)


def ranking(tabela, entidade, medida="liquido", limite=10):
    dados = tabela.nlargest(limite, medida).sort_values(medida).copy()
    dados["Valor"] = dados[medida].map(reais)
    dados["R$"] = dados[medida] / 100
    fig = px.bar(dados, x="R$", y=entidade, orientation="h", custom_data=["Valor"],
                 color_discrete_sequence=[CORES[0]], labels={entidade: ROTULOS.get(entidade, entidade)})
    fig.update_traces(hovertemplate="%{y}<br>%{customdata[0]}<extra></extra>")
    fig.update_yaxes(title=None, automargin=True)
    plotar(fig, altura=max(270, 35 * len(dados) + 80))


def executiva(vendas, evolucao):
    cards_resumo(resumo(vendas), ["bruto", "liquido", "lucro", "margem", "ticket"])
    st.subheader("Evolução do faturamento líquido")
    serie_mensal(evolucao)
    st.subheader("Receita por filial")
    ranking(desempenho(vendas, "filial"), "filial")


def comercial(vendas, vendas_dimensoes, filtros, evolucao):
    totais = resumo(vendas)
    ultimo = evolucao.iloc[-1]
    cards([(ROTULOS["pedidos"], numero(totais["pedidos"])),
           (ROTULOS["mensal"], percentual(ultimo["mensal"])),
           (ROTULOS["anual"], percentual(ultimo["anual"]))])
    st.caption("Os cards de crescimento usam o último mês do recorte.")
    st.subheader("Evolução e comparação por mês")
    serie_mensal(evolucao)
    tabela = evolucao.assign(mes=evolucao["mes"].map(lambda mes: f"{mes[5:]}/{mes[:4]}"))
    tabela_exibicao(tabela, ["mes", "liquido", "mensal", "anual"])
    st.subheader("Sazonalidade por mês do calendário")
    sazonal = sazonalidade(vendas_dimensoes, filtros)
    if sazonal.empty:
        st.info("Selecione um período com pelo menos um mês completo.")
        return
    sazonal["Mês"] = sazonal["mes"].map(lambda mes: MESES[mes - 1])
    sazonal["Receita média (R$)"] = sazonal["media"] / 100
    sazonal["Valor"] = sazonal["media"].map(reais)
    fig = px.bar(sazonal, x="Mês", y="Receita média (R$)", color_discrete_sequence=[CORES[1]],
                 custom_data=["Valor", "observacoes"])
    fig.update_traces(hovertemplate="%{x}<br>%{customdata[0]}<br>%{customdata[1]} mês(es)<extra></extra>")
    plotar(fig)
    tabela_exibicao(sazonal, ["Mês", "media", "observacoes"])


def financeira(base, vendas, filtros):
    totais = resumo(vendas)
    cards_resumo(totais, ["liquido", "custo", "lucro", "margem"])
    st.subheader("Composição do faturamento e do lucro")
    fig = px.bar(
        x=[ROTULOS[campo] for campo in ("bruto", "desconto", "tributo", "liquido", "custo", "lucro")],
        y=[totais[campo] / 100 for campo in ("bruto", "desconto", "tributo", "liquido", "custo", "lucro")],
        labels={"x": "Componente", "y": "R$"}, color_discrete_sequence=[CORES[1]],
    )
    fig.update_traces(customdata=[reais(totais[c]) for c in ("bruto", "desconto", "tributo", "liquido", "custo", "lucro")],
                      hovertemplate="%{x}<br>%{customdata}<extra></extra>")
    plotar(fig)
    st.subheader("Resultado operacional gerencial")
    resultado, motivo = resultado_operacional(base, vendas, filtros)
    if resultado is None:
        st.info(motivo)
        return
    st.metric("Resultado operacional", reais(resultado["resultado"]))
    st.metric("Despesas operacionais", reais(resultado["despesas"]))
    st.dataframe(
        resultado["por_tipo"].map(reais).rename("Valor").rename_axis("Tipo de despesa").reset_index(),
        hide_index=True, use_container_width=True,
    )


def clientes(vendas):
    cards_resumo(resumo(vendas), ["clientes", "frequencia", "ticket"])
    st.subheader("Faturamento líquido por segmento")
    ranking(desempenho(vendas, "segmento"), "segmento")
    por_cliente = desempenho(vendas, ["cliente", "segmento"])
    st.subheader("Frequência de compra")
    distribuicao = por_cliente["pedidos"].value_counts().sort_index().rename_axis("Pedidos por cliente")
    fig = px.bar(distribuicao.rename("Clientes").reset_index(), x="Pedidos por cliente", y="Clientes",
                 color_discrete_sequence=[CORES[1]])
    plotar(fig)
    tabela_exibicao(por_cliente.sort_values("pedidos", ascending=False),
                    ["cliente", "segmento", "pedidos", "liquido", "ticket"])


def produtos(vendas):
    abc = curva_abc(vendas)
    st.subheader("Curva ABC por faturamento líquido")
    positivas = abc.loc[abc["acumulado"].notna()].reset_index(drop=True)
    if positivas.empty:
        st.info("Nenhum produto com faturamento líquido positivo neste recorte.")
    else:
        fig = px.line(positivas.assign(Posição=positivas.index + 1), x="Posição", y="acumulado",
                      custom_data=["produto", "classe"], labels={"acumulado": "Receita acumulada"},
                      color_discrete_sequence=[CORES[0]])
        fig.update_traces(hovertemplate="%{customdata[0]}<br>Classe %{customdata[1]} · %{y:.1%}<extra></extra>")
        fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
        for limite in (0.8, 0.95):
            fig.add_hline(y=limite, line_dash="dot", line_color=CORES[1])
        plotar(fig)
    st.subheader("Rentabilidade por produto")
    ranking(abc, "produto", "lucro")
    comuns = ["sku", "produto", "classe", "liquido", "acumulado", "lucro", "margem"]
    tabela_exibicao(abc.loc[abc["acumulado"].notna()], comuns)
    sem_receita = abc.loc[abc["acumulado"].isna()]
    if not sem_receita.empty:
        with st.expander("Produtos sem faturamento líquido positivo"):
            tabela_exibicao(sem_receita, comuns)


def comparacao(vendas, entidade):
    tabela = desempenho(vendas, entidade)
    st.subheader("Faturamento líquido por " + ROTULOS[entidade].lower())
    ranking(tabela, entidade)
    st.subheader("Evolução mensal")
    principais = tabela.head(5)[entidade]
    mensal = vendas.loc[vendas[entidade].isin(principais)].copy()
    mensal["mes"] = mensal["data_venda"].dt.to_period("M").astype(str)
    serie = mensal.groupby(["mes", entidade])["liquido"].sum().reset_index()
    meses = pd.period_range(mensal["mes"].min(), mensal["mes"].max(), freq="M").astype(str)
    grade = pd.MultiIndex.from_product([meses, principais], names=["mes", entidade])
    serie = serie.set_index(["mes", entidade]).reindex(grade, fill_value=0).reset_index()
    serie["Período"] = serie["mes"].map(lambda mes: f"{mes[5:]}/{mes[:4]}")
    serie["Receita (R$)"] = serie["liquido"] / 100
    serie["Valor"] = serie["liquido"].map(reais)
    fig = px.line(serie, x="Período", y="Receita (R$)", color=entidade,
                  color_discrete_sequence=CORES, custom_data=[entidade, "Valor"])
    fig.update_traces(hovertemplate="%{x}<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>")
    fig.update_xaxes(title=None, type="category", nticks=10)
    plotar(fig, altura=390)
    st.caption("Evolução das cinco maiores receitas no recorte.")
    tabela_exibicao(tabela, [entidade, "liquido", "lucro", "margem", "pedidos", "ticket"])


def qualidade(base):
    st.caption("Diagnóstico do lote completo. Seleções comerciais não se aplicam a este módulo.")
    tabelas = base.tratamento["tabelas"]
    cards([("Ocorrências detectadas", numero(base.qualidade["total_ocorrencias"])),
           ("Registros em quarentena", numero(sum(t["quarentena"] for t in tabelas.values()))),
           ("Cópias exatas excluídas", numero(sum(t["excluidos"] for t in tabelas.values()))),
           ("Pedidos com itens rejeitados", numero(base.tratamento["pedidos_parciais"]))])
    st.subheader("Reconciliação por tabela")
    linhas = [{"Tabela": TABELAS[nome], **{rotulo: numero(valores[campo]) for campo, rotulo in (
        ("brutos", "Brutos"), ("tratados", "Tratados"), ("quarentena", "Quarentena"),
        ("excluidos", "Excluídos"),
    )}} for nome, valores in tabelas.items()]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    st.subheader("Diagnóstico por regra")
    alvo = st.selectbox("Tabela bruta", list(TABELAS), index=list(TABELAS).index("itens_venda"),
                        format_func=TABELAS.__getitem__)
    perfil = base.qualidade["tabelas"][alvo]
    st.metric("Registros com ocorrências", percentual(perfil["taxa_registros_com_ocorrencias"]))
    regras = perfil["regras_com_ocorrencias"]
    if not regras:
        st.success("Nenhuma ocorrência detectada nesta tabela.")
        return
    detalhes = [{
        "Regra": REGRAS.get(regra["regra"], regra["regra"].replace("_", " ").capitalize()),
        "Campo": regra["campo"], "Ocorrências": numero(regra["ocorrencias"]),
        "Taxa": percentual(regra["taxa"]),
        "Exemplos": " · ".join(f"linha {e['ordinal_bruto']}: {e['valor_bruto'] or '(vazio)'}"
                              for e in regra["exemplos"]),
    } for regra in regras]
    st.dataframe(pd.DataFrame(detalhes), hide_index=True, use_container_width=True)


PAGINAS = (
    "Visão executiva", "Desempenho comercial", "Análise financeira", "Análise de clientes",
    "Desempenho dos produtos", "Comparação entre filiais", "Desempenho dos vendedores", "Qualidade dos dados",
)


def filtros_sidebar(vendas):
    with st.sidebar.expander("Filtros comerciais", expanded=True):
        limites = dict(min_value=pd.Timestamp(INICIO), max_value=pd.Timestamp(FIM), format="DD/MM/YYYY")
        inicio = st.date_input("Data inicial", pd.Timestamp(INICIO), key="filtro_inicio", **limites)
        fim = st.date_input("Data final", pd.Timestamp(FIM), key="filtro_fim", **limites)
        recortes = {
            atributo: tuple(st.multiselect(
                FILTRO_ROTULOS[atributo], sorted(vendas[campo].unique()),
                placeholder="Todos", key=f"filtro_{atributo}",
            )) for atributo, campo in CAMPOS_FILTRO.items()
        }
    if inicio is None or fim is None or inicio > fim:
        return None
    return Filtros(pd.Timestamp(inicio), pd.Timestamp(fim), **recortes)


def executar(raiz):
    st.set_page_config(page_title="Orizon Sales", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.sidebar.title("Orizon Sales")
    pagina = st.sidebar.radio("Módulos", PAGINAS)
    try:
        base = carregar_base(raiz)
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível carregar a base comercial. {erro}")
        return
    filtros = filtros_sidebar(base.vendas)
    st.markdown(
        f'<section class="orz-hero"><div class="orz-marca">ORIZON SALES</div>'
        f'<h1>{pagina}</h1><p>Distribuidora fictícia · Inteligência comercial</p></section>',
        unsafe_allow_html=True,
    )
    if pagina == PAGINAS[7]:
        qualidade(base)
        return
    if filtros is None:
        st.info("Selecione uma data inicial anterior ou igual à data final.")
        return
    st.caption(f"Período de {filtros.inicio:%d/%m/%Y} a {filtros.fim:%d/%m/%Y}")
    vendas_dimensoes = filtrar_dimensoes(base.vendas, filtros)
    vendas = no_periodo(vendas_dimensoes, filtros.inicio, filtros.fim)
    if vendas.empty and pagina != PAGINAS[2]:
        st.info("Nenhuma venda encontrada neste recorte.")
        return
    if pagina in PAGINAS[:2]:
        evolucao = crescimento(vendas_dimensoes, filtros, pd.Timestamp(INICIO), pd.Timestamp(FIM))
        if pagina == PAGINAS[0]:
            executiva(vendas, evolucao)
        else:
            comercial(vendas, vendas_dimensoes, filtros, evolucao)
    elif pagina == PAGINAS[2]:
        financeira(base, vendas, filtros)
    elif pagina == PAGINAS[3]:
        clientes(vendas)
    elif pagina == PAGINAS[4]:
        produtos(vendas)
    else:
        comparacao(vendas, "filial" if pagina == PAGINAS[5] else "vendedor")