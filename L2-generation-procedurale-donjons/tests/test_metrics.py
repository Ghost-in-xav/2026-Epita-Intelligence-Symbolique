from dungeon.grid import Grid, Room, Tile
from dungeon.metrics import count_dead_ends, evaluate, reachable_from, shortest_path_length


def _corridor_grid(length: int) -> Grid:
    grid = Grid(width=length + 2, height=3)
    for x in range(1, length + 1):
        grid.set(x, 1, Tile.FLOOR)
    grid.start = (1, 1)
    grid.end = (length, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    return grid


def test_reachable_from_simple_corridor():
    grid = _corridor_grid(5)
    reached = reachable_from(grid, (1, 1))
    assert len(reached) == 5


def test_shortest_path_length_corridor():
    grid = _corridor_grid(5)
    assert shortest_path_length(grid, (1, 1), (5, 1)) == 4


def test_shortest_path_none_when_disconnected():
    grid = Grid(width=5, height=3)
    grid.set(1, 1, Tile.FLOOR)
    grid.set(3, 1, Tile.FLOOR)  # separee par un mur en x=2
    assert shortest_path_length(grid, (1, 1), (3, 1)) is None


def test_evaluate_fully_connected_corridor():
    grid = _corridor_grid(6)
    metrics = evaluate(grid)
    assert metrics.is_fully_connected
    assert metrics.connectivity_ratio == 1.0
    assert metrics.path_length == 5


def test_count_dead_ends_corridor():
    grid = _corridor_grid(4)
    # les deux extremites d'un simple couloir n'ont qu'un seul voisin marchable
    assert count_dead_ends(grid) == 2


def test_room_size_variety_identical_rooms_is_zero():
    grid = Grid(width=10, height=10)
    grid.rooms = [Room(0, 0, 3, 3), Room(5, 5, 3, 3)]
    from dungeon.metrics import room_size_variety

    assert room_size_variety(grid) == 0.0
