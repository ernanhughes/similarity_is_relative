"""Make the temporary absence of behavioural tests explicit."""

from pathlib import Path


def test_historical_suite_is_preserved_but_quarantined() -> None:
    """The architecture reset must not delete the historical evidence suite."""

    historical_suite = Path("tests")
    assert historical_suite.is_dir()
    assert any(historical_suite.glob("test_*.py"))
