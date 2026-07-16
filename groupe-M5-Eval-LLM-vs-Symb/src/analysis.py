import pandas as pd

def classify_error(prediction, ground_truth):
    pred_clean = prediction.lower().strip()
    truth_clean = ground_truth.lower().strip()
    
    if truth_clean in pred_clean or pred_clean == truth_clean:
        return "Correct"
        
    if "erreur de traduction" in pred_clean:
        return "Erreur de Traduction"
        
    if pred_clean in ["inconnu", "erreur de raisonnement"] or "erreur api" in pred_clean:
        return "Erreur de Raisonnement"
        
    return "Hallucination / Erreur de Raisonnement"

def evaluate_all_models(data, llm_evaluator, symb_evaluator):
    results = []
    
    examples = data[:3]
    
    for item in data:
        ctx = item['context']
        q = item['question']
        truth = item['answer']
        
        llm_zs_pred = llm_evaluator.evaluate_zero_shot(ctx, q)
        llm_zs_status = classify_error(llm_zs_pred, truth)
        
        llm_fs_pred = llm_evaluator.evaluate_few_shot(ctx, q, examples)
        llm_fs_status = classify_error(llm_fs_pred, truth)
        
        llm_cot_pred = llm_evaluator.evaluate_chain_of_thought(ctx, q)
        llm_cot_status = classify_error(llm_cot_pred, truth)
        
        z3_pred = symb_evaluator.evaluate(ctx, q)
        z3_status = classify_error(z3_pred, truth)
        
        results.append({
            "ID": item["id"],
            "Question": q,
            "Vérité Terrain": truth,
            "LLM_ZS (Statut)": llm_zs_status,
            "LLM_FS (Statut)": llm_fs_status,
            "LLM_CoT (Statut)": llm_cot_status,
            "Z3 (Statut)": z3_status,
            "LLM_ZS (Pred)": llm_zs_pred,
            "LLM_FS (Pred)": llm_fs_pred,
            "LLM_CoT (Pred)": llm_cot_pred,
            "Z3 (Pred)": z3_pred
        })
        
    return pd.DataFrame(results)

def compute_taxonomy_global(df):
    categories = ["Correct", "Erreur de Traduction", "Erreur de Raisonnement", "Hallucination / Erreur de Raisonnement"]
    
    taxonomy_data = []
    
    zs_counts = df['LLM_ZS (Statut)'].value_counts().to_dict()
    fs_counts = df['LLM_FS (Statut)'].value_counts().to_dict()
    cot_counts = df['LLM_CoT (Statut)'].value_counts().to_dict()
    z3_counts = df['Z3 (Statut)'].value_counts().to_dict()
    
    for cat in categories:
        taxonomy_data.append({
            "Catégorie": cat,
            "LLM (Zero-Shot)": zs_counts.get(cat, 0),
            "LLM (Few-Shot)": fs_counts.get(cat, 0),
            "LLM (Chain-of-Thought)": cot_counts.get(cat, 0),
            "Symbolique (Z3)": z3_counts.get(cat, 0)
        })
        
    return pd.DataFrame(taxonomy_data)
