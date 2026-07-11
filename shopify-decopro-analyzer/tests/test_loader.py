"""Tests minimalistes du loader (exécuter : python -m pytest, ou lancer direct)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.loader.loader import load_products, summarize, LoaderError  # noqa: E402


SAMPLE = Path(__file__).resolve().parents[1] / "data/input/produits_deco.json"


def test_load_sample():
    products = load_products(SAMPLE)
    assert len(products) == 4
    assert products[0].sku == "ARENITE-100X100-PEARL-MAT"
    assert products[0].price_ttc == 39.90


def test_summary():
    s = summarize(load_products(SAMPLE))
    assert s["total"] == 4
    assert "Pierre naturelle" in s["categories"]


def test_missing_file():
    try:
        load_products("n_existe_pas.json")
    except LoaderError:
        return
    raise AssertionError("LoaderError attendu")


if __name__ == "__main__":
    test_load_sample()
    test_summary()
    test_missing_file()
    print("✅ Tous les tests passent.")
