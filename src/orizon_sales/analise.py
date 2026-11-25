"""Carrega fatos comerciais e calcula indicadores em centavos."""

import json
from calendar import monthrange
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MEDIDAS = ("bruto", "desconto", "tributo", "liquido", "custo", "lucro")


@dataclass(frozen=True)
class BaseComercial:
    vendas: pd.DataFrame
    despesas: pd.DataFrame
    cobertura: dict
    tratamento: dict
    qualidade: dict


@dataclass(frozen=True)
class Filtros:
    inicio: pd.Timestamp
    fim: pd.Timestamp
    filiais: tuple = ()
    categorias: tuple = ()
    produtos: tuple = ()
    vendedores: tuple = ()
    segmentos: tuple = ()
    clientes: tuple = ()


CAMPOS_FILTRO = {
    "filiais": "filial", "categorias": "categoria", "produtos": "produto",
    "vendedores": "vendedor", "segmentos": "segmento", "clientes": "cliente",
}


def ler_json(caminho):
    return caminho.read_text(encoding="utf-8")


def carregar(lote, diagnostico):
    """Monta o fato na granularidade do item com junções de muitos para um."""
    lote, diagnostico = Path(lote), Path(diagnostico)
    tratados = lote / "tratados"

    def ler(tabela, **opcoes):
        return pd.read_csv(tratados / f"{tabela}.csv", keep_default_na=False, **opcoes)

    pedidos = ler("pedidos", parse_dates=["data_venda"])
    itens = ler("itens_venda")
    vendas = itens.merge(pedidos, on="pedido_id", validate="many_to_one")
    for tabela, chave, campos in (
        ("produtos", "produto_id", ["sku", "nome_produto", "categoria_id"]),
        ("categorias", "categoria_id", ["nome_categoria"]),
        ("filiais", "filial_id", ["nome_filial"]),
        ("vendedores", "vendedor_id", ["nome_vendedor"]),
        ("clientes", "cliente_id", ["nome_cliente", "segmento"]),
    ):
        vendas = vendas.merge(ler(tabela)[[chave, *campos]], on=chave, validate="many_to_one")

    if len(vendas) != len(itens):
        raise ValueError("Existem itens tratados sem correspondência nos cadastros ou pedidos.")
    # Os códigos distinguem cadastros que compartilham o mesmo nome.
    renomear = {
        "cliente": "cliente_id", "produto": "sku", "filial": "filial_id",
        "vendedor": "vendedor_id", "categoria": "categoria_id",
    }
    for entidade, codigo in renomear.items():
        vendas[entidade] = vendas[f"nome_{entidade}"] + " · " + vendas[codigo]

    vendas["bruto"] = vendas["quantidade"] * vendas["preco_unitario_centavos"]
    vendas["desconto"] = vendas["desconto_centavos"]
    vendas["tributo"] = vendas["tributo_centavos"]
    vendas["liquido"] = vendas["bruto"] - vendas["desconto"] - vendas["tributo"]
    vendas["custo"] = vendas["quantidade"] * vendas["custo_unitario_centavos"]
    vendas["lucro"] = vendas["liquido"] - vendas["custo"]
    return BaseComercial(
        vendas, ler("despesas", parse_dates=["mes_competencia"]),
        json.loads(ler_json(lote / "relatorios" / "cobertura.json")),
        json.loads(ler_json(lote / "manifesto.json")),
        json.loads(ler_json(diagnostico / "perfil.json")),
    )


def filtrar_dimensoes(vendas, filtros):
    """Mantém o mesmo recorte comercial nas séries e nas referências."""
    for atributo, campo in CAMPOS_FILTRO.items():
        selecao = getattr(filtros, atributo)
        if selecao:
            vendas = vendas.loc[vendas[campo].isin(selecao)]
    return vendas


def no_periodo(vendas, inicio, fim):
    return vendas.loc[vendas["data_venda"].between(inicio, fim)]


def razao(numerador, denominador):
    return float(numerador / denominador) if denominador else None


def resumo(vendas):
    """Calcula totais, margem ponderada e ticket de pedidos distintos."""
    totais = {campo: int(vendas[campo].sum()) for campo in MEDIDAS}
    pedidos = vendas["pedido_id"].nunique()
    clientes = vendas["cliente_id"].nunique()
    return {
        **totais, "pedidos": pedidos, "clientes": clientes,
        "margem": razao(totais["lucro"], totais["liquido"]),
        "ticket": razao(totais["liquido"], pedidos),
        "frequencia": razao(pedidos, clientes),
    }


def desempenho(vendas, campos):
    """Agrega itens por dimensão preservando a granularidade dos pedidos."""
    grupos = vendas.groupby(campos, observed=True, dropna=False)
    tabela = grupos[list(MEDIDAS)].sum()
    tabela["pedidos"] = grupos["pedido_id"].nunique()
    tabela["clientes"] = grupos["cliente_id"].nunique()
    tabela["margem"] = tabela["lucro"].div(tabela["liquido"].where(tabela["liquido"].ne(0)))
    tabela["ticket"] = tabela["liquido"].div(tabela["pedidos"].where(tabela["pedidos"].ne(0)))
    return tabela.reset_index().sort_values("liquido", ascending=False, kind="stable")


def meses_do_recorte(inicio, fim):
    return pd.period_range(inicio, fim, freq="M")


def mes_completo(mes, inicio, fim):
    return inicio <= mes.start_time and mes.end_time.normalize() <= fim


def crescimento(vendas, filtros, cobertura_inicio, cobertura_fim):
    """Compara cada mês com o anterior e com o mesmo mês do ano anterior."""
    registros = []
    for mes in meses_do_recorte(filtros.inicio, filtros.fim):
        inicio = max(mes.start_time, filtros.inicio)
        fim = min(mes.end_time.normalize(), filtros.fim)
        atual = int(no_periodo(vendas, inicio, fim)["liquido"].sum())
        registro = {"mes": str(mes), "liquido": atual}
        for coluna, deslocamento in (("mensal", 1), ("anual", 12)):
            referencia = mes - deslocamento
            primeiro, ultimo = referencia.start_time, referencia.end_time.normalize()
            if not mes_completo(mes, inicio, fim):
                if fim.day > monthrange(primeiro.year, primeiro.month)[1]:
                    registro[coluna] = None
                    continue
                primeiro += pd.Timedelta(days=inicio.day - 1)
                ultimo = referencia.start_time + pd.Timedelta(days=fim.day - 1)
            comparavel = cobertura_inicio <= primeiro <= ultimo <= cobertura_fim
            anterior = int(no_periodo(vendas, primeiro, ultimo)["liquido"].sum()) if comparavel else 0
            registro[coluna] = razao(atual - anterior, anterior)
        registros.append(registro)
    return pd.DataFrame(registros)


def sazonalidade(vendas, filtros):
    """Inclui meses completos sem vendas como zero na média do mês-calendário."""
    recorte = no_periodo(vendas, filtros.inicio, filtros.fim)
    serie = recorte.groupby(recorte["data_venda"].dt.to_period("M"))["liquido"].sum()
    completos = [mes for mes in meses_do_recorte(filtros.inicio, filtros.fim)
                 if mes_completo(mes, filtros.inicio, filtros.fim)]
    linhas = serie.reindex(completos, fill_value=0).rename("liquido").to_frame()
    linhas["mes"] = [mes.month for mes in completos]
    return linhas.groupby("mes")["liquido"].agg(media="mean", observacoes="size").reset_index()


def curva_abc(vendas):
    """Classifica cada produto pelo acumulado anterior, com desempate pelo SKU."""
    tabela = desempenho(vendas, ["sku", "produto"]).sort_values(
        ["liquido", "sku"], ascending=[False, True]
    )
    positivos = tabela["liquido"].gt(0)
    tabela["classe"] = "Sem receita positiva"
    tabela["acumulado"] = float("nan")
    if positivos.any():
        receita = tabela.loc[positivos, "liquido"]
        acumulado = receita.cumsum()
        total = int(receita.sum())
        # A comparação inteira mantém a fronteira de 80% e 95% exata.
        anterior = (acumulado - receita).map(int).astype(object) * 100
        classes = anterior.map(lambda valor: "A" if valor < 80 * total else "B" if valor < 95 * total else "C")
        tabela.loc[positivos, "classe"] = classes
        tabela.loc[positivos, "acumulado"] = acumulado / total
    return tabela


def resultado_operacional(base, vendas, filtros):
    """Exibe lucro menos despesas apenas onde competência e cobertura são válidas."""
    if any(getattr(filtros, atributo) for atributo in CAMPOS_FILTRO if atributo != "filiais"):
        return None, "Use apenas filtros de período e filial para incluir despesas."
    meses = meses_do_recorte(filtros.inicio, filtros.fim)
    if not all(mes_completo(mes, filtros.inicio, filtros.fim) for mes in meses):
        return None, "Selecione apenas meses completos para incluir despesas."

    datas = {mes.start_time.date().isoformat() for mes in meses}
    despesas = base.despesas
    filiais = {rotulo.rsplit(" · ", 1)[-1] for rotulo in filtros.filiais}
    if not filiais:
        filiais = set(base.vendas["filial_id"]) | set(despesas["filial_id"])
    for chave in ("pares_sem_despesas_tratadas", "escopos_com_despesas_rejeitadas"):
        for escopo in base.cobertura[chave]:
            if escopo["mes"] in datas | {None} and escopo["filial_id"] in filiais | {None}:
                return None, "Há despesas ausentes ou rejeitadas no período e nas filiais selecionadas."

    validas = despesas["mes_competencia"].between(filtros.inicio, filtros.fim)
    validas &= despesas["filial_id"].isin(filiais)
    por_tipo = despesas.loc[validas].groupby("tipo_despesa")["valor_centavos"].sum()
    total = int(por_tipo.sum())
    return {"despesas": total, "resultado": int(vendas["lucro"].sum()) - total,
            "por_tipo": por_tipo}, None