# G3 — GraphRAG : Design Spec

**Projet** : EPITA 2026 — Intelligence Symbolique  
**Groupe** : Paul Witkowski & Matteo Atkinson  
**Sujet** : Combine Knowledge Graphs et LLM pour le RAG  
**Date** : 2026-06-13

---

## 1. Vue d'ensemble

Deux livrables de même importance :

- **A — Notebooks** : SW-11 et SW-12 enrichis (import `graphrag_core`) + `benchmark.ipynb` (GraphRAG vs RAG classique sur HotpotQA/MuSiQue)
- **B — App web** : FastAPI backend + HTML/JS frontend — démo live du pipeline GraphRAG avec upload de documents, construction du KG et interface Q&A

Tout le code métier vit dans un package Python partagé `graphrag_core/` importé par les deux livrables. Un seul `.env` à la racine configure l'ensemble.

---

## 2. Structure du projet

```
groupe-G3-GraphRAG-.../
├── .env                          ← configuration unique
├── graphrag_core/
│   ├── __init__.py
│   ├── llm.py                    ← abstraction multi-provider
│   ├── extractor.py              ← extraction entités/relations via LLM
│   ├── graph.py                  ← construction KG RDF + community detection
│   ├── retriever.py              ← subgraph extraction multi-hop + trace
│   └── pipeline.py               ← orchestration complète
├── app/
│   ├── main.py                   ← FastAPI routes
│   ├── models.py                 ← Pydantic schemas
│   └── static/
│       ├── index.html            ← frontend single-page
│       └── style.css
├── notebooks/
│   ├── SW-11-Python-KnowledgeGraphs.ipynb   ← déplacé depuis la racine, enrichi
│   ├── SW-12-Python-GraphRAG.ipynb          ← déplacé depuis la racine, enrichi
│   ├── SW-4b-Python-SPARQL.ipynb            ← déplacé depuis la racine
│   └── benchmark.ipynb                      ← nouveau
├── data/
│   ├── hotpotqa/                 ← subset HotpotQA multi-hop
│   └── custom/                   ← corpus uploadé par l'utilisateur
└── docs/
    └── 2026-06-13-G3-graphrag-design.md     ← ce fichier
```

---

## 3. Configuration `.env`

```env
# LLM
LLM_PROVIDER=openai             # openai | anthropic | ollama
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...           # si LLM_PROVIDER=openai
ANTHROPIC_API_KEY=sk-ant-...    # si LLM_PROVIDER=anthropic
OLLAMA_BASE_URL=http://localhost:11434  # si LLM_PROVIDER=ollama

# App
APP_HOST=0.0.0.0
APP_PORT=8000
DATA_DIR=./data
```

Chargé via `python-dotenv` dans `graphrag_core/`, `app/main.py` et les notebooks (`load_dotenv()` en cellule d'init).

---

## 4. `graphrag_core/` — Package partagé

### `llm.py`
Interface unique `LLMClient.complete(prompt: str) -> str` avec implémentations pour OpenAI, Anthropic (claude-haiku-4-5 / sonnet) et Ollama. Le provider est résolu depuis `LLM_PROVIDER` dans le `.env`.

### `extractor.py`
Reçoit un chunk de texte, envoie un prompt structuré au LLM, retourne une liste de triplets `(sujet, relation, objet)` en JSON. Gère le chunking et la déduplication.

### `graph.py`
- Construit le graphe RDF avec `rdflib` à partir des triplets extraits
- Convertit vers NetworkX pour la community detection
- Lance l'algorithme de Leiden (`leidenalg` via conversion NetworkX → igraph) pour partitionner en communautés thématiques
- Expose : graphe NetworkX, nœuds/arêtes sérialisables JSON, communautés avec labels

### `retriever.py`
- BFS multi-hop depuis les entités détectées dans la question (max 2 hops par défaut)
- Retourne le sous-graphe pertinent + la trace complète :
  ```python
  TraceStep(hop=1, from_node="GraphRAG", relation="AUTHORED_BY", to_nodes=["Darren Edge", ...])
  ```
- Identifie les documents sources ayant contribué aux triplets du sous-graphe

### `pipeline.py`
Orchestration : `run(question: str, graph: nx.Graph) -> PipelineResult`
```python
PipelineResult(
    answer=str,
    trace=list[TraceStep],
    docs_used=list[DocReference],
    subgraph_nodes=list[str],
    subgraph_edges=list[tuple]
)
```

---

## 5. App Web — FastAPI

### Routes

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/upload` | Upload fichiers → sauvegarde dans `data/custom/` |
| `POST` | `/build` | Lance pipeline extraction+KG, stream SSE des 4 étapes |
| `GET` | `/graph` | Retourne graphe courant (nœuds, arêtes, communautés) JSON |
| `POST` | `/query` | Question → `pipeline.run()` → `QueryResponse` |
| `GET` | `/datasets` | Liste datasets disponibles (hotpotqa, custom) |
| `POST` | `/dataset/select` | Active un dataset |

### SSE `/build` — 4 étapes streamées
1. `extraction` — extraction entités/relations (N docs traités)
2. `graph_build` — construction du graphe RDF
3. `community_detection` — Leiden sur NetworkX
4. `indexing` — préparation pour le retrieval

### `QueryResponse` schema
```json
{
  "answer": "...",
  "trace": [
    {"hop": 1, "from": "GraphRAG", "relation": "AUTHORED_BY", "to": ["Darren Edge"]},
    {"hop": 2, "from": "Darren Edge", "relation": "WORKS_AT", "to": ["Microsoft Research"]}
  ],
  "docs_used": [
    {"filename": "graphrag_paper.pdf", "pages": [1, 2, 12]},
    {"filename": "knowledge_base.md", "sections": ["Auteurs & affiliations"]}
  ],
  "subgraph_nodes": ["GraphRAG", "Microsoft", "Darren Edge"],
  "subgraph_edges": [["GraphRAG", "AUTHORED_BY", "Darren Edge"]]
}
```

---

## 6. Frontend — HTML/JS

### Layout général
- **Nav** (sticky, glassmorphism) : logo + badge EPITA 2026 + indicateur d'étape en 3 pills (① Upload → ② Build KG → ③ Query)
- **Sidebar gauche** (320px, persistante dans les deux tabs) :
  - Zone de drop drag & drop (PDF, TXT, Markdown)
  - Toggle dataset : `HotpotQA | Corpus custom`
  - Liste des documents avec statut (✓ ou ⚙ En cours)
  - Bouton "Construire le Knowledge Graph" / état post-build
  - Bouton "Réinitialiser" pour supprimer le corpus custom (visible uniquement quand le toggle "Corpus custom" est actif)
- **Zone droite** avec 2 tabs :
  - **💬 Q&A** — interface chat + drawer de détail
  - **🕸 Graphe de connaissances** — visualisation plein écran

### Tab Q&A
- Messages utilisateur (bulle indigo droite) et réponses GraphRAG (bulle blanche gauche)
- Chaque réponse a une **bulle cliquable** (chip) : `⚡ N-hop · N entités · N docs — voir le détail`
- Clic sur le chip → drawer animé (CSS transition `max-height`) révélant :
  - Étapes de raisonnement numérotées (nœud de départ, hop 1, hop 2…) avec entity tags
  - Documents sources avec noms de fichier et pages/sections
- Barre d'input bloquée (disabled + badge explicatif) pendant les états ① et ② :
  - ① : badge "Uploadez vos documents d'abord"
  - ② : badge "Construction du KG en cours…" + barre de progression SSE avec 4 sous-étapes
  - ③ : input et bouton actifs

### Tab Graphe
- **Toolbar** : stats (N entités, N relations, N communautés) + filtres par communauté (badges colorés cliquables)
- **Graphe D3.js** force-directed :
  - Nœuds colorés par communauté (couleur assignée dynamiquement selon l'index de communauté : indigo, violet, ambre… selon le nombre détecté)
  - Zones communautés en ellipses pointillées avec label
  - Arêtes fléchées avec labels de relation
  - Halos lumineux (radial gradient SVG) sur les nœuds centraux
  - Highlight ambre des nœuds/arêtes utilisés pour la dernière réponse Q&A
  - Tooltip au clic sur un nœud : nom, type, liste des relations

### Style visuel
- Palette : tons indigo `#6366f1` / violet `#8b5cf6`, fond `#f0f4ff`
- Effets lumineux : blobs floutés en position fixe (glow background), halos SVG sur les nœuds, ombres colorées sur les boutons
- Glassmorphism nav : `backdrop-filter: blur(12px)` + fond blanc semi-transparent
- Animations : chip drawer (CSS), barre de progression (SSE), dot "live" pulsant
- Librairies frontend : D3.js (graphe), pas de framework JS

---

## 7. Notebooks

### SW-11, SW-12 et SW-4b (déplacés + enrichis)
Les trois notebooks existants à la racine du dossier G3 sont déplacés dans `notebooks/`. Les cellules de démonstration existantes restent intactes. Les exercices et exemples guides ajoutent des imports depuis `graphrag_core` pour illustrer l'usage du pipeline réel, sans remplacer le code pédagogique existant.

### `benchmark.ipynb` (nouveau)
- Chargement d'un subset HotpotQA (500 questions)
- Exécution pipeline GraphRAG vs RAG vectoriel classique (embeddings cosinus)
- Métriques : F1, Exact Match sur les réponses
- Visualisations : courbes comparatives, distribution des hops, impact de la community detection (Leiden vs Louvain)

---

## 8. Données

- **HotpotQA** : téléchargement d'un subset (500 questions) depuis le dataset officiel, stocké dans `data/hotpotqa/`
- **Corpus custom** : fichiers uploadés via le frontend, stockés dans `data/custom/`. Persistants entre sessions ; supprimés uniquement sur action explicite de l'utilisateur (bouton "Réinitialiser" dans la sidebar).

---

## 9. Ce qui n'est pas dans la démo

- Comparaison GraphRAG vs RAG classique → **dans `benchmark.ipynb` uniquement**
- Évaluation automatique (F1/EM) → notebook uniquement
- Authentification, multi-utilisateur → hors scope

---

## 10. Livrables finaux

| Livrable | Forme | Deadline |
|---------|-------|----------|
| Code source `graphrag_core/` + `app/` | Python | PR -2j avant soutenance |
| Notebooks SW-11, SW-12, benchmark | Jupyter | PR -2j avant soutenance |
| Slides de soutenance | PDF ou lien | Jour J |
| Pull Request | GitHub | PR -2j avant soutenance |
