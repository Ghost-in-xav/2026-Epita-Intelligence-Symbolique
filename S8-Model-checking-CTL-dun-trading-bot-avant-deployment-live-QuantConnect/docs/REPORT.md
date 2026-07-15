# Model checking CTL d'un bot de trading avant deploiement live

Rapport - IASY S8

## 1. Probleme

Avant de deployer un bot de trading avec du capital reel, on veut une garantie
formelle qu'il ne violera jamais ses contraintes de surete. Un backtest, meme
sur 5 ans, ne teste qu'un seul chemin d'execution parmi une infinite. Le model
checking (Clarke, Emerson & Sistla 1986) verifie au contraire *toutes* les
executions accessibles d'un automate fini, ou exhibe un contre-exemple.

On modelise le bot comme une structure de Kripke, on encode ses contraintes en
CTL, on les verifie, puis on deploie la version certifiee et on confronte
l'execution reelle aux invariants prouves.

## 2. Modele formel

### 2.1 Strategie

Bot trend-following (croisement de moyennes mobiles 20/50) avec couche de
gestion du risque : circuit-breaker sur chute brutale, take-profit, reduction
de levier et mise a plat sur drawdown.

### 2.2 Structure de Kripke

Un etat = (mode, signal, drawdown, leverage, profit).

- mode in {flat, long, short, margin_warning, halted}
- signal in {buy, sell, hold, halt, tp} (entree exogene du marche)
- drawdown in {0,1,2,3} : 0 sain, 1 modere, 2 alerte (>=15%), 3 critique (>=20%)
- leverage in {0,1,2}
- profit booleen (un take-profit a deja ete realise)

La logique de controle est deterministe etant donne (etat, entrees). Le non
determinisme modelise le marche : le signal suivant est libre, et en position
leveragee le drawdown peut s'aggraver de +1 (mouvement adverse). Hors position,
le drawdown se resorbe. L'espace accessible compte 190 etats et 1450
transitions (calcule par exploration en avant).

Point cle de surete : des que le drawdown atteint la zone d'alerte (bucket 2)
en position, le bot bascule en `margin_warning` et coupe le levier a l'etape
suivante. Comme un margin call exige une position *leveragee* a drawdown
critique, et que le levier est coupe avant que le drawdown n'atteigne le bucket
3, le margin call est structurellement impossible.

## 3. Proprietes CTL

| Id | Formule | Type | Verdict |
|----|---------|------|---------|
| P1 | `AG !margin_call` | surete | vrai |
| P2 | `AG (leverage <= 2)` | surete | vrai |
| P3 | `AG ((dd_warn & flat) -> AX !in_position)` | surete | vrai |
| P4 | `AG (halted -> AF flat)` | vivacite | vrai |
| P5 | `AG (margin_warning -> AF flat)` | vivacite | vrai |
| P6 | `AG (long -> EF flat)` | atteignabilite | vrai |
| P7 | `EF profit_target` | atteignabilite | vrai |
| P8 | `AG (dd_crit -> AF flat)` | vivacite | vrai |

P3 encode "AG (drawdown > 0.15 -> AX !buy)" du sujet : sous drawdown d'alerte
et a plat, le bot n'entre pas en position a l'etape suivante.

## 4. Algorithme de verification

Model checker CTL explicite par etiquetage (algorithme de Clarke-Emerson-
Sistla). Pour une formule Phi, on calcule Sat(Phi), l'ensemble des etats qui la
satisfont, par induction :

- les operateurs existentiels EX, EU, EG sont des points fixes sur (2^S, inclus) ;
  EU est un plus petit point fixe, EG un plus grand point fixe ;
- les operateurs derives (EF, AX, AF, AG, AU) sont reecrits dans l'ensemble
  adequat {!, &, EX, EU, EG}.

Le modele satisfait Phi ssi tous les etats initiaux sont dans Sat(Phi).
Complexite O(|Phi| . (|S| + |R|)). NuSMV obtient le meme resultat de maniere
symbolique avec des BDD ; ici l'espace d'etats est petit (< 10^3) donc
l'approche explicite suffit et reste lisible.

En cas d'echec, on reconstruit un contre-exemple par parcours en largeur :
pour `AG p` faux, le plus court chemin d'un etat initial vers un etat violant p.

## 5. Modele fautif et contre-exemples

Pour montrer que la verification a un pouvoir discriminant, on construit une
variante sans gestion du risque (pas de bascule en margin_warning, levier non
reduit). Le model checker prouve alors que P1, P3 et P8 sont fausses et fournit
des traces. Contre-exemple pour P1 (margin call) :

```
flat  sig=hold dd=0 lev=0
flat  sig=buy  dd=0 lev=0
long  sig=buy  dd=0 lev=2
long  sig=buy  dd=1 lev=2
long  sig=hold dd=2 lev=2
long  sig=hold dd=3 lev=2   <- margin call (position leveragee, drawdown critique)
```

Le bot reste leverage pendant que le drawdown grimpe jusqu'au seuil critique :
c'est precisement ce que la gestion du risque du modele certifie empeche.

## 6. Extension probabiliste (PCTL / MDP)

On encode le bot comme un MDP ou le mouvement adverse de marche survient avec
probabilite p (par defaut 0.3), et on evalue des proprietes PCTL par iteration
de valeur (Baier & Katoen 2008 ch. 10 ; PRISM, Storm).

- Modele certifie : `Pmin [G !margin_call] = 1` - certitude totale, coherente
  avec le resultat CTL.
- Modele fautif : `Pmax [F margin_call] > 0` - le risque devient quantifiable
  (par ex. ~0.99 avec p=0.1), ce qui illustre la difference entre la certitude
  totale du model checking deterministe (NuSMV) et la certitude probabilisee de
  Storm/PRISM.

`P[G !margin_call] = 1 - Pmax[F margin_call]` : pour la surete on prend le pire
ordonnanceur (maximisation de l'atteinte du danger).

## 7. Deploiement QuantConnect

`quantconnect/main.py` implemente l'automate certifie en LEAN (QCAlgorithm) :
mêmes seuils, même logique de controle, levier borne a 2x cote courtier. Un
moniteur d'invariants embarque verifie a chaque barre les invariants prouves
(P1, P2) et liquide en urgence en cas de violation.

Pipeline (notebooks CoursIA) : QC-Py-15 (optimisation des parametres) -> QC-Py-27
(production) -> QC-Py-40/41 (paper trading 2-4 semaines) avant capital reel.

## 8. Gap modele / realite

Le backtest (`run_backtest.py`) rejoue la strategie sur 5 ans de prix et
soumet chaque etat au moniteur. Resultats : 0 violation d'invariant de surete,
levier toujours <= 2x, drawdown plafonne au bucket 2.

En revanche le moniteur detecte des *gaps* modele/realite : sur certains seeds,
un mouvement de marche fait sauter le drawdown de plus d'un bucket en une seule
barre (par ex. 0 -> 2). Le modele suppose une aggravation de +1 bucket par pas ;
la realite peut gapper davantage. C'est l'ecart central a documenter :

- la propriete *critique* (P1, pas de margin call) tient malgre les gaps, car
  le bot reagit a la barre suivante et le drawdown plafonne au bucket 2 ;
- mais l'hypothese de granularite du modele est mise en defaut. Pour reduire le
  gap on peut : (a) raffiner les buckets de drawdown, (b) ajouter des
  transitions de saut (gap) au modele, (c) modeliser explicitement slippage et
  latence d'ordre, (d) passer au model checking probabiliste avec une
  distribution de sauts calibree sur les donnees.

Autres sources de gap a considerer en live : slippage et fills partiels, halts
declenches par le circuit-breaker de l'echange, latence entre signal et
execution. Le moniteur runtime sert de garde-fou : si un invariant prouve est
viole en live, c'est le signal que la realite est sortie du domaine du modele.

## 9. Conclusion

Le model checking CTL prouve exhaustivement les contraintes de surete du bot
sur son modele fini, la ou un backtest n'echantillonne qu'un chemin. Le modele
fautif montre que la methode detecte de vraies violations avec des
contre-exemples exploitables. L'extension PCTL quantifie le risque residuel
sous incertitude. Enfin, le moniteur d'invariants relie la preuve a
l'execution et mesure le gap modele/realite, qui reste circonscrit aux
hypotheses de granularite sans compromettre la surete critique.
