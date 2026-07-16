import pytest

from dungeon.metrics import evaluate
from dungeon.solvers.cpsat_generator import CPSATDungeonGenerator


def _small_result(seed=0, n_rooms=5, symmetry=False):
    gen = CPSATDungeonGenerator()
    return gen.generate(width=24, height=18, seed=seed, n_rooms=n_rooms, symmetry=symmetry, time_limit_s=5.0)


def test_generation_succeeds():
    result = _small_result()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert len(result.grid.rooms) == 5


def test_rooms_do_not_overlap():
    result = _small_result()
    rooms = result.grid.rooms
    for i, a in enumerate(rooms):
        for b in rooms[i + 1 :]:
            overlap_x = a.x < b.x2 + 1 and b.x < a.x2 + 1
            overlap_y = a.y < b.y2 + 1 and b.y < a.y2 + 1
            assert not (overlap_x and overlap_y), f"chevauchement entre {a} et {b}"


def test_rooms_within_bounds():
    result = _small_result()
    for r in result.grid.rooms:
        assert r.x >= 1 and r.y >= 1
        assert r.x2 <= result.grid.width - 2
        assert r.y2 <= result.grid.height - 2


def test_level_is_fully_playable():
    result = _small_result()
    metrics = evaluate(result.grid)
    assert metrics.is_fully_connected
    assert metrics.path_length is not None and metrics.path_length > 0


def test_symmetry_constraint_mirrors_rooms():
    result = _small_result(n_rooms=4, symmetry=True)
    rooms = result.grid.rooms
    width = result.grid.width
    for i in range(2):
        j = 3 - i
        assert rooms[i].w == rooms[j].w
        assert rooms[i].h == rooms[j].h
        assert rooms[i].x + rooms[j].x + rooms[i].w == width


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_different_seeds_produce_different_layouts(seed):
    r1 = _small_result(seed=0)
    r2 = _small_result(seed=seed)
    coords1 = sorted((r.x, r.y) for r in r1.grid.rooms)
    coords2 = sorted((r.x, r.y) for r in r2.grid.rooms)
    assert coords1 != coords2
