from typing import Any, Dict, List, Tuple

from cfg import DEFAULT_TARGET_LABELS, RULES_EXCLUDE, RULES_INCLUDE, SYSTEM_LABELS, THRESHOLDS
from data_store import fetch_for_prediction, save_prediction
from model import predict


def suggest_label(text: str, model_label: str) -> str:
    # bias by rules
    text_l = text.lower()
    scores = {lab: 0 for lab in DEFAULT_TARGET_LABELS}
    for lab, kws in RULES_INCLUDE.items():
        for kw in kws:
            if kw in text_l:
                scores[lab] = scores.get(lab, 0) + 1
    for lab, kws in RULES_EXCLUDE.items():
        for kw in kws:
            if kw in text_l:
                scores[lab] = -999
    # choose between rules and model label
    best_rule = max(scores, key=lambda k: scores[k]) if scores else None
    if best_rule and scores[best_rule] > 0 and best_rule != model_label:
        return best_rule
    return model_label


def propose(limit: int = 100) -> List[Dict[str, Any]]:
    rows = fetch_for_prediction(limit=limit)
    if not rows:
        return []
    texts = [r.text for r in rows]
    labels, conf, spam_scores = predict(texts)
    actions = []
    for r, lab, c, sp in zip(rows, labels, conf, spam_scores):
        target = None
        action = "review"
        if sp >= THRESHOLDS["spam"]:
            action = "trash"
        else:
            # route if confident else review
            t = suggest_label(r.text, lab)
            if c >= THRESHOLDS["certain"]:
                action = "route"
                target = t
            else:
                target = t
        save_prediction(r.id, float(sp), lab, target)
        actions.append(
            {
                "id": r.id,
                "snippet": r.snippet,
                "spam_score": float(sp),
                "conf": float(c),
                "pred_label": lab,
                "target": target,
                "action": action,
            }
        )
    return actions
