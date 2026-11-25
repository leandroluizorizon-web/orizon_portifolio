"""Gera uma base comercial fictícia e preserva cada execução bruta."""

import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from importlib.metadata import version
from itertools import accumulate
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from faker import Faker


INICIO = date(2023, 1, 1)
FIM = date(2025, 12, 31)
VERSAO_GERADOR = "1"
LOCALIDADES = (("Fortaleza", "CE"), ("Recife", "PE"), ("Natal", "RN"),
               ("João Pessoa", "PB"), ("Teresina", "PI"))
CATEGORIAS = ("Mercearia", "Bebidas", "Higiene", "Limpeza", "Embalagens")
SEGMENTOS = ("Varejo", "Atacado", "Alimentação", "Serviços")
TIPOS_DESPESA = ("Pessoal", "Aluguel", "Logística", "Utilidades", "Administração")
MESES = tuple(date(ano, mes, 1) for ano in range(2023, 2026) for mes in range(1, 13))
FATORES_MENSAIS = np.array([0.91, 0.88, 0.99, 0.98, 1.02, 1.09,
                           0.96, 1.00, 1.03, 1.07, 1.19, 1.34])


def codigo(prefixo, numero, largura=5):
    """Formata a chave canônica sem eliminar zeros à esquerda."""
    return f"{prefixo}-{numero:0{largura}d}"


def escolher_dias(rng, total):
    """Distribui pedidos com crescimento gradual e sazonalidade de volume."""
    dias = [INICIO + timedelta(days=i) for i in range((FIM - INICIO).days + 1)]
    pesos = np.array([FATORES_MENSAIS[dia.month - 1] * (1 + 0.10 * (dia.year - 2023))
                      for dia in dias])
    # Reserva um pedido por competência para garantir cobertura em toda execução.
    sorteados = rng.choice(dias, size=total - len(MESES), p=pesos / pesos.sum())
    return sorted([*MESES, *sorteados])


def gerar_cadastros(rng, faker):
    """Monta dimensões e associa cada cliente a uma carteira na simulação."""
    clientes = []
    for numero in range(1, 5001):
        municipio, uf = LOCALIDADES[(numero - 1) % len(LOCALIDADES)]
        cadastro = INICIO - timedelta(days=int(rng.integers(1, 1461)))
        clientes.append(dict(cliente_id=codigo("CLI", numero),
                             nome_cliente=f"Cliente Fictício {numero:05d} — {faker.first_name()}",
                             segmento=str(rng.choice(SEGMENTOS)), municipio=municipio, uf=uf,
                             data_cadastro=cadastro.isoformat()))

    fornecedores = [
        dict(fornecedor_id=codigo("FOR", numero), nome_fornecedor=f"Fornecedor Fictício {numero:02d}",
             municipio=municipio, uf=uf)
        for numero, (municipio, uf) in enumerate(LOCALIDADES * 5, start=1)
    ]
    categorias = [dict(categoria_id=codigo("CAT", numero), nome_categoria=nome)
                  for numero, nome in enumerate(CATEGORIAS, start=1)]
    produtos = [
        dict(produto_id=codigo("PRO", numero), sku=codigo("SKU", numero),
             nome_produto=f"{categoria['nome_categoria']} — Produto {numero:03d}",
             categoria_id=categoria["categoria_id"],
             fornecedor_id=fornecedores[(numero - 1) % len(fornecedores)]["fornecedor_id"])
        for numero in range(1, 501)
        for categoria in [categorias[(numero - 1) % len(categorias)]]
    ]
    filiais = [dict(filial_id=codigo("FIL", numero), nome_filial=f"Filial {municipio}",
                    municipio=municipio, uf=uf)
               for numero, (municipio, uf) in enumerate(LOCALIDADES, start=1)]
    vendedores = [
        dict(vendedor_id=codigo("VEN", numero),
             nome_vendedor=f"Vendedor Fictício {numero:02d} — {faker.first_name()}",
             filial_lotacao_id=filiais[(numero - 1) // 6]["filial_id"])
        for numero in range(1, 31)
    ]
    return dict(clientes=clientes, fornecedores=fornecedores, categorias=categorias,
                produtos=produtos, filiais=filiais, vendedores=vendedores)


def gerar_vendas(rng, total_itens, cadastros):
    """Gera pedidos com um a quatro itens e preços e custos históricos."""
    tamanhos = rng.choice([1, 2, 3, 4], size=total_itens, p=[0.30, 0.38, 0.23, 0.09])
    limites = [limite for limite in accumulate(map(int, tamanhos)) if limite < total_itens]
    faixas = list(zip([0, *limites], [*limites, total_itens]))
    dias = escolher_dias(rng, len(faixas))

    atividade = rng.lognormal(mean=0, sigma=1, size=5000)
    clientes = rng.choice(5000, size=len(faixas), p=atividade / atividade.sum())
    pesos = np.arange(1, 501, dtype=float) ** -0.82
    rng.shuffle(pesos)
    indices_produto = rng.choice(500, size=total_itens, p=pesos / pesos.sum())
    precos = rng.integers(450, 24001, size=500)
    proporcoes_custo = rng.integers(52, 82, size=500)
    quantidades = rng.integers(1, 19, size=total_itens)
    descontos = rng.choice([0, 3, 5, 8, 12], size=total_itens, p=[0.48, 0.20, 0.17, 0.10, 0.05])
    tributos = rng.choice([4, 7, 10, 12, 15], size=total_itens)
    regioes = rng.choice(5, size=len(faixas), p=[0.30, 0.25, 0.19, 0.15, 0.11])
    vendedores = rng.integers(0, 6, size=len(faixas))
    transferencias = rng.random(len(faixas)) < 0.04

    pedidos, itens = [], []
    for indice, ((inicio, fim), dia) in enumerate(zip(faixas, dias, strict=True)):
        filial = int(regioes[indice])
        lotacao = (filial + int(transferencias[indice])) % len(LOCALIDADES)
        pedido_id = codigo("PED", indice + 1, 6)
        pedidos.append(dict(pedido_id=pedido_id, data_venda=dia.isoformat(),
                            cliente_id=cadastros["clientes"][clientes[indice]]["cliente_id"],
                            filial_id=codigo("FIL", filial + 1),
                            vendedor_id=codigo("VEN", lotacao * 6 + int(vendedores[indice]) + 1)))
        reajuste = 100 + 5 * (dia.year - INICIO.year)
        for i in range(inicio, fim):
            produto = int(indices_produto[i])
            preco = (int(precos[produto]) * reajuste + 50) // 100
            quantidade = int(quantidades[i])
            bruto = quantidade * preco
            itens.append(dict(item_id=codigo("ITM", i + 1, 6), pedido_id=pedido_id,
                              produto_id=cadastros["produtos"][produto]["produto_id"],
                              quantidade=quantidade, preco_unitario_centavos=preco,
                              desconto_centavos=(bruto * int(descontos[i]) + 50) // 100,
                              tributo_centavos=(bruto * int(tributos[i]) + 50) // 100,
                              custo_unitario_centavos=(preco * int(proporcoes_custo[produto]) + 50) // 100))
    return pedidos, itens


def gerar_despesas(rng):
    """Gera cinco tipos de despesa em cada par de filial e competência."""
    despesas = []
    for mes in MESES:
        for filial in range(1, 6):
            for tipo, base in zip(TIPOS_DESPESA, (920000, 350000, 480000, 120000, 175000), strict=True):
                valor = base * (120 - filial * 6 + int(rng.integers(-10, 11))) // 100
                despesas.append(dict(despesa_id=codigo("DES", len(despesas) + 1),
                                     mes_competencia=mes.isoformat(), filial_id=codigo("FIL", filial),
                                     tipo_despesa=tipo, valor_centavos=valor))
    return despesas


def escrever_csv(caminho, linhas):
    """Escreve o cabeçalho de acordo com a ordem contratada das colunas."""
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def gerar_base(destino, semente=42, semente_defeitos=137, total_itens=100_000):
    """Publica a execução inteira em um novo diretório e retorna o manifesto."""
    from .inconsistencias import injetar

    if not 144 <= total_itens <= 999_000:
        raise ValueError("A quantidade de itens deve estar entre 144 e 999.000.")
    if min(semente, semente_defeitos) < 0:
        raise ValueError("As sementes devem ser inteiros não negativos.")

    destino = Path(destino)
    if destino.exists():
        raise FileExistsError(f"O destino já existe: {destino}")
    rng = np.random.default_rng(semente)
    faker = Faker("pt_BR")
    faker.seed_instance(semente)
    tabelas = gerar_cadastros(rng, faker)
    tabelas["pedidos"], tabelas["itens_venda"] = gerar_vendas(rng, total_itens, tabelas)
    tabelas["despesas"] = gerar_despesas(rng)
    contagens = {nome: len(linhas) for nome, linhas in tabelas.items()}
    defeitos, configuracao = injetar(tabelas, np.random.default_rng(semente_defeitos))

    destino.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destino.parent, prefix=".geracao-") as temporario:
        lote = Path(temporario) / "lote"
        lote.mkdir()
        arquivos = {}
        for nome, linhas in {**tabelas, "defeitos_injetados": defeitos}.items():
            caminho = lote / f"{nome}.csv"
            escrever_csv(caminho, linhas)
            with caminho.open("rb") as arquivo:
                resumo = hashlib.file_digest(arquivo, "sha256").hexdigest()
            arquivos[caminho.name] = {"registros": len(linhas), "sha256": resumo}

        manifesto = {
            "versao_contrato": "1", "versao_gerador": VERSAO_GERADOR,
            "dependencias": {nome: version(nome) for nome in ("Faker", "numpy", "tzdata")},
            "sementes": {"base": semente, "defeitos": semente_defeitos},
            "janela": {"inicio": INICIO.isoformat(), "fim": FIM.isoformat()},
            "contagens": {nome: {"antes_da_injecao": antes, "brutos": len(tabelas[nome])}
                          for nome, antes in contagens.items()},
            "defeitos": configuracao, "arquivos": arquivos,
        }
        with (lote / "manifesto.json").open("w", encoding="utf-8", newline="\n") as arquivo:
            json.dump(manifesto, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        # O lote só aparece no destino depois que todos os arquivos foram gravados.
        lote.rename(destino)
    return manifesto


def main():
    """Executa a geração pela linha de comando."""
    parser = argparse.ArgumentParser(description="Gera os dados brutos do Orizon Sales.")
    parser.add_argument("--destino", type=Path, default=Path("dados/brutos/base_padrao"))
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--semente-defeitos", type=int, default=137)
    parser.add_argument("--itens", type=int, default=100_000)
    args = parser.parse_args()
    try:
        manifesto = gerar_base(args.destino, args.semente, args.semente_defeitos, args.itens)
    except (ValueError, OSError) as erro:
        parser.exit(2, f"Falha na geração: {erro}\n")
    total = manifesto["contagens"]["itens_venda"]["brutos"]
    print(f"Base publicada em {args.destino.resolve()} com {total:,} itens brutos.".replace(",", "."))


if __name__ == "__main__":
    main()