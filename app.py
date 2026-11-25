"""Entrada do dashboard a partir do checkout local ou da Community Cloud."""

from pathlib import Path

from src.orizon_sales.visualizacao import executar


if __name__ == "__main__":
    executar(Path(__file__).resolve().parent)