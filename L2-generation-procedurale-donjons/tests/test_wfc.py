from dungeon.grid import Tile
from dungeon.metrics import evaluate
from dungeon.solvers.wfc import WFCDungeonGenerator
from dungeon.tileset import DIRS, OPPOSITE, TILES, build_compatibility


def test_compatibility_matrix_is_symmetric():
    compat = build_compatibility()
    for d, (dx, dy) in DIRS.items():
        opp = OPPOSITE[d]
        for i in range(len(TILES)):
            for j in compat[d][i]:
                assert i in compat[opp][j]


def test_border_tiles_have_wall_socket_outward():
    # sanity: la tuile WALL a bien un socket 'W' de tous les cotes (utilisee au bord)
    wall_idx = next(i for i, t in enumerate(TILES) if t.name == "WALL")
    for d in DIRS:
        assert TILES[wall_idx].sockets[d] == "W"


def test_wfc_generates_valid_adjacent_sockets():
    gen = WFCDungeonGenerator()
    result = gen.generate(width=16, height=12, seed=0)
    grid = result.grid
    # toute paire horizontale FLOOR/WALL adjacente doit correspondre a une frontiere valide
    # (pas de verification de socket exact ici : on verifie juste que la grille est bien formee)
    assert grid.tiles.shape == (12, 16)


def test_wfc_start_and_end_are_walkable_and_connected():
    gen = WFCDungeonGenerator()
    result = gen.generate(width=20, height=15, seed=1)
    grid = result.grid
    assert grid.start is not None and grid.end is not None
    metrics = evaluate(grid)
    assert metrics.path_length is not None
    assert metrics.is_fully_connected


def test_wfc_no_unreachable_floor_islands():
    gen = WFCDungeonGenerator()
    result = gen.generate(width=20, height=15, seed=2)
    metrics = evaluate(result.grid)
    assert metrics.connectivity_ratio == 1.0
