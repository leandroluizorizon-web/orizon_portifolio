"""Diagnostica tabelas brutas sem consultar a trilha de injeção."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


VERSAO_REGRAS = "1"
INICIO, FIM = "2023-01-01", "2025-12-31"
COLUNAS = {
    "clientes": "cliente_id nome_cliente segmento municipio uf data_cadastro",
    "fornecedores": "fornecedor_id nome_fornecedor municipio uf",
    "categorias": "categoria_id nome_categoria",
    "produtos": "produto_id sku nome_produto categoria_id fornecedor_id",
    "filiais": "filial_id nome_filial municipio uf",
    "vendedores": "vendedor_id nome_vendedor filial_lotacao_id",
    "pedidos": "pedido_id data_venda cliente_id filial_id vendedor_id",
    "itens_venda": ("item_id pedido_id produto_id quantidade preco_unitario_centavos "
                   "desconto_centavos tributo_centavos custo_unitario_centavos"),
    "despesas": "despesa_id mes_competencia filial_id tipo_despesa valor_centavos",
}
PREFIXOS = {
    "cliente_id": "CLI", "fornecedor_id": "FOR", "categoria_id": "CAT", "produto_id": "PRO",
    "filial_id": "FIL", "filial_lotacao_id": "FIL", "vendedor_id": "VEN", "pedido_id": "PED",
    "item_id": "ITM", "despesa_id": "DES", "sku": "SKU",
}
REFERENCIAS = {
    "cliente_id": "clientes", "fornecedor_id": "fornecedores", "categoria_id": "categorias",
    "produto_id": "produtos", "filial_id": "filiais", "filial_lotacao_id": "filiais",
    "vendedor_id": "vendedores", "pedido_id": "pedidos",
}
DOMINIOS = {
    "segmento": {"Varejo", "Atacado", "Alimentação", "Serviços"},
    "tipo_despesa": {"Pessoal", "Aluguel", "Logística", "Utilidades", "Administração"},
    "uf": set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()),
}
DATAS = {"data_cadastro", "data_venda", "mes_competencia"}
CAMPOS_OCORRENCIA = (
    "arquivo", "ordinal_bruto", "chave_original", "dimensao", "regra", "campo",
    "valor_bruto", "exposicao", "valor_centavos",
)


def ler_tabela(caminho, colunas):
    """Preserva texto e a posição do registro lógico no CSV."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.reader(arquivo, strict=True)
        if next(leitor, None) != colunas:
            raise ValueError(f"Cabeçalho incompatível com o contrato: {caminho.name}")
        linhas = []
        for ordinal, linha in enumerate(leitor, 1):
            if len(linha) != len(colunas):
                raise ValueError(f"Quantidade de colunas inválida em {caminho.name}, registro {ordinal}.")
            linhas.append(linha)
    return pd.DataFrame(linhas, columns=colunas, dtype="string")


def inteiro_canonico(valor):
    """Converte um inteiro canônico dentro da faixa contratada."""
    if not valor.isascii() or not valor.isdecimal() or len(valor) > 19:
        return None
    numero = int(valor)
    return numero if numero <= 2**63 - 1 else None


def exposicao_financeira(tabela, linha):
    """Retorna o valor bruto observado, sem estimar o efeito da limpeza."""
    if tabela == "itens_venda":
        quantidade = inteiro_canonico(linha["quantidade"])
        preco = inteiro_canonico(linha["preco_unitario_centavos"])
        if quantidade and preco is not None:
            return "faturamento_bruto_da_linha", quantidade * preco
    if tabela == "despesas":
        valor = inteiro_canonico(linha["valor_centavos"])
        if valor:
            return "despesa_da_linha", valor
    return None, None


def verificar_tabela(nome, bruto, tabelas, registrar):
    """Aplica regras de campo, unicidade e integridade referencial."""
    chave = bruto.columns[0]
    limpo = bruto.apply(lambda coluna: coluna.str.strip())
    opcionais = {"municipio", "uf"} if nome in {"clientes", "fornecedores"} else set()
    datas = {}
    numeros = {}

    exatas = bruto.duplicated()
    conflitos = limpo.loc[~exatas, chave].duplicated(keep="first").reindex(bruto.index, fill_value=False)
    registrar(exatas, "unicidade", "duplicata_exata", chave)
    registrar(conflitos & limpo[chave].ne(""), "unicidade", "duplicata_conflitante", chave)

    for campo, valores in limpo.items():
        preenchido = valores.ne("")
        if campo not in opcionais:
            registrar(~preenchido, "completude", "valor_ausente", campo)
        registrar(preenchido & bruto[campo].ne(valores), "formato", "espacos_externos", campo)

        if campo in PREFIXOS:
            largura = 6 if campo in {"pedido_id", "item_id"} else 5
            formato = valores.str.fullmatch(rf"{PREFIXOS[campo]}-[0-9]{{{largura}}}")
            registrar(preenchido & ~formato, "formato", "codigo_invalido", campo)
            if campo != chave and campo in REFERENCIAS:
                destino = tabelas[REFERENCIAS[campo]]
                chaves = destino.iloc[:, 0].str.strip()
                registrar(formato & ~valores.isin(chaves), "integridade", "referencia_inexistente", campo)

        if campo in DOMINIOS:
            registrar(preenchido & ~valores.isin(DOMINIOS[campo]), "dominio", "valor_fora_do_dominio", campo)

        if campo in DATAS:
            formato = valores.str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
            validas = pd.to_datetime(valores.where(formato), format="%Y-%m-%d", errors="coerce")
            datas[campo] = validas
            registrar(preenchido & validas.isna(), "formato", "data_invalida", campo)
            if campo != "data_cadastro":
                fora = validas.notna() & ~valores.between(INICIO, FIM)
                registrar(fora, "dominio", "data_fora_da_janela", campo)
            if campo == "mes_competencia":
                registrar(validas.notna() & validas.dt.day.ne(1), "dominio", "competencia_invalida", campo)

        if campo == "quantidade" or campo.endswith("_centavos"):
            convertidos = pd.Series([inteiro_canonico(valor) for valor in valores],
                                    index=bruto.index, dtype=object)
            numeros[campo] = convertidos
            registrar(preenchido & convertidos.isna(), "formato", "inteiro_invalido", campo)
            if campo in {"quantidade", "valor_centavos"}:
                registrar(convertidos.eq(0), "dominio", "valor_deve_ser_positivo", campo)

        if campo in {"sku", "nome_categoria"}:
            registrar(preenchido & limpo[campo].duplicated(keep="first") & ~exatas,
                      "unicidade", "valor_repetido", campo)

    if opcionais:
        registrar(limpo["municipio"].eq("").ne(limpo["uf"].eq("")),
                  "completude", "localidade_incompleta", "municipio")

    if nome == "pedidos":
        clientes = tabelas["clientes"][["cliente_id", "data_cadastro"]].drop_duplicates()
        clientes = clientes.loc[~clientes["cliente_id"].duplicated(keep=False)]
        cadastro = pd.to_datetime(limpo["cliente_id"].map(clientes.set_index("cliente_id")["data_cadastro"]),
                                  format="%Y-%m-%d", errors="coerce")
        registrar(datas["data_venda"].lt(cadastro), "integridade", "venda_anterior_ao_cadastro", "data_venda")
        tem_item = limpo[chave].isin(tabelas["itens_venda"]["pedido_id"].str.strip())
        registrar(limpo[chave].ne("") & ~tem_item, "integridade", "pedido_sem_item_bruto", chave)

    if nome == "itens_venda":
        campos = ("quantidade", "preco_unitario_centavos", "desconto_centavos", "tributo_centavos")
        excede = [None not in (qtd, preco, desconto, tributo) and desconto + tributo > qtd * preco
                  for qtd, preco, desconto, tributo in zip(*(numeros[c] for c in campos), strict=True)]
        registrar(pd.Series(excede, index=bruto.index, dtype=bool),
                  "dominio", "deducoes_acima_do_bruto", "desconto_centavos")


def diagnosticar(origem, destino):
    """Persiste ocorrências e perfil, sem modificar os arquivos de entrada."""
    origem, destino = Path(origem).resolve(), Path(destino).resolve()
    if destino == origem or origem in destino.parents:
        raise ValueError("O relatório deve ficar fora do diretório dos dados brutos.")
    tabelas = {nome: ler_tabela(origem / f"{nome}.csv", campos.split())
               for nome, campos in COLUNAS.items()}
    perfis, ocorrencias = {}, []
    for nome, bruto in tabelas.items():
        arquivo = f"{nome}.csv"
        por_regra = defaultdict(list)
        afetados = set()

        def registrar(mascara, dimensao, regra, campo):
            for indice in mascara[mascara].index:
                linha = bruto.loc[indice]
                exposicao, valor = exposicao_financeira(nome, linha)
                evento = dict(arquivo=arquivo, ordinal_bruto=int(indice) + 1,
                              chave_original=linha.iloc[0], dimensao=dimensao, regra=regra,
                              campo=campo, valor_bruto=linha[campo], exposicao=exposicao,
                              valor_centavos=valor)
                ocorrencias.append(evento)
                por_regra[(dimensao, regra, campo)].append(evento)
                afetados.add(indice)

        verificar_tabela(nome, bruto, tabelas, registrar)
        total = len(bruto)
        with (origem / arquivo).open("rb") as entrada:
            resumo = hashlib.file_digest(entrada, "sha256").hexdigest()
        perfis[nome] = {
            "sha256": resumo, "registros": total, "registros_com_ocorrencias": len(afetados),
            "taxa_registros_com_ocorrencias": len(afetados) / total if total else None,
            "campos": {campo: {"ausentes": int(valores.str.strip().eq("").sum()),
                               "distintos_preenchidos": int(valores[valores.str.strip().ne("")].nunique())}
                       for campo, valores in bruto.items()},
            "regras_com_ocorrencias": [
                {"dimensao": dimensao, "regra": regra, "campo": campo, "ocorrencias": len(eventos),
                 "taxa": len(eventos) / total, "exemplos": eventos[:3],
                 "registros_com_exposicao_calculavel": sum(e["valor_centavos"] is not None for e in eventos)}
                for (dimensao, regra, campo), eventos in por_regra.items()
            ],
        }

    resultado = {"versao_regras": VERSAO_REGRAS, "total_ocorrencias": len(ocorrencias),
                 "tabelas": perfis}
    destino.mkdir(parents=True, exist_ok=True)
    with (destino / "ocorrencias.csv").open("w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=CAMPOS_OCORRENCIA, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(ocorrencias)
    with (destino / "perfil.json").open("w", encoding="utf-8") as saida:
        json.dump(resultado, saida, ensure_ascii=False, indent=2)
        saida.write("\n")
    return resultado


def main():
    parser = argparse.ArgumentParser(description="Diagnostica a qualidade dos dados brutos do Orizon Sales.")
    parser.add_argument("--origem", type=Path, default=Path("dados/brutos/base_padrao"))
    parser.add_argument("--destino", type=Path, default=Path("dados/relatorios/base_padrao"))
    args = parser.parse_args()
    try:
        perfil = diagnosticar(args.origem, args.destino)
    except (OSError, ValueError, csv.Error) as erro:
        parser.exit(2, f"Falha no diagnóstico: {erro}\n")
    print(f"{perfil['total_ocorrencias']} ocorrências em {len(perfil['tabelas'])} tabelas.")


if __name__ == "__main__":
    main()