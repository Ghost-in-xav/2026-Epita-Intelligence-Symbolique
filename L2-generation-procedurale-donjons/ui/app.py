"""Interface Streamlit : playground de generation + dashboard de benchmark."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dungeon.generator import generate
from dungeon.grid import Tile
from dungeon.metrics import evaluate
from dungeon.playtest import ENEMY_HP, PLAYER_MAX_HP, move_player, new_play_state

st.set_page_config(page_title="Generation procedurale de donjons", layout="wide")

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "tiles"
TILE_PX = 24

TILE_SPRITES = {
    Tile.WALL: "wall",
    Tile.FLOOR: "floor",
    Tile.START: "start",
    Tile.END: "end",
    Tile.KEY: "key",
    Tile.DOOR: "door",
    Tile.ENEMY: "enemy",
    Tile.TREASURE: "treasure",
}


@st.cache_resource
def load_sprites() -> dict:
    return {
        tile: Image.open(ASSETS_DIR / f"{name}.png").convert("RGBA").resize((TILE_PX, TILE_PX), Image.NEAREST)
        for tile, name in TILE_SPRITES.items()
    }


@st.cache_resource
def load_player_sprite() -> Image.Image:
    return Image.open(ASSETS_DIR / "player.png").convert("RGBA").resize((TILE_PX, TILE_PX), Image.NEAREST)


def render_grid(grid) -> Image.Image:
    sprites = load_sprites()
    canvas = Image.new("RGBA", (grid.width * TILE_PX, grid.height * TILE_PX))
    for y in range(grid.height):
        for x in range(grid.width):
            tile = Tile(grid.tiles[y, x])
            canvas.paste(sprites[tile], (x * TILE_PX, y * TILE_PX), sprites[tile])
    return canvas


def render_play_grid(state) -> Image.Image:
    sprites = load_sprites()
    canvas = Image.new("RGBA", (state.width * TILE_PX, state.height * TILE_PX))
    for y in range(state.height):
        for x in range(state.width):
            tile = Tile(state.tiles[y, x])
            canvas.paste(sprites[tile], (x * TILE_PX, y * TILE_PX), sprites[tile])

    draw = ImageDraw.Draw(canvas)
    for enemy in state.enemies:
        px, py = enemy.x * TILE_PX, enemy.y * TILE_PX
        canvas.paste(sprites[Tile.ENEMY], (px, py), sprites[Tile.ENEMY])
        bar_w = TILE_PX - 4
        ratio = max(enemy.hp, 0) / ENEMY_HP
        draw.rectangle([px + 2, py + 1, px + 2 + bar_w, py + 4], fill=(40, 10, 10))
        if ratio > 0:
            bar_color = (60, 200, 90) if ratio >= 1.0 else (230, 160, 40) if ratio >= 0.5 else (220, 60, 60)
            draw.rectangle([px + 2, py + 1, px + 2 + int(bar_w * ratio), py + 4], fill=bar_color)

    player_sprite = load_player_sprite()
    px, py = state.player_x * TILE_PX, state.player_y * TILE_PX
    canvas.paste(player_sprite, (px, py), player_sprite)
    bar_w = TILE_PX - 4
    ratio = max(state.player_hp, 0) / PLAYER_MAX_HP
    draw.rectangle([px + 2, py + 1, px + 2 + bar_w, py + 4], fill=(40, 10, 10))
    if ratio > 0:
        bar_color = (60, 200, 90) if ratio >= 1.0 else (230, 160, 40) if ratio >= 0.5 else (220, 60, 60)
        draw.rectangle([px + 2, py + 1, px + 2 + int(bar_w * ratio), py + 4], fill=bar_color)
    return canvas


tab_playground, tab_play, tab_dashboard = st.tabs(["Playground", "Jouer", "Dashboard"])

with tab_playground:
    st.header("Generateur de donjons")
    col_params, col_view = st.columns([1, 2])

    with col_params:
        method = st.selectbox("Methode", ["cpsat", "wfc"])
        width = st.slider("Largeur", 15, 60, 30)
        height = st.slider("Hauteur", 12, 45, 22)
        seed = st.number_input("Graine aleatoire", min_value=0, max_value=2_147_483_647, value=0, step=1)
        n_rooms = st.slider("Nombre de salles (CP-SAT)", 3, 15, 8, disabled=(method != "cpsat"))
        symmetry = st.checkbox("Symetrie (CP-SAT)", value=False, disabled=(method != "cpsat"))
        generate_clicked = st.button("Generer", type="primary")

    if generate_clicked or "last_result" not in st.session_state:
        params = {"n_rooms": n_rooms, "symmetry": symmetry} if method == "cpsat" else {}
        result = generate(method, int(width), int(height), int(seed), **params)
        st.session_state["last_result"] = result
        # Compteur monotone plutot que id(result) : un objet libere par le garbage collector
        # peut voir son id reattribue a un objet different, ce qui casserait la detection de
        # changement de niveau dans l'onglet "Jouer".
        st.session_state["generation_counter"] = st.session_state.get("generation_counter", 0) + 1

    result = st.session_state["last_result"]
    metrics = evaluate(result.grid)

    with col_view:
        st.image(render_grid(result.grid))

    st.subheader("Metriques")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Statut", result.solver_status)
    m2.metric("Temps (s)", f"{result.elapsed_s:.3f}")
    m3.metric("Connectivite", f"{metrics.connectivity_ratio:.0%}")
    m4.metric("Longueur chemin", metrics.path_length if metrics.path_length is not None else "N/A")
    st.json(metrics.to_dict())

with tab_play:
    st.header("Jouer le donjon généré")
    result = st.session_state.get("last_result")
    if result is None:
        st.info("Générez d'abord un donjon dans l'onglet Playground.")
    elif result.grid.start is None:
        st.error(
            f"La dernière génération a échoué (statut : {result.solver_status}). "
            "Retournez dans l'onglet Playground et regénérez (par ex. avec moins de "
            "salles ou une grille plus grande) avant de jouer."
        )
    else:
        level_key = st.session_state.get("generation_counter")
        if st.session_state.get("play_level_key") != level_key:
            st.session_state["play_state"] = new_play_state(result.grid)
            st.session_state["play_level_key"] = level_key

        state = st.session_state["play_state"]

        st.caption(
            "Tour par tour façon Dofus : avancez **sur** un monstre pour l'attaquer "
            "(vous ne vous déplacez pas dans sa case), puis tous les monstres encore "
            "en vie jouent leur tour — ils attaquent s'ils sont juste à côté de vous, "
            "vous poursuivent s'ils vous repèrent, ou restent passifs sinon."
        )

        col_board, col_hud = st.columns([2, 1])

        with col_hud:
            hp = max(state.player_hp, 0)
            st.markdown(f"**Vos PV** — {'❤️' * hp}{'🖤' * (PLAYER_MAX_HP - hp)}  ({hp}/{PLAYER_MAX_HP})")
            m1, m2, m3 = st.columns(3)
            m1.metric("Clé", "Oui" if state.has_key else "Non")
            m2.metric("Trésors", state.score)
            m3.metric("Tour", state.turn)

            if state.status == "WON":
                st.success("Victoire ! Vous avez atteint la sortie.")
            elif state.status == "LOST":
                st.error("Défaite : les monstres ont eu raison de vous — voir l'historique ci-dessous.")

            if state.enemies:
                st.markdown("**Monstres visibles**")
                for enemy in state.enemies:
                    dist = abs(enemy.x - state.player_x) + abs(enemy.y - state.player_y)
                    hearts = "❤️" * enemy.hp + "🖤" * (ENEMY_HP - enemy.hp)
                    warning = " ⚔️ **à portée d'attaque !**" if dist <= 1 else ""
                    st.caption(f"{hearts} — à {dist} case(s){warning}")

            st.write("**Déplacement**")
            row1 = st.columns(3)
            row2 = st.columns(3)
            row3 = st.columns(3)
            up = row1[1].button("⬆️", use_container_width=True, disabled=(state.status != "PLAYING"))
            left = row2[0].button("⬅️", use_container_width=True, disabled=(state.status != "PLAYING"))
            right = row2[2].button("➡️", use_container_width=True, disabled=(state.status != "PLAYING"))
            down = row3[1].button("⬇️", use_container_width=True, disabled=(state.status != "PLAYING"))

            direction = "N" if up else "S" if down else "O" if left else "E" if right else None
            if direction:
                hp_before = state.player_hp
                log_before = len(state.log)
                move_player(state, direction)
                new_events = state.log[log_before:]
                if new_events:
                    # Un seul toast agrege pour tout le tour : les evenements individuels
                    # (deplacement, ramassage, attaque du joueur, riposte des monstres) ne
                    # sont pas attribuables un par un a une prise de degats precise.
                    took_damage = state.player_hp < hp_before
                    st.toast(" · ".join(new_events), icon="💥" if took_damage else "ℹ️")

            if st.button("🔄 Recommencer la partie"):
                st.session_state["play_state"] = new_play_state(result.grid)
                state = st.session_state["play_state"]

            if state.log:
                st.caption("Dernier événement : " + state.log[-1])
            with st.expander(f"Historique complet ({len(state.log)} événements)"):
                for i, event in enumerate(state.log, start=1):
                    st.text(f"#{i}  {event}")

        with col_board:
            st.image(render_play_grid(state))

with tab_dashboard:
    st.header("Comparaison des paradigmes (benchmark)")
    default_csv = Path(__file__).resolve().parent.parent / "benchmarks" / "results" / "results.csv"
    uploaded = st.file_uploader("Charger un CSV de benchmark", type="csv")
    df = None
    if uploaded is not None:
        df = pd.read_csv(uploaded)
    elif default_csv.exists():
        df = pd.read_csv(default_csv)

    if df is None or df.empty:
        st.info("Aucun benchmark disponible. Lancez `dungeon-gen benchmark` pour en generer un.")
    else:
        # Rendu en markdown/matplotlib plutot que st.dataframe/st.bar_chart : ces widgets
        # serialisent le DataFrame pandas en Arrow via pyarrow, ce qui peut segfault de
        # facon native sur certaines combinaisons de versions pandas/pyarrow/Streamlit.
        summary = df.groupby(["method", "size"]).mean(numeric_only=True).round(3).reset_index()
        st.markdown(summary.to_markdown(index=False))

        metric = st.selectbox(
            "Metrique a comparer",
            ["elapsed_s", "connectivity_ratio", "path_length", "floor_density", "room_size_variety", "n_dead_ends"],
        )
        pivot = df.groupby(["size", "method"])[metric].mean().unstack("method")
        fig, ax = plt.subplots(figsize=(6, 4))
        pivot.plot(kind="bar", ax=ax)
        ax.set_xlabel("taille de grille")
        ax.set_ylabel(metric)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
