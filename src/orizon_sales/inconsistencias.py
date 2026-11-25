"""Injeta defeitos identificáveis sem reutilizar a semente da simulação."""


# Cada taxa incide sobre a quantidade original de registros da tabela.
REGRAS = (
    ("duplicata_exata", "itens_venda", "item_id", 0.006, None),
    ("duplicata_conflitante", "itens_venda", "quantidade", 0.002, None),
    ("valor_ausente", "itens_venda", "custo_unitario_centavos", 0.003, ""),
    ("formato_incorreto", "itens_venda", "quantidade", 0.002, "2 caixas"),
    ("referencia_inexistente", "itens_venda", "produto_id", 0.002, "PRO-99999"),
    ("data_invalida", "pedidos", "data_venda", 0.003, "2025-02-30"),
    ("data_fora_da_janela", "pedidos", "data_venda", 0.001, "2026-01-15"),
    ("divergencia_cadastral", "clientes", "segmento", 0.010, None),
    ("espaco_no_codigo", "produtos", "fornecedor_id", 0.008, None),
    ("valor_ausente", "despesas", "valor_centavos", 0.004, ""),
)
VARIANTES_SEGMENTO = {
    "Varejo": "VAREJO", "Atacado": "atac.", "Alimentação": "Alimentacao", "Serviços": "Servicos",
}


def injetar(tabelas, rng):
    """Registra a posição lógica e os valores antes e depois de cada alteração."""
    candidatos = {nome: list(map(int, rng.permutation(len(linhas))))
                  for nome, linhas in tabelas.items()}
    totais = {nome: len(linhas) for nome, linhas in tabelas.items()}
    eventos, configuracao = [], []

    for regra, tabela, campo, taxa, substituto in REGRAS:
        linhas = tabelas[tabela]
        indices = candidatos[tabela]
        quantidade = max(1, round(totais[tabela] * taxa))
        configuracao.append(dict(regra=regra, tabela=tabela, campo=campo, taxa=taxa,
                                  planejados=quantidade))
        for _ in range(quantidade):
            indice = indices.pop()
            original = linhas[indice]
            anterior = original[campo]

            if regra in ("duplicata_exata", "duplicata_conflitante"):
                copia = original.copy()
                if regra == "duplicata_conflitante":
                    copia[campo] = anterior + 1
                linhas.append(copia)
                ordinal = len(linhas)
                posterior = copia[campo]
            else:
                posterior = substituto
                if regra == "divergencia_cadastral":
                    posterior = VARIANTES_SEGMENTO[anterior]
                elif regra == "espaco_no_codigo":
                    posterior = f" {anterior} "
                original[campo] = posterior
                ordinal = indice + 1

            eventos.append(dict(tabela=tabela, ordinal_bruto=ordinal,
                                ordinal_original=indice + 1, chave_original=next(iter(original.values())),
                                regra=regra, campo=campo, valor_anterior=anterior,
                                valor_injetado=posterior))
    return eventos, configuracao