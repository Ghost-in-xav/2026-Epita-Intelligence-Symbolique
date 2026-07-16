# S8 - Model checking CTL d'un bot de trading avant deploiement live

Projet IASY S8. On modelise un bot de trading trend-following comme un
automate fini (structure de Kripke), on prouve ses contraintes de surete par
model checking CTL (puis PCTL probabiliste en extension), et on deploie la
version certifiee sur QuantConnect en comparant l'execution reelle aux
invariants prouves.

## Idee

Avant de risquer du capital reel, on veut une garantie formelle que le bot ne
violera jamais ses contraintes de surete :

- jamais de margin call,
- effet de levier toujours <= 2x,
- retour systematique en position flat apres un signal halt,
- pas d'ouverture de position en zone de drawdown critique,
- desengagement (deleveraging) garanti des l'alerte de marge.

On encode ces proprietes en CTL et un model checker verifie *exhaustivement*
toutes les executions accessibles, ou fournit un contre-exemple concret.

## Contenu

```
botcheck/            moteur de model checking + modele du bot
  kripke.py          structure de Kripke
  ctl.py             syntaxe CTL
  model_checker.py   model checker CTL par etiquetage + contre-exemples
  pctl.py            MDP + model checking PCTL (value iteration) [extension]
  strategy.py        automate fini de la strategie (source unique)
  model_builder.py   construit Kripke / MDP depuis la strategie
  properties.py      catalogue des proprietes CTL et PCTL
  backtest.py        simulateur de backtest
  monitor.py         moniteur d'invariants a l'execution + detection de gap
models/
  nusmv/             modeles .smv (NuSMV) : certifie + version fautive
  prism/             modele .prism + proprietes .pctl (PRISM / Storm)
quantconnect/main.py algorithme LEAN du bot certifie
verify.py            verifie toutes les proprietes CTL (correct + buggy)
verify_pctl.py       verification probabiliste PCTL (extension)
run_backtest.py      backtest + verification runtime des invariants
tests/               tests pytest
docs/REPORT.md       rapport
```

## Utilisation

```bash
python verify.py          # model checking CTL : modele certifie + modele fautif
python verify_pctl.py     # extension PCTL probabiliste (MDP)
python run_backtest.py    # backtest + monitoring runtime des invariants
python -m pytest tests/   # tests
```

Le model checker CTL et PCTL est implemente en Python pur : tout tourne sans
installer NuSMV/PRISM. Les fichiers `models/nusmv/*.smv` et
`models/prism/*.prism` sont les memes modeles au format des outils standards,
prets a lancer si on les installe :

```bash
NuSMV models/nusmv/trading_bot.smv
NuSMV models/nusmv/trading_bot_buggy.smv      # produit les contre-exemples
prism models/prism/trading_bot.prism models/prism/props.pctl
```

## Le modele

Automate fini du bot :

- modes : `flat`, `long`, `short`, `margin_warning`, `halted`
- variables : `signal` (entree marche), `drawdown` (buckets 0..3),
  `leverage` (0..2), `profit` (booleen)
- le controle est deterministe ; le non determinisme vient du marche
  (signal libre, aggravation possible du drawdown en position).

La meme logique sert au model checking, au backtest, au moniteur runtime et a
l'algorithme QuantConnect, ce qui garantit que ce qui est prouve correspond a
ce qui s'execute.

## Resultats

- Modele certifie : les 8 proprietes CTL sont verifiees.
- Modele fautif (gestion du risque retiree) : P1 (margin call), P3 (achat en
  drawdown) et P8 sont fausses, avec contre-exemples.
- PCTL : sur le modele certifie `P[G !margin_call] = 1` (certitude totale,
  comme en CTL) ; sur le modele fautif la probabilite de margin call devient
  strictement positive.
- Backtest : 0 violation d'invariant. Les gaps de marche (sauts de drawdown de
  plus d'un bucket en une barre) sont detectes separement : ils sortent d'une
  hypothese du modele sans casser la propriete critique de surete.

Voir `docs/REPORT.md` pour le detail.

## References

- Clarke, Emerson & Sistla (1986). Automatic verification of finite-state
  concurrent systems using temporal logic specifications. ACM TOPLAS 8(2).
- Baier & Katoen (2008). Principles of Model Checking. MIT Press.
- Cimatti et al. (2002). NuSMV 2. CAV 2002.
- Kwiatkowska, Norman & Parker (2011). PRISM 4.0. CAV 2011.
- Hensel et al. (2022). The Probabilistic Model Checker Storm. STTT 24(4).
