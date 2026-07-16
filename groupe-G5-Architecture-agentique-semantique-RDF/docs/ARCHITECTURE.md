# Notes d'architecture

## 1. Pourquoi un blackboard RDF à graphes nommés ?

Les architectures multi-agents classiques opposent la communication par
messages (FIPA-ACL) et la coordination par espace partagé (blackboard). Notre
coordination est **centralisée et pilotée par le plan** : l'orchestrateur
séquence les agents et réagit à la valeur de retour de chaque action. Le
**blackboard est un `rdflib.Dataset`** dont les graphes nommés isolent les
responsabilités (faits assertés par document, faits inférés, rapports SHACL,
liens, journal d'évènements, TBox), et les **évènements sémantiques** sont
décrits en RDF et journalisés dans le blackboard — non pour piloter le flux de
contrôle, mais pour la traçabilité. Deux bénéfices :

1. **Provenance native** : on distingue toujours ce qui a été asserté,
   inféré, validé ou lié — condition nécessaire à un raisonnement auditable.
2. **Homogénéité représentationnelle** : l'état du système *et* son historique
   sont dans le même formalisme que les données traitées ; le pipeline peut
   s'introspecter en SPARQL (« combien de violations l'agent de validation
   a-t-il levées ce mois-ci ? » est une simple requête sur `urn:graph:events`).

## 2. Planification PDDL et indéterminisme du monde

La planification classique suppose des actions déterministes, or l'issue
d'une validation SHACL ou d'un parsing est inconnue au moment de planifier.
Plutôt que de recourir à de la planification contingente (FOND, coûteuse),
nous adoptons le schéma **plan – exécution – supervision – replanification** :

* le domaine PDDL modélise les issues *nominales* des actions ;
* l'orchestrateur compare l'issue réelle (évènement émis) à l'effet attendu ;
* en cas de contradiction, il **corrige l'état symbolique** (`(failed d)`) et
  replanifie ; la structure du domaine (précondition négative `(not (failed
  ?d))` sur toutes les actions nominales, action `quarantine` de garde) fait
  que le nouveau plan optimal emprunte nécessairement la route de quarantaine.

Le planificateur (`src/rdf_agents/planner.py`, ~220 lignes) implémente :
parsing s-expressions du PDDL, listes typées, grounding par produit
cartésien sur les objets typés, et recherche en largeur sur des états
`frozenset` de faits ground — optimalité en nombre d'actions garantie. Sur ce
domaine (8 schémas d'action, 1 objet), l'espace d'états est minuscule et la
planification prend < 1 ms ; le même code passe à l'échelle de plusieurs
documents simultanés (cf. `test_multi_document_grounding`).

## 3. Alternative : orchestration Semantic Kernel

Le sujet propose PDDL **ou** Semantic Kernel (SK). Nous avons retenu PDDL car
il garde l'ordonnancement entièrement **symbolique, explicable et vérifiable**
(le plan est un objet de première classe que l'on peut tester). Une
orchestration SK remplacerait l'orchestrateur par un planner LLM (function
calling sur les `perform` des agents exposés comme plugins) ; l'interface
`Agent.handles`/`Agent.perform` a été conçue pour que cette substitution soit
locale à `orchestrator.py`, sans toucher aux agents. Le compromis est
classique : flexibilité linguistique du LLM contre garanties formelles du
planificateur symbolique.

## 4. Choix de raisonnement

* **OWL-RL** (bibliothèque `owlrl`) plutôt qu'un raisonneur DL complet
  (HermiT/Pellet) : profil OWL 2 conçu pour la matérialisation par règles sur
  des données à grande échelle, en cohérence avec un pipeline de flux. Les
  axiomes de l'ontologie ont été choisis pour rester dans le fragment RL
  (subsomption, disjonction, inverses, transitivité, `someValuesFrom` en
  sous-classe). En particulier, la règle « jeu de données publié par un
  organisme public ⊑ GovDataset » est axiomatisée par un `rdfs:subClassOf`
  direct sur l'intersection anonyme `dcat:Dataset ⊓ ∃dct:publisher.PublicBody`
  (`someValuesFrom` en position sous-classe) et **non** par un
  `owl:equivalentClass` : la grammaire OWL 2 RL interdit `someValuesFrom` en
  super-classe/équivalence, et seule la direction antécédent ⊑ conséquent est
  nécessaire à l'inférence.
* **Détection d'inconsistance** : `owlrl` matérialise les contradictions
  (règle `cax-dw` sur les classes disjointes) sous forme de noeuds
  `ErrorMessage` ; le `ReasoningAgent` les convertit en évènement
  `InconsistencyDetected`, traité par l'orchestrateur comme un échec.
* **Re-validation post-inférence** : la clôture déductive peut créer de
  nouvelles cibles pour les shapes (p.ex. un individu nouvellement typé
  `foaf:Person` devient cible de `PersonShape`) ; le plan nominal inclut donc
  systématiquement `revalidate` après `reason`. Ce cas — conforme à
  l'assertion mais violant après inférence — est exercé par
  `doc7_postinference_violation.ttl` et le test
  `test_revalidation_failure_after_inference_triggers_replanning`.

## 5. Reproductibilité

L'ensemble s'exécute hors-ligne : corpus embarqué (représentatif de
data.gouv.fr / DBpedia / Wikidata) et cache local d'extraits Linked Data.
L'interrogation directe des endpoints publics DBpedia/Wikidata (avec repli sur
le cache) est une extension prévue mais non implémentée.
