import pytest

from dungeon.generator import generate, generate_batch


def test_generate_dispatches_to_cpsat():
    result = generate("cpsat", width=20, height=15, seed=0, n_rooms=5)
    assert result.method == "cpsat"


def test_generate_dispatches_to_wfc():
    result = generate("wfc", width=16, height=12, seed=0)
    assert result.method == "wfc"


def test_generate_unknown_method_raises():
    with pytest.raises(ValueError):
        generate("unknown", width=10, height=10, seed=0)


def test_generate_batch_varies_seed():
    results = generate_batch("cpsat", width=20, height=15, seeds=[0, 1, 2], n_rooms=5)
    assert len(results) == 3
    assert [r.seed for r in results] == [0, 1, 2]
