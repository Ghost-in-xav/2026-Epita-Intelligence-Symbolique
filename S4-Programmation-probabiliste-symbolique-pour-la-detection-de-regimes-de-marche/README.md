# S4 — Détection de régimes de marché (probabiliste + symbolique)

> Projet **Intelligence Symbolique** (SCIA / EPITA 2026) — sujet **S4**, difficulté 3/5.
> **Membres** : Samuel Krief et Nicolas Teisseire

## L'idée en bref

Un HMM détecte les régimes de marché (*bull* / *range* / *bear*) numériquement, mais utilisé naïvement il « clignote » et autorise des transitions absurdes (*bull → bear* direct). On ajoute deux petites couches **symboliques** pour obtenir un régime plus **stable**, **cohérent** et **interprétable**, puis on alloue un portefeuille selon le régime et on backtest contre le HMM seul et le buy-and-hold.

## Les 3 couches

1. **Probabiliste** (`src/hmm.py`) — HMM gaussien (`hmmlearn`) : probabilité de régime par jour.
2. **Révision AGM** (`src/agm.py`) — on ne change de régime *cru* que sur évidence **forte et persistante** (au lieu de suivre l'argmax bruité du HMM).
3. **Qualitative** (`src/qualitative.py`) — une algèbre de transition interdit les changements incohérents (*range* est le seul pont entre *bull* et *bear*).

→ régime final (`src/strategy.py`) → allocation → backtest.

## La stratégie (volontairement simple)

Un actif risqué : **bull → 100 %**, **range → 50 %**, **bear → 0 % (cash)**.
Backtest local (pandas) avec **coûts de transaction (10 bps)**, comparé à (1) buy-and-hold et (2) HMM pur.

## Résultats (données synthétiques par défaut)

| | changements de régime | trades | Sharpe | max drawdown |
|---|---|---|---|---|
| HMM pur | 143 | 142 | 1.08 | −32 % |
| **pipeline** | **35** | **34** | **1.11** | −35 % |
| buy-and-hold | — | 0 | 0.85 | −47 % |

Le pipeline est ~4× plus stable, trade ~4× moins, reste compétitif après coûts, et garantit **0 transition illégale**. Les chiffres exacts varient sur données réelles (`yfinance`).

## Structure

```
.
├── README.md
├── requirements.txt
├── demo.py               # démo à lancer en direct : python demo.py
├── s4_regimes.ipynb      # notebook explicatif (livrable) — exécuté, avec figures
└── src/
    ├── data.py           # chargement yfinance + repli synthétique (régimes connus)
    ├── hmm.py            # couche 1 — HMM
    ├── agm.py            # couche 2 — révision AGM
    ├── qualitative.py   # couche 3 — transitions cohérentes
    └── strategy.py      # allocation + backtest (avec coûts)
```

## Lancer

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt

python demo.py                    # démo narrée + figures (demo_figures/)
jupyter notebook s4_regimes.ipynb # notebook détaillé
```

Sans réseau, tout bascule automatiquement sur des données **synthétiques à régimes connus** (utile en soutenance si le wifi lâche).

## Ressources (cours CoursIA)

- `Probas/PyMC-HMM-Trading-Alpha.ipynb` — HMM appliqué au trading (couche 1).
- `Tweety-4-Belief-Revision.ipynb` — AGM (couche 2) — _absent des zips fournis ; implémentation basée sur l'article AGM 1985_.
- `Python/QC-Py-Cloud-05-RegimeSwitching.ipynb` — allocation regime-switching (inspiration couche 4).

## Références

- Hamilton (1989), *A New Approach to the Economic Analysis of Nonstationary Time Series*.
- Alchourrón, Gärdenfors & Makinson (1985), *On the Logic of Theory Change* (AGM).
- Wellman (1990), *Fundamental Concepts of Qualitative Probabilistic Networks*.

## État

- [x] Couche 1 — HMM (proba de régime)
- [x] Couche 2 — révision AGM
- [x] Couche 3 — transitions qualitatives
- [x] Stratégie + backtest local (coûts) vs HMM pur vs buy-and-hold
- [x] Notebook explicatif + démo
- [ ] (option) backtest QuantConnect Lean
- [ ] Slides de soutenance
