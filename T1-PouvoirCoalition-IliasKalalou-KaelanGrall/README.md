Projet T1 — Pouvoir de coalition par verification formelle
==========================================================

Groupe : Ilias Kalalou et Kaelan Grall
EPITA SCIA — Intelligence Symbolique 2026

Sujet : mesurer le pouvoir reel des acteurs d'un vote (Shapley-Shubik, Banzhaf,
Deegan-Packel), le verifier formellement par le solveur SMT Z3, et l'appliquer a
des donnees electorales reelles.

Idee directrice
---------------

Le pouvoir d'un acteur dans un vote ne se confond pas avec son poids en sieges.
Un petit parti charniere peut peser autant que deux grands blocs ; un grand parti
isole ideologiquement peut etre quasi impuissant. Les indices de pouvoir mesurent
cette capacite a faire basculer une coalition. Le projet calcule ces indices,
les ancre dans le raisonnement symbolique (encodage SMT, preuve des axiomes par
Z3) et confronte la theorie aux resultats electoraux francais.

Couverture du sujet
-------------------

| Objectif de l'enonce                                                     | Etat                                                    |
|--------------------------------------------------------------------------|---------------------------------------------------------|
| 1. Indices Shapley-Shubik, Banzhaf, Deegan-Packel par encodage SAT/SMT, verifies sur instances de reference | Couvert : double calcul, enumeration exacte et voie SMT (Z3), concordance testee |
| 2. Preuve formelle des axiomes et proprietes qui distinguent les indices | Couvert : preuve Z3 des axiomes des trois indices (Shapley-Shubik, Banzhaf et Deegan-Packel), distinction formelle efficacite/additivite |
| 3. Application aux legislatives 2022 et 2024, coalitions et indices       | Couvert : indices sur les groupes et sur les blocs agreges (NUPES/NFP, Ensemble, RN, LR), contrefactuel d'union de la gauche, chaine d'agregation par circonscription et nuance |
| 4. Comparaison pouvoir theorique / coalitions reelles et divergences      | Couvert : confrontation a un vote reel (censure du 4 decembre 2024), detail par groupe, decomposition de l'ecart de discipline et criticite observee |
| 5. Extension aux scrutins proportionnels (D'Hondt) et impact du mode de scrutin | Couvert : D'Hondt sur les europeennes 2024, prime majoritaire sur les regionales 2021, contrefactuels a suffrages constants et analyse des seuils strategiques |

Precisions d'honnetete academique. La preuve des axiomes est bornee : etablie
par Z3 pour chaque nombre de joueurs n teste (preuve assistee par ordinateur au
sens de Tang et Lin, 2009), et non pour tout n par induction, ce qui releverait
d'un assistant comme Lean. Les axiomes des trois indices sont prouves par Z3.
Pour Shapley-Shubik et Banzhaf, les valeurs des coalitions deviennent des reels
Z3 et l'indice s'ecrit en combinaison lineaire. Deegan-Packel, non lineaire car
defini via les coalitions gagnantes minimales, est prouve en encodant le predicat
de coalition minimale : la symetrie, le joueur nul et l'efficacite sont etablis
par negation UNSAT, sans division, et doubles d'une verification empirique.
L'additivite ne concerne que Shapley-Shubik : la somme de deux jeux simples n'est
pas un jeu simple, aussi n'est-elle pas definie pour les indices de pouvoir a
priori. Chaque indice est enfin calcule par deux voies independantes :
l'enumeration Python (indices/) et la voie SMT (formal/smt_indices.py), ou Z3
enumere les swings stratifies par taille de coalition et les coalitions gagnantes
minimales ; seule l'arithmetique de ponderation reste en Python, et la
concordance des deux voies est testee.

Sur l'objectif 4, la comparaison entre pouvoir a priori et vote reel reste bornee
par nature : un scrutin unique ne fournit pas de frequence empirique de pivot. Le
detail par groupe des 331 voix est en revanche exact et permet de decomposer
l'ecart de discipline entre defections internes et ralliements externes. Sur
l'objectif 3, la chaine data/circonscriptions.py va du resultat par circonscription
au poids d'un acteur, mais la repartition finale en groupes provient de l'Assemblee
nationale : la nuance de campagne ne determine pas le groupe, constitue apres
l'election, ce qui justifie la modelisation au niveau des groupes.

Structure
---------

    T1-PouvoirCoalition-IliasKalalou-KaelanGrall/
    ├── app.py                     Application Streamlit (6 modes)
    ├── analysis.py                Tableaux comparatifs, validation croisee, benchmark
    ├── presentation.pptx          Slides de soutenance (et export presentation.pdf)
    ├── core/
    │   └── games.py               Jeu de vote pondere, coalitions, statut des joueurs
    ├── indices/
    │   ├── shapley_shubik.py      Indice de Shapley-Shubik (exact + Monte Carlo)
    │   ├── banzhaf.py             Indice de Banzhaf (absolu et normalise)
    │   └── deegan_packel.py       Indice de Deegan-Packel (coalitions minimales)
    ├── formal/
    │   ├── smt_encoding.py        Encodage SMT (Z3) : statut, swings, MWC
    │   ├── smt_indices.py         Les trois indices calcules par la voie SMT
    │   ├── axioms.py              Preuve Z3 des axiomes (Shapley-Shubik, Banzhaf, Deegan-Packel)
    │   └── distinctions.py        Proprietes qui distinguent les indices
    ├── data/
    │   ├── legislatives_2024.py   Groupes de l'Assemblee, XVIIe legislature
    │   ├── legislatives_2022.py   Groupes de l'Assemblee, XVIe legislature
    │   ├── coalitions.py          Agregation en blocs (NUPES/NFP, Ensemble) et contrefactuel d'union
    │   ├── circonscriptions.py    Agregation par circonscription et nuance vers les groupes
    │   ├── votes_reels.py         Vote reel : censure du 4 decembre 2024, detail par groupe
    │   ├── modes_scrutin.py       Contrefactuel de mode de scrutin a suffrages constants
    │   ├── europeennes_dhondt.py  Methode D'Hondt, europeennes 2024, seuils strategiques
    │   └── regionales.py          Prime majoritaire, regionales 2021 (Ile-de-France)
    ├── viz/
    │   ├── power_vs_weight.py     Sieges contre pouvoir, ecarts de pouvoir
    │   ├── coalitions.py          Coalitions gagnantes minimales, criticite
    │   └── dhondt.py              Quotients D'Hondt, repartition des sieges
    ├── tests/
    │   ├── test_indices.py        Indices sur instances de reference (ONU, paradoxes)
    │   ├── test_smt.py            Concordance encodage SMT / enumeration
    │   ├── test_axioms.py         Preuves Z3 des axiomes des trois indices
    │   ├── test_coalitions.py     Blocs politiques et contrefactuel d'union
    │   ├── test_circonscriptions.py  Chaine d'agregation candidat / nuance / groupe
    │   ├── test_votes_reels.py    Confrontation au vote reel (censure 2024), discipline
    │   ├── test_modes_scrutin.py  Contrefactuel D'Hondt / Sainte-Lague / majoritaire
    │   ├── test_regionales.py     Prime majoritaire et impact du mode de scrutin
    │   ├── test_edge_cases.py     Cas limites et validation des entrees
    │   └── test_data.py           Integrite des donnees, methode D'Hondt
    └── requirements.txt

Installation
------------

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Lancement
---------

Application interactive :

    streamlit run app.py

Tests unitaires :

    pytest

Les trois indices de pouvoir
----------------------------

| Indice          | Principe                                              | Somme |
|-----------------|-------------------------------------------------------|-------|
| Shapley-Shubik  | Fraction des ordres ou le joueur est pivot            | 1     |
| Banzhaf norm.   | Part des coalitions ou le joueur est critique (swing) | 1     |
| Banzhaf absolu  | Probabilite que le vote du joueur soit decisif        | -     |
| Deegan-Packel   | Partage egal au sein des coalitions gagnantes minimales | 1   |

Le volet symbolique
-------------------

Le solveur SMT Z3 intervient a deux niveaux.

1. Encodage des jeux (formal/smt_encoding.py et formal/smt_indices.py) :
   chaque joueur devient une variable booleenne, la victoire une contrainte de
   poids. Le statut des joueurs (veto, nul, dictateur), les swings stratifies
   par taille de coalition et les coalitions gagnantes minimales sont obtenus
   par satisfiabilite, puis les trois indices sont recalcules integralement
   depuis ces sorties. La concordance avec l'enumeration combinatoire est
   systematiquement testee (tests/test_smt.py) et garantit la correction.

2. Preuve des axiomes (formal/axioms.py, formal/distinctions.py) : pour n
   joueurs, les 2^n valeurs des coalitions deviennent des variables reelles Z3.
   Pour Shapley-Shubik et Banzhaf, l'indice s'ecrit comme combinaison lineaire de
   ces valeurs. Pour Deegan-Packel, non lineaire, on encode le predicat de
   coalition gagnante minimale (S gagne et tout retrait la fait perdre), puis on
   prouve la symetrie, le joueur nul et l'efficacite sans division, en raisonnant
   sur les numerateurs et le nombre de coalitions minimales. Chaque axiome est
   demontre en etablissant que sa negation est insatisfaisable (UNSAT). La
   distinction entre indices est etablie formellement : Shapley-Shubik est le seul
   a concilier efficacite et additivite ; Z3 exhibe un jeu ou la somme des indices
   de Banzhaf differe de la valeur de la grande coalition (violation de
   l'efficacite), et un contre-exemple montre que le Banzhaf normalise n'est pas
   additif.

Resultats marquants
-------------------

- Paradoxe du petit parti [51 ; 49, 48, 3] : les trois partis ont un pouvoir egal
  (1/3 chacun) malgre des poids tres inegaux, car toute paire gagne.
- Conseil de securite de l'ONU : chaque membre permanent detient 19,6 % du
  pouvoir, chaque non permanent 0,19 %, conformement a Shapley et Shubik (1954).
- Assemblee 2024 : aucun groupe n'a la majorite absolue (289/577) ; l'indice de
  Deegan-Packel egalise fortement les groupes, et le pouvoir de pivot des deux
  premiers groupes (RN et EPR) depasse legerement leur part de sieges sous
  Shapley-Shubik et Banzhaf.
- Europeennes 2024 : la methode D'Hondt implementee reproduit exactement la
  repartition officielle des 81 sieges francais.
- Blocs 2024 : agreges en blocs (NFP, Ensemble, RN, DR, LIOT, UDR), trois blocs
  seulement (NFP, Ensemble, RN) se partagent le pouvoir a parts egales et les
  autres deviennent nuls. Le contrefactuel d'union montre qu'en 2022 unir la
  gauche aurait reduit son pouvoir de pivot (-7,4 points), alors qu'en 2024 il
  l'augmente legerement.
- Motion de censure du 4 decembre 2024 : la coalition NFP + RN + UDR totalise 335
  sieges mais 331 voix ; l'ecart de 4 mesure l'imperfection de la discipline de
  parti. La coalition est gagnante mais non minimale ; seuls RN, LFI et SOC y
  etaient critiques. Cette alliance ideologiquement improbable illustre la limite
  des indices a priori.
- Mode de scrutin a suffrages constants (europeennes 2024) : sous D'Hondt et
  Sainte-Lague le pouvoir de pivot du RN reste quasi identique, mais le scrutin
  majoritaire integral le transforme en dictateur (100 % du pouvoir).
- Regionales 2021 en Ile-de-France : la prime majoritaire donne 125 sieges sur
  209 a la liste arrivee en tete avec 45,9 % des voix, ce qui en fait un dictateur
  au sens des indices (100 % du pouvoir). La meme repartition en proportionnelle
  pure ne lui donnerait que 96 sieges et la moitie du pouvoir de pivot.
- Seuils strategiques de D'Hondt (europeennes 2024) : le dernier siege s'obtient
  au quotient frontiere d'environ 258 000 voix ; la liste Renaissance n'etait qu'a
  environ 11 700 voix d'un siege supplementaire, ce qui chiffre la pression aux
  fusions de listes.

Pistes d'extension
------------------

- Exploiter les votes nominatifs individuels (positions par depute) sur un grand
  nombre de scrutins, pour construire une frequence empirique de pivot et non un
  cas unique.
- Ingerer directement les fichiers par circonscription de data.gouv.fr via
  data/circonscriptions.py, la chaine d'agregation etant deja en place.
- Formaliser l'unicite de l'indice de Shapley-Shubik en Lean 4 pour une preuve
  non bornee des axiomes (valable pour tout n, et non pour chaque n teste).

References
----------

- Shapley L., Shubik M. (1954), A Method for Evaluating the Distribution of Power
  in a Committee System, American Political Science Review 48(3).
- Banzhaf J. (1965), Weighted Voting Doesn't Work : A Mathematical Analysis,
  Rutgers Law Review 19.
- Deegan J., Packel E. (1978), A New Index of Power for Simple n-Person Games,
  International Journal of Game Theory 7(2).
- Dubey P., Shapley L. (1979), Mathematical Properties of the Banzhaf Power
  Index, Mathematics of Operations Research 4(2).
- Deng X., Papadimitriou C. (1994), On the Complexity of Cooperative Solution
  Concepts, Mathematics of Operations Research 19(2) (#P-difficulte du calcul).
- Felsenthal D., Machover M. (1998), The Measurement of Voting Power, Edward Elgar.
- Tang P., Lin F. (2009), Computer-Aided Proofs of Arrow's and Other Impossibility
  Theorems, Artificial Intelligence 173(11).
- de Moura L., Bjorner N. (2008), Z3 : An Efficient SMT Solver, TACAS.
- Sources de donnees : Assemblee nationale (composition des groupes), ministere
  de l'Interieur (resultats des elections europeennes 2024).
