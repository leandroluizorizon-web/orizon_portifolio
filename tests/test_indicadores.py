"""Exercita regras de indicadores e fluxos da aplicação demonstrativa."""

import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from orizon_sales.analise import (
    BaseComercial, Filtros, crescimento, curva_abc, no_periodo,
    resultado_operacional, resumo, sazonalidade,
)
from orizon_sales.visualizacao import PAGINAS


def vendas_exemplo():
    dados = pd.DataFrame([
        ("2025-01-10", "PED-1", "CLI-1", "SKU-1", 8000),
        ("2025-01-10", "PED-1", "CLI-1", "SKU-2", 1500),
        ("2025-02-10", "PED-2", "CLI-1", "SKU-3", 500),
        ("2025-02-15", "PED-3", "CLI-2", "SKU-4", 0),
    ], columns=["data_venda", "pedido_id", "cliente_id", "sku", "liquido"])
    dados["data_venda"] = pd.to_datetime(dados["data_venda"])
    dados["produto"] = dados["sku"]
    dados["filial_id"] = "FIL-00001"
    dados["desconto"] = 0
    dados["tributo"] = 0
    dados["bruto"] = dados["liquido"]
    dados["custo"] = dados["liquido"] // 2
    dados["lucro"] = dados["liquido"] - dados["custo"]
    return dados


class TestIndicadores(unittest.TestCase):
    def setUp(self):
        self.vendas = vendas_exemplo()

    def test_margem_ticket_e_classes_abc(self):
        totais = resumo(self.vendas)
        self.assertEqual(totais["pedidos"], 3)
        self.assertAlmostEqual(totais["ticket"], 10_000 / 3)
        self.assertEqual(totais["margem"], .5)
        self.assertEqual(totais["frequencia"], 1.5)
        self.assertEqual(curva_abc(self.vendas)["classe"].tolist(),
                         ["A", "B", "C", "Sem receita positiva"])

    def test_periodos_parciais_usam_os_mesmos_dias(self):
        filtros = Filtros(pd.Timestamp("2025-02-02"), pd.Timestamp("2025-02-12"))
        serie = crescimento(self.vendas, filtros, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-28"))
        self.assertAlmostEqual(serie.iloc[0]["mensal"], (500 - 9500) / 9500)
        self.assertIsNone(serie.iloc[0]["anual"])
        self.assertTrue(sazonalidade(self.vendas, filtros).empty)

    def test_despesas_exigem_cobertura_e_mes_completo(self):
        despesas = pd.DataFrame({
            "mes_competencia": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "filial_id": ["FIL-00001", "FIL-00001"],
            "tipo_despesa": ["Aluguel", "Aluguel"],
            "valor_centavos": [1000, 1500],
        })
        cobertura = {
            "pares_sem_despesas_tratadas": [],
            "escopos_com_despesas_rejeitadas": [{"mes": "2025-02-01", "filial_id": "FIL-00001"}],
        }
        base = BaseComercial(self.vendas, despesas, cobertura, {}, {})
        janeiro = Filtros(pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-31"))
        vendas = no_periodo(self.vendas, janeiro.inicio, janeiro.fim)
        indicador, motivo = resultado_operacional(base, vendas, janeiro)
        self.assertIsNone(motivo)
        self.assertEqual(indicador["resultado"], 3750)
        for filtros in (
            Filtros(janeiro.inicio, pd.Timestamp("2025-01-15")),
            Filtros(janeiro.inicio, janeiro.fim, vendedores=("VEN-01",)),
            Filtros(janeiro.inicio, pd.Timestamp("2025-02-28")),
        ):
            indicador, motivo = resultado_operacional(base, vendas, filtros)
            self.assertIsNone(indicador)
            self.assertTrue(motivo)


class TestDashboard(unittest.TestCase):
    def test_abre_modulos_e_aplica_filtros(self):
        app = AppTest.from_file("app.py", default_timeout=120).run()
        for pagina in PAGINAS:
            with self.subTest(pagina=pagina):
                app.radio[0].set_value(pagina).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)

        app.radio[0].set_value(PAGINAS[0]).run()
        receita_total = app.metric[1].value
        filial = app.multiselect(key="filtro_filiais")
        filial.set_value([filial.options[0]]).run()
        self.assertFalse(app.exception)
        self.assertNotEqual(app.metric[1].value, receita_total)
        app.radio[0].set_value(PAGINAS[-1]).run()
        self.assertEqual(app.metric[0].value, "1.747")