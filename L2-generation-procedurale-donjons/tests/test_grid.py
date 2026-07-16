from dungeon.grid import Grid, Room, Tile


def test_grid_defaults_to_walls():
    grid = Grid(width=5, height=4)
    assert grid.tiles.shape == (4, 5)
    assert grid.get(0, 0) == Tile.WALL


def test_set_get_roundtrip():
    grid = Grid(width=5, height=4)
    grid.set(2, 1, Tile.FLOOR)
    assert grid.get(2, 1) == Tile.FLOOR
    assert grid.is_walkable(2, 1)
    assert not grid.is_walkable(0, 0)


def test_out_of_bounds_not_walkable():
    grid = Grid(width=3, height=3)
    assert not grid.is_walkable(-1, 0)
    assert not grid.is_walkable(3, 0)


def test_room_cells_and_center():
    room = Room(x=2, y=3, w=3, h=2)
    cells = list(room.cells())
    assert len(cells) == 6
    assert room.center == (3, 4)
    assert room.x2 == 4 and room.y2 == 4
