"""Publica um relatório reproduzível de exploração da base demonstrativa."""

import argparse
from pathlib import Path

import pandas as pd

from .analise import Filtros, carregar, crescimento, curva_abc, desempenho, resumo, sazonalidade
from .qualidade import FIM, INICIO


def correlacao_spearman(receita, pedidos):
    try:
        from scipy.stats import spearmanr
    except ModuleNotFoundError as erro:
        if erro.name != "scipy":
            raise
        return receita.rank().corr(pedidos.rank()), "Pandas (correlação dos postos)"
    return spearmanr(receita, pedidos).statistic, "SciPy"


def numero(valor, casas=0):
    return f"{valor:,.{casas}f}".translate(str.maketrans(".,", ",."))


def reais(centavos):
    return "R$ " + numero(centavos / 100, 2)


def explorar(base):
    vendas = base.vendas
    inicio, fim = pd.Timestamp(INICIO), pd.Timestamp(FIM)
    filtros = Filtros(inicio, fim)
    totais = resumo(vendas)
    meses = vendas.groupby(vendas["data_venda"].dt.to_period("M")).agg(
        receita=("liquido", "sum"), pedidos=("pedido_id", "nunique"),
    )
    correlacao, implementacao = correlacao_spearman(meses["receita"], meses["pedidos"])
    ultimo = crescimento(vendas, filtros, inicio, fim).iloc[-1]
    sazonal = sazonalidade(vendas, filtros)
    pico = int(sazonal.loc[sazonal["media"].idxmax(), "mes"])
    menor = int(sazonal.loc[sazonal["media"].idxmin(), "mes"])
    abc = curva_abc(vendas)
    classe_a = abc.loc[abc["classe"].eq("A")]
    filial_lider = desempenho(vendas, "filial").iloc[0]
    pedidos_cliente = vendas.groupby("cliente_id")["pedido_id"].nunique()
    tickets = vendas.groupby("pedido_id")["liquido"].sum()
    despesas = base.cobertura["escopos_com_despesas_rejeitadas"]
    return f"""# Análise exploratória — Orizon Sales

Base tratada de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}, com {len(meses)} meses observados.

## Perfil comercial

- {numero(len(vendas))} itens em {numero(totais['pedidos'])} pedidos e {numero(totais['clientes'])} clientes ativos.
- Média de {numero(totais['frequencia'], 2)} pedidos por cliente ativo, com {numero(pedidos_cliente.eq(1).sum())} clientes que compraram uma vez.
- Ticket médio de {reais(totais['ticket'])}, mediana de {reais(tickets.median())} e percentil 90 de {reais(tickets.quantile(.9))}.
- {filial_lider['filial']} liderou as vendas, com {reais(filial_lider['liquido'])} de faturamento líquido.

## Receita e rentabilidade

- Faturamento bruto de {reais(totais['bruto'])} e líquido de {reais(totais['liquido'])}. Lucro bruto de {reais(totais['lucro'])} e margem de {numero(totais['margem'] * 100, 1)}%.
- A classe A reúne {len(classe_a)} de {len(abc)} produtos vendidos e responde por {numero(classe_a['liquido'].sum() / totais['liquido'] * 100, 1)}% da receita líquida.
- {len(despesas)} recortes de filial e competência têm despesas rejeitadas. Por isso, o resultado operacional do período integral fica indisponível.

## Evolução e sazonalidade

- {meses['receita'].idxmax().start_time:%m/%Y} registrou a maior receita líquida mensal. O último mês da janela variou {numero(ultimo['mensal'] * 100, 1)}% ante o mês anterior e {numero(ultimo['anual'] * 100, 1)}% ante o mesmo mês do ano anterior.
- O mês-calendário {pico:02d} apresentou a maior média e o mês {menor:02d}, a menor. Cada mês-calendário teve três observações completas.
- A correlação descritiva de Spearman entre receita líquida e número de pedidos nos 36 meses foi {numero(correlacao, 3)} ({implementacao}).

## Limitações

- {numero(base.tratamento['pedidos_parciais'])} pedidos permaneceram com apenas os itens aceitos. Os indicadores comerciais usam os valores desses itens.
- O gerador incorpora sazonalidade de volume, diferenças entre filiais e reajustes anuais. Os padrões encontrados descrevem esse cenário sintético.
"""


def main():
    parser = argparse.ArgumentParser(description="Gera o relatório exploratório da base tratada.")
    parser.add_argument("--lote", type=Path, default=Path("dados/processamento/base_padrao"))
    parser.add_argument("--diagnostico", type=Path, default=Path("dados/relatorios/base_padrao"))
    parser.add_argument("--saida", type=Path, default=Path("docs/analise_exploratoria.md"))
    args = parser.parse_args()
    relatorio = explorar(carregar(args.lote, args.diagnostico))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(relatorio, encoding="utf-8", newline="\n")
    print(f"Relatório exploratório salvo em {args.saida.resolve()}.")


if __name__ == "__main__":
    main()