"""Normaliza, valida e publica um lote tratado com trilha de auditoria."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from .qualidade import (
    COLUNAS,
    FIM,
    INICIO,
    REFERENCIAS,
    VERSAO_REGRAS as VERSAO_VALIDACAO,
    inteiro_canonico,
    ler_tabela,
    verificar_tabela,
)


VERSAO_REGRAS = "1"
VARIANTES_SEGMENTO = {
    "VAREJO": "Varejo",
    "atac.": "Atacado",
    "Alimentacao": "Alimentação",
    "Servicos": "Serviços",
}
DESTINOS = ("tratados", "quarentena", "excluidos")


def registrar(trilha, tabela, ordinal, chave, acao, regra, campo, antes="", depois=""):
    """Acrescenta um evento vinculado à posição lógica no arquivo bruto."""
    trilha.append(dict(arquivo=f"{tabela}.csv", ordinal_bruto=int(ordinal) + 1,
                       chave_original=chave, acao=acao, regra=regra,
                       campo=campo, valor_bruto=antes, valor_tratado=depois))


def normalizar(brutos, trilha):
    """Remove cópias exatas e aplica ajustes determinísticos aos candidatos."""
    tabelas, excluidos = {}, {}
    for nome, bruto in brutos.items():
        chave = bruto.columns[0]
        copia = bruto.duplicated()
        excluidos[nome] = bruto.index[copia]
        for indice in excluidos[nome]:
            valor = bruto.at[indice, chave]
            registrar(trilha, nome, indice, valor, "excluidos", "duplicata_exata", chave, valor)

        candidatos = bruto.loc[~copia]
        tabela = candidatos.apply(lambda coluna: coluna.str.strip())
        for campo in tabela.columns:
            for indice in tabela.index[tabela[campo].ne(candidatos[campo])]:
                registrar(trilha, nome, indice, bruto.at[indice, chave], "ajuste",
                          "remover_espacos_externos", campo, bruto.at[indice, campo],
                          tabela.at[indice, campo])

        if nome == "clientes":
            for indice in tabela.index[tabela["segmento"].isin(VARIANTES_SEGMENTO)]:
                anterior = tabela.at[indice, "segmento"]
                novo = VARIANTES_SEGMENTO[anterior]
                tabela.at[indice, "segmento"] = novo
                registrar(trilha, nome, indice, bruto.at[indice, chave], "ajuste",
                          "padronizar_segmento", "segmento", anterior, novo)
        tabelas[nome] = tabela
    return tabelas, excluidos


def selecionar_validos(tabelas, brutos, trilha):
    """Rejeita conflitos e propaga rejeições até preservar as referências."""
    motivos = {nome: {} for nome in tabelas}
    for nome, tabela in tabelas.items():
        chave = tabela.columns[0]

        def rejeitar(mascara, _dimensao, regra, campo):
            if regra in {"duplicata_exata", "duplicata_conflitante", "valor_repetido",
                         "pedido_sem_item_bruto"}:
                return
            for indice in mascara[mascara].index:
                motivos[nome].setdefault(indice, set()).add((regra, campo))

        verificar_tabela(nome, tabela, tabelas, rejeitar)

        # Nenhuma versão de uma chave conflitante tem precedência.
        for campo in (chave, *({"produtos": ("sku",), "categorias": ("nome_categoria",)}.get(nome, ()))):
            valores = tabela[campo]
            repetidos = valores.ne("") & valores.duplicated(keep=False)
            regra = "duplicata_conflitante" if campo == chave else "valor_repetido"
            for indice in tabela.index[repetidos]:
                motivos[nome].setdefault(indice, set()).add((regra, campo))

    aceitos = {}
    # A ordem do contrato coloca os cadastros antes das tabelas que os referenciam.
    for nome, tabela in tabelas.items():
        chave = tabela.columns[0]
        candidatos = tabela.drop(index=list(motivos[nome]))
        for campo in (set(candidatos.columns) & REFERENCIAS.keys()) - {chave}:
            alvo = aceitos[REFERENCIAS[campo]].iloc[:, 0]
            for indice in candidatos.index[~candidatos[campo].isin(alvo)]:
                motivos[nome].setdefault(indice, set()).add(("referencia_rejeitada", campo))
        aceitos[nome] = candidatos.drop(index=list(motivos[nome]), errors="ignore")

    pedidos = aceitos["pedidos"]
    sem_itens = ~pedidos["pedido_id"].isin(aceitos["itens_venda"]["pedido_id"])
    for indice in pedidos.index[sem_itens]:
        motivos["pedidos"].setdefault(indice, set()).add(("pedido_sem_item_valido", "pedido_id"))
    aceitos["pedidos"] = pedidos.loc[~sem_itens]

    for nome, rejeitados in motivos.items():
        bruto = brutos[nome]
        chave = bruto.columns[0]
        for indice, regras in sorted(rejeitados.items()):
            for regra, campo in sorted(regras):
                registrar(trilha, nome, indice, bruto.at[indice, chave],
                          "quarentena", regra, campo, bruto.at[indice, campo])
    return aceitos, motivos


def valores_financeiros(nome, tabela):
    """Apura valores calculáveis sem preencher lacunas ou inferir valores."""
    if nome == "despesas":
        return {"despesas": [inteiro_canonico(valor.strip()) for valor in tabela["valor_centavos"]]}

    medidas = dict(faturamento_bruto=[], faturamento_liquido=[], custo_mercadoria=[], lucro_bruto=[])
    campos = ("quantidade", "preco_unitario_centavos", "desconto_centavos",
              "tributo_centavos", "custo_unitario_centavos")
    for linha in tabela[list(campos)].itertuples(index=False, name=None):
        quantidade, preco, desconto, tributo, custo = map(inteiro_canonico, map(str.strip, linha))
        bruto = quantidade * preco if quantidade is not None and preco is not None else None
        liquido = bruto - desconto - tributo if None not in (bruto, desconto, tributo) else None
        custo_total = quantidade * custo if quantidade is not None and custo is not None else None
        lucro = liquido - custo_total if None not in (liquido, custo_total) else None
        for valores, valor in zip(medidas.values(), (bruto, liquido, custo_total, lucro), strict=True):
            valores.append(valor)
    return medidas


def reconciliar(brutos, aceitos, motivos, excluidos):
    """Compara a entrada com os três destinos, incluindo valores e lacunas."""
    resultado = {}
    for nome, bruto in brutos.items():
        indices = {
            "tratados": aceitos[nome].index,
            "quarentena": pd.Index(motivos[nome]),
            "excluidos": excluidos[nome],
        }
        particao = Counter(int(indice) for grupo in indices.values() for indice in grupo)
        if particao != Counter(bruto.index):
            raise ValueError(f"Os destinos não conciliam com os registros de {nome}.")

        resultado[nome] = dict(brutos=len(bruto), **{destino: len(indice) for destino, indice in indices.items()})
        if nome not in {"itens_venda", "despesas"}:
            continue
        valores_brutos = valores_financeiros(nome, bruto)
        valores_tratados = valores_financeiros(nome, aceitos[nome])
        medidas = {}
        for medida, valores in valores_brutos.items():
            grupos = {
                "brutos": valores,
                "tratados": valores_tratados[medida],
                **{destino: [valores[i] for i in indices[destino]] for destino in ("quarentena", "excluidos")},
            }
            saldos = {
                destino: {"centavos": sum(v for v in lista if v is not None),
                          "sem_valor_calculavel": lista.count(None)}
                for destino, lista in grupos.items()
            }
            for campo in ("centavos", "sem_valor_calculavel"):
                if saldos["brutos"][campo] != sum(saldos[d][campo] for d in DESTINOS):
                    raise ValueError(f"O saldo de {medida} não concilia em {campo}.")
            medidas[medida] = saldos
        resultado[nome]["reconciliacao_financeira"] = medidas
    return resultado


def resumir_cobertura(brutos, aceitos, motivos):
    """Localiza despesas não confiáveis e pedidos com itens rejeitados."""
    filiais = set(aceitos["filiais"]["filial_id"])
    meses = set(pd.date_range(INICIO, FIM, freq="MS").strftime("%Y-%m-%d"))
    despesas = aceitos["despesas"]
    pares = set(zip(despesas["mes_competencia"], despesas["filial_id"], strict=True))
    faltantes = {(mes, filial) for mes in meses for filial in filiais} - pares
    escopos = set()
    for indice in motivos["despesas"]:
        despesa = brutos["despesas"].loc[indice]
        mes = despesa["mes_competencia"].strip()
        filial = despesa["filial_id"].strip()
        escopos.add((mes if mes in meses else "", filial if filial in filiais else ""))

    itens_rejeitados = brutos["itens_venda"].loc[list(motivos["itens_venda"]), "pedido_id"].str.strip()
    parciais = aceitos["pedidos"]["pedido_id"].isin(itens_rejeitados)
    return {
        "pedidos_com_itens_rejeitados": aceitos["pedidos"].loc[parciais, "pedido_id"].tolist(),
        "pares_sem_despesas_tratadas": [{"mes": mes, "filial_id": filial} for mes, filial in sorted(faltantes)],
        "escopos_com_despesas_rejeitadas": [
            {"mes": mes or None, "filial_id": filial or None} for mes, filial in sorted(escopos)
        ],
    }


def hash_arquivo(caminho):
    with caminho.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def tratar(origem, destino):
    """Publica dados tratados, quarentena e relatórios como um lote indivisível."""
    origem, destino = Path(origem).resolve(), Path(destino).resolve()
    if destino == origem or origem in destino.parents:
        raise ValueError("O tratamento deve ficar fora do diretório dos dados brutos.")
    if destino.exists():
        raise FileExistsError(f"O destino já existe: {destino}")
    brutos = {}
    hashes_brutos = {}
    for nome, campos in COLUNAS.items():
        arquivo = origem / f"{nome}.csv"
        hashes_brutos[arquivo.name] = hash_arquivo(arquivo)
        brutos[nome] = ler_tabela(arquivo, campos.split())
        if hash_arquivo(arquivo) != hashes_brutos[arquivo.name]:
            raise ValueError(f"O arquivo bruto mudou durante a leitura: {arquivo.name}")

    trilha = []
    normalizados, excluidos = normalizar(brutos, trilha)
    aceitos, motivos = selecionar_validos(normalizados, brutos, trilha)
    resumo = reconciliar(brutos, aceitos, motivos, excluidos)
    cobertura = resumir_cobertura(brutos, aceitos, motivos)
    manifesto = {
        "versao_contrato": "1", "versao_tratamento": VERSAO_REGRAS,
        "versao_validacao": VERSAO_VALIDACAO, "hashes_brutos": hashes_brutos,
        "tabelas": resumo,
        "eventos_por_regra": dict(sorted(Counter(evento["regra"] for evento in trilha).items())),
        "pedidos_parciais": len(cobertura["pedidos_com_itens_rejeitados"]),
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destino.parent, prefix=".tratamento-") as temporario:
        lote = Path(temporario) / "lote"
        for pasta in ("tratados", "quarentena", "relatorios"):
            (lote / pasta).mkdir(parents=True)
        for nome, tratado in aceitos.items():
            tratado.to_csv(lote / "tratados" / f"{nome}.csv", index=False, lineterminator="\n")
            rejeitados = brutos[nome].loc[sorted(motivos[nome])].copy()
            rejeitados.insert(0, "ordinal_bruto", rejeitados.index + 1)
            rejeitados.to_csv(lote / "quarentena" / f"{nome}.csv", index=False, lineterminator="\n")

        campos = ("arquivo", "ordinal_bruto", "chave_original", "acao", "regra",
                  "campo", "valor_bruto", "valor_tratado")
        ordem = lambda evento: (evento["arquivo"], evento["ordinal_bruto"], evento["acao"],
                                evento["regra"], evento["campo"])
        with (lote / "relatorios" / "transformacoes.csv").open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator="\n")
            escritor.writeheader()
            escritor.writerows(sorted(trilha, key=ordem))
        gravar_json(lote / "relatorios" / "cobertura.json", cobertura)
        manifesto["hashes_saida"] = {
            caminho.relative_to(lote).as_posix(): hash_arquivo(caminho)
            for caminho in sorted(lote.glob("*/*"))
        }
        gravar_json(lote / "manifesto.json", manifesto)
        lote.rename(destino)
    return manifesto


def gravar_json(caminho, documento):
    caminho.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Trata os dados brutos do Orizon Sales.")
    parser.add_argument("--origem", type=Path, default=Path("dados/brutos/base_padrao"))
    parser.add_argument("--destino", type=Path, default=Path("dados/processamento/base_padrao"))
    args = parser.parse_args()
    try:
        manifesto = tratar(args.origem, args.destino)
    except (OSError, ValueError, csv.Error) as erro:
        parser.exit(2, f"Falha no tratamento: {erro}\n")
    print(f"Lote tratado em {args.destino.resolve()}.")
    for nome, contagens in manifesto["tabelas"].items():
        print(f"{nome}: {contagens['tratados']} tratados, {contagens['quarentena']} em quarentena, "
              f"{contagens['excluidos']} excluídos.")


if __name__ == "__main__":
    main()