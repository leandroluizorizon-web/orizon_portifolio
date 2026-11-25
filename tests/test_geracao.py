"""Verifica a geração, o diagnóstico e a publicação do lote tratado."""

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
from faker import Faker

from orizon_sales.geracao import gerar_base, gerar_cadastros, gerar_despesas, gerar_vendas
from orizon_sales.qualidade import diagnosticar
from orizon_sales.tratamento import hash_arquivo, tratar


def ler_csv(caminho):
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


class TestPipeline(unittest.TestCase):
    def test_base_valida(self):
        rng = np.random.default_rng(42)
        faker = Faker("pt_BR")
        faker.seed_instance(42)
        cadastros = gerar_cadastros(rng, faker)
        pedidos, itens = gerar_vendas(rng, 144, cadastros)
        despesas = gerar_despesas(rng)

        esperados = {"clientes": 5000, "produtos": 500, "filiais": 5, "vendedores": 30}
        self.assertEqual({nome: len(cadastros[nome]) for nome in esperados}, esperados)
        self.assertEqual(len(itens), 144)
        self.assertEqual(len({item["item_id"] for item in itens}), 144)
        self.assertEqual({p["pedido_id"] for p in pedidos}, {i["pedido_id"] for i in itens})
        self.assertEqual(len({p["data_venda"][:7] for p in pedidos}), 36)
        self.assertEqual(len({(d["mes_competencia"], d["filial_id"]) for d in despesas}), 180)
        for item in itens:
            bruto = item["quantidade"] * item["preco_unitario_centavos"]
            self.assertLessEqual(item["desconto_centavos"] + item["tributo_centavos"], bruto)

    def test_lote_reproduzivel_e_rastreavel(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            origem = pasta / "brutos"
            primeiro = gerar_base(origem, total_itens=144)
            segundo = gerar_base(pasta / "reproducao", total_itens=144)
            self.assertEqual(primeiro, segundo)
            self.assertEqual(primeiro["contagens"]["itens_venda"], {"antes_da_injecao": 144, "brutos": 146})
            self.assertEqual(len(primeiro["contagens"]), 9)
            tabelas = {nome: ler_csv(origem / f"{nome}.csv") for nome in primeiro["contagens"]}
            eventos = ler_csv(origem / "defeitos_injetados.csv")
            self.assertEqual(len(eventos), sum(regra["planejados"] for regra in primeiro["defeitos"]))
            for evento in eventos:
                linha = tabelas[evento["tabela"]][int(evento["ordinal_bruto"]) - 1]
                self.assertEqual(linha[evento["campo"]], evento["valor_injetado"])
                self.assertEqual(next(iter(linha.values())), evento["chave_original"])
            with self.assertRaises(FileExistsError):
                gerar_base(origem, total_itens=144)

            perfil = diagnosticar(origem, pasta / "diagnostico")
            self.assertEqual(perfil["total_ocorrencias"], len(eventos))
            destino = pasta / "processamento"
            manifesto = tratar(origem, destino)
            self.assertEqual(diagnosticar(destino / "tratados", pasta / "verificacao")["total_ocorrencias"], 0)
            itens = manifesto["tabelas"]["itens_venda"]
            self.assertEqual(itens["excluidos"], 1)
            conflito = next(e["chave_original"] for e in eventos if e["regra"] == "duplicata_conflitante")
            quarentena = ler_csv(destino / "quarentena" / "itens_venda.csv")
            self.assertEqual(sum(item["item_id"] == conflito for item in quarentena), 2)
            self.assertEqual(itens["brutos"], itens["tratados"] + itens["quarentena"] + itens["excluidos"])
            for arquivo, dados in primeiro["arquivos"].items():
                self.assertEqual(hash_arquivo(origem / arquivo), dados["sha256"])