"""Prepara os artefatos da demonstração em um checkout novo."""

from pathlib import Path
from tempfile import TemporaryDirectory

from .analise import carregar
from .geracao import gerar_base
from .qualidade import diagnosticar
from .tratamento import tratar


def carregar_demonstracao(raiz):
    """Usa a execução local ou materializa uma cópia temporária no primeiro acesso."""
    raiz = Path(raiz)
    lote = raiz / "dados" / "processamento" / "base_padrao"
    diagnostico = raiz / "dados" / "relatorios" / "base_padrao"
    if (lote / "manifesto.json").is_file() and (diagnostico / "perfil.json").is_file():
        return carregar(lote, diagnostico)

    # A instância de demonstração só mantém os dados de consulta na memória.
    with TemporaryDirectory(prefix="orizon-sales-") as pasta:
        pasta = Path(pasta)
        origem = pasta / "brutos"
        gerar_base(origem)
        diagnosticar(origem, pasta / "diagnostico")
        tratar(origem, pasta / "processamento")
        return carregar(pasta / "processamento", pasta / "diagnostico")