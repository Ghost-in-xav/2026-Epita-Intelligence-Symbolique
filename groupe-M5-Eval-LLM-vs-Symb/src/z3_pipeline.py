from z3 import *
import re

class SymbolicEvaluator:
    def __init__(self):
        pass

    def _parse_and_translate(self, context):
        solver = Solver()
        
        # Normalisation basique
        context = context.lower().replace('.', ' .').replace('?', '')
        sentences = [s.strip() for s in context.split('.') if s.strip()]
        
        person_locs = {} # Dictionnaire pour stocker les variables Z3 de localisation
        
        def get_loc(p):
            if p not in person_locs:
                # Crée une variable SMT (String) pour représenter le lieu de la personne
                person_locs[p] = Const(f'loc_{p}', StringSort())
            return person_locs[p]
        
        for sentence in sentences:
            # Règle 1: "X est dans Y"
            match_in = re.search(r'([a-z\']+)\s+(est dans le|est dans la|va dans la|est sur le|est sur la|est à l\'|est au|est à la)\s+([a-z\s\']+)', sentence)
            
            if match_in:
                person_name = match_in.group(1).replace("'", "")
                loc_name = match_in.group(3).strip().replace("'", "")
                
                # Le lieu de la personne EST la chaîne de caractères
                solver.add(get_loc(person_name) == StringVal(loc_name))
                
            # Règle 2: "X est avec Y"
            match_with = re.search(r'([a-z\']+)\s+(est avec|rejoint)\s+([a-z\']+)', sentence)
            if match_with:
                person1 = match_with.group(1).replace("'", "")
                person2 = match_with.group(3).replace("'", "")
                
                # Le lieu de la personne 1 EST le lieu de la personne 2
                solver.add(get_loc(person1) == get_loc(person2))

        return solver, person_locs

    def evaluate(self, context, question):
        try:
            solver, person_locs = self._parse_and_translate(context)
            
            match_q = re.search(r'où est (le |la |l\')?([a-z\']+)', question.lower())
            if not match_q:
                return "Erreur de traduction (Question)"
                
            person_q = match_q.group(2).replace("'", "")
            
            if person_q not in person_locs:
                return "Erreur de traduction (Entité non trouvée)"
            
            if solver.check() == sat:
                m = solver.model()
                # On récupère la valeur de la variable Z3 correspondant au lieu de la personne
                ans = m[person_locs[person_q]]
                if ans is not None:
                    return str(ans).strip('"')
            
            return "Erreur de traduction (Insoluble)"
            
        except Exception:
            return "Erreur de traduction (Exception)"
