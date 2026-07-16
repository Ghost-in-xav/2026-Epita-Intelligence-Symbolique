"""Simulation jouable, tour par tour, du donjon genere.

Inspire du systeme de tours de Dofus : a chaque tour, le joueur agit une fois
(deplacement, ou attaque au corps-a-corps s'il vise une case occupee par un
monstre), puis chaque monstre agit a son tour : il attaque s'il est adjacent
au joueur, se rapproche par plus-court-chemin (BFS) s'il est a portee d'aggro,
ou reste passif sinon. C'est un moyen concret d'evaluer qualitativement la
jouabilite d'un niveau genere (accessibilite, difficulte percue).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .grid import Grid, Tile

DIRECTIONS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0)}

PLAYER_MAX_HP = 5
PLAYER_ATTACK = 2  # tue un monstre (ENEMY_HP) en un seul coup : pas de riposte si le coup est fatal
ENEMY_HP = 2
ENEMY_ATTACK = 1
ENEMY_AGGRO_RANGE = 4
TREASURE_HEAL = 1  # les tresors soignent en plus d'incrementer le score : ressource de survie


@dataclass
class Enemy:
    x: int
    y: int
    hp: int = ENEMY_HP


@dataclass
class PlayState:
    width: int
    height: int
    tiles: object  # copie mutable de grid.tiles (numpy array), evolue avec les ramassages/ouvertures
    player_x: int
    player_y: int
    player_hp: int = PLAYER_MAX_HP
    has_key: bool = False
    score: int = 0
    turn: int = 0
    status: str = "PLAYING"  # PLAYING | WON | LOST
    enemies: list[Enemy] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def tile_at(self, x: int, y: int) -> Tile:
        return Tile(self.tiles[y, x])

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        self.tiles[y, x] = int(tile)

    def enemy_at(self, x: int, y: int) -> Enemy | None:
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                return enemy
        return None


def new_play_state(grid: Grid) -> PlayState:
    """Initialise une partie a partir d'un donjon genere : les monstres deviennent des
    entites mobiles independantes de la grille statique (leur case redevient du sol)."""
    tiles = grid.tiles.copy()
    enemies = []
    for y in range(grid.height):
        for x in range(grid.width):
            if Tile(tiles[y, x]) == Tile.ENEMY:
                enemies.append(Enemy(x, y))
                tiles[y, x] = int(Tile.FLOOR)
    px, py = grid.start
    return PlayState(width=grid.width, height=grid.height, tiles=tiles, player_x=px, player_y=py, enemies=enemies)


def _in_bounds(state: PlayState, x: int, y: int) -> bool:
    return 0 <= x < state.width and 0 <= y < state.height


def _is_blocked(state: PlayState, x: int, y: int) -> bool:
    if not _in_bounds(state, x, y):
        return True
    tile = state.tile_at(x, y)
    if tile == Tile.WALL:
        return True
    if tile == Tile.DOOR and not state.has_key:
        return True
    return False


def move_player(state: PlayState, direction: str) -> PlayState:
    """Fait agir le joueur (deplacement ou attaque), puis joue le tour des monstres."""
    if state.status != "PLAYING":
        return state

    dx, dy = DIRECTIONS[direction]
    nx, ny = state.player_x + dx, state.player_y + dy

    target = state.enemy_at(nx, ny)
    if target is not None:
        target.hp -= PLAYER_ATTACK
        if target.hp <= 0:
            state.enemies.remove(target)
            state.log.append("Monstre vaincu !")
        else:
            state.log.append("Vous frappez le monstre.")
    elif _is_blocked(state, nx, ny):
        state.log.append("Chemin bloque.")
    else:
        state.player_x, state.player_y = nx, ny
        tile = state.tile_at(nx, ny)
        if tile == Tile.KEY:
            state.has_key = True
            state.set_tile(nx, ny, Tile.FLOOR)
            state.log.append("Clé récupérée.")
        elif tile == Tile.TREASURE:
            state.score += 1
            healed = min(TREASURE_HEAL, PLAYER_MAX_HP - state.player_hp)
            state.player_hp += healed
            state.set_tile(nx, ny, Tile.FLOOR)
            if healed > 0:
                state.log.append(f"Trésor collecté (+{healed} PV).")
            else:
                state.log.append("Trésor collecté.")
        elif tile == Tile.DOOR:
            state.set_tile(nx, ny, Tile.FLOOR)
            state.log.append("Porte ouverte.")
        elif tile == Tile.END:
            state.status = "WON"
            state.log.append("Sortie atteinte, victoire !")
            return state

    _enemies_turn(state)
    state.turn += 1
    return state


def _bfs_next_step(state: PlayState, start: tuple[int, int], goal: tuple[int, int]) -> tuple[int, int] | None:
    """Premier pas du plus court chemin de `start` vers `goal` (les autres monstres bloquent)."""
    visited = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        cx, cy = cur
        for dx, dy in DIRECTIONS.values():
            nxt = (cx + dx, cy + dy)
            if nxt in visited or not _in_bounds(state, *nxt):
                continue
            tile = state.tile_at(*nxt)
            if tile == Tile.WALL:
                continue
            if tile == Tile.DOOR and not state.has_key:
                continue
            if nxt != goal and state.enemy_at(*nxt) is not None:
                continue
            visited[nxt] = cur
            queue.append(nxt)
    if goal not in visited:
        return None
    step = goal
    while visited[step] != start:
        step = visited[step]
        if step is None:
            return None
    return step


def _enemies_turn(state: PlayState) -> None:
    if state.status != "PLAYING":
        return
    player_pos = (state.player_x, state.player_y)
    for enemy in list(state.enemies):
        dist = abs(enemy.x - player_pos[0]) + abs(enemy.y - player_pos[1])
        if dist == 1:
            state.player_hp -= ENEMY_ATTACK
            state.log.append("Un monstre vous attaque !")
            if state.player_hp <= 0:
                state.status = "LOST"
                state.log.append("Vous avez succombé...")
                return
        elif dist <= ENEMY_AGGRO_RANGE:
            step = _bfs_next_step(state, (enemy.x, enemy.y), player_pos)
            if step is not None and state.enemy_at(*step) is None:
                enemy.x, enemy.y = step
