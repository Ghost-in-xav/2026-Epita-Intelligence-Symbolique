from dungeon.grid import Grid, Tile
from dungeon.playtest import PLAYER_MAX_HP, Enemy, move_player, new_play_state


def _corridor_state(length: int, enemy_offset: int | None = None) -> object:
    grid = Grid(width=length + 2, height=3)
    for x in range(1, length + 1):
        grid.set(x, 1, Tile.FLOOR)
    grid.start = (1, 1)
    grid.end = (length, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    if enemy_offset is not None:
        grid.set(1 + enemy_offset, 1, Tile.ENEMY)
    return new_play_state(grid)


def test_new_play_state_extracts_enemies_from_static_grid():
    state = _corridor_state(5, enemy_offset=2)
    assert len(state.enemies) == 1
    assert state.enemies[0].x == 3
    assert state.tile_at(3, 1) == Tile.FLOOR  # la case redevient du sol


def test_move_player_walks_into_open_corridor():
    state = _corridor_state(5)
    move_player(state, "E")
    assert (state.player_x, state.player_y) == (2, 1)
    assert state.status == "PLAYING"


def test_move_player_blocked_by_wall():
    state = _corridor_state(5)
    move_player(state, "N")  # mur au-dessus du couloir
    assert (state.player_x, state.player_y) == (1, 1)
    assert "bloque" in state.log[-1].lower()


def test_reaching_end_wins():
    state = _corridor_state(3)
    move_player(state, "E")
    move_player(state, "E")
    assert state.status == "WON"


def _branch_key_door_grid() -> Grid:
    """Couloir principal y=1 (x=1..4, porte en x=4, sortie en x=5) avec une cle
    accessible uniquement par une branche laterale en (2, 0)."""
    grid = Grid(width=6, height=3)
    for x in range(1, 5):
        grid.set(x, 1, Tile.FLOOR)
    grid.set(2, 0, Tile.KEY)
    grid.set(4, 1, Tile.DOOR)
    grid.set(5, 1, Tile.FLOOR)
    grid.start = (1, 1)
    grid.end = (5, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    return grid


def test_key_unlocks_door():
    state = new_play_state(_branch_key_door_grid())
    move_player(state, "E")  # -> (2, 1)
    move_player(state, "N")  # -> (2, 0) : ramasse la cle
    assert state.has_key
    move_player(state, "S")  # revient sur le couloir principal
    move_player(state, "E")  # -> (3, 1)
    move_player(state, "E")  # -> (4, 1) : la porte s'ouvre
    assert state.tile_at(4, 1) == Tile.FLOOR
    move_player(state, "E")  # -> (5, 1) : sortie
    assert state.status == "WON"


def test_door_blocks_without_key():
    state = new_play_state(_branch_key_door_grid())
    move_player(state, "E")  # -> (2, 1), sans detour par la cle
    move_player(state, "E")  # -> (3, 1)
    move_player(state, "E")  # tentative vers la porte (4, 1) : bloque
    assert state.player_x == 3
    assert state.tile_at(4, 1) == Tile.DOOR


def test_treasure_increments_score():
    grid = Grid(width=5, height=3)
    for x in range(1, 4):
        grid.set(x, 1, Tile.FLOOR)
    grid.set(2, 1, Tile.TREASURE)
    grid.start = (1, 1)
    grid.end = (3, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    state = new_play_state(grid)
    move_player(state, "E")
    assert state.score == 1


def test_treasure_heals_player_up_to_max():
    grid = Grid(width=5, height=3)
    for x in range(1, 4):
        grid.set(x, 1, Tile.FLOOR)
    grid.set(2, 1, Tile.TREASURE)
    grid.start = (1, 1)
    grid.end = (3, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    state = new_play_state(grid)
    state.player_hp = PLAYER_MAX_HP - 1
    move_player(state, "E")
    assert state.player_hp == PLAYER_MAX_HP  # soigne mais jamais au-dela du maximum


def test_attacking_adjacent_enemy_does_not_move_player():
    state = _corridor_state(5, enemy_offset=1)
    move_player(state, "E")
    assert (state.player_x, state.player_y) == (1, 1)  # attaque, ne se deplace pas
    assert len(state.enemies) == 0  # PLAYER_ATTACK == ENEMY_HP : mort en un coup, pas de riposte


def test_killing_enemy_removes_it():
    state = _corridor_state(5, enemy_offset=1)
    move_player(state, "E")
    assert len(state.enemies) == 0


def test_one_shot_kill_costs_no_hp_when_already_adjacent():
    """Un combat doit etre gagnable : tuer un monstre deja adjacent en un coup ne
    doit infliger aucun degat (il est retire avant de pouvoir riposter ce tour-la)."""
    state = _corridor_state(5, enemy_offset=1)
    hp_before = state.player_hp
    move_player(state, "E")
    assert len(state.enemies) == 0
    assert state.player_hp == hp_before


def test_adjacent_enemy_attacks_player_each_turn():
    grid = Grid(width=6, height=3)
    for x in range(1, 5):
        grid.set(x, 1, Tile.FLOOR)
    grid.start = (1, 1)
    grid.end = (4, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    state = new_play_state(grid)
    state.enemies.append(Enemy(x=2, y=1, hp=99))  # ne meurt pas, reste adjacent en boucle
    starting_hp = state.player_hp
    move_player(state, "N")  # coup dans le vide (mur) : le monstre agit quand meme
    assert state.player_hp == starting_hp - 1


def test_player_dies_when_hp_reaches_zero():
    grid = Grid(width=6, height=3)
    for x in range(1, 5):
        grid.set(x, 1, Tile.FLOOR)
    grid.start = (1, 1)
    grid.end = (4, 1)
    grid.set(*grid.start, Tile.START)
    grid.set(*grid.end, Tile.END)
    state = new_play_state(grid)
    state.enemies.append(Enemy(x=2, y=1, hp=99))
    for _ in range(state.player_hp):
        if state.status != "PLAYING":
            break
        move_player(state, "N")
    assert state.status == "LOST"
