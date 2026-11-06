"""Explainable rule-based fraud screening for the B.Tech demo.
Replace with a trained classifier only after validating a suitable labelled dataset.
"""
def predict_fraud(amount: float, description: str = "") -> dict:
    reasons = []
    score = 0.0
    if amount >= 25000:
        score += 0.65
        reasons.append("amount is unusually high for this demo")
    elif amount >= 15000:
        score += 0.35
        reasons.append("amount exceeds the demo review threshold")
    suspicious_terms = ["urgent", "gift card", "password", "crypto", "prize"]
    found = [term for term in suspicious_terms if term in (description or "").lower()]
    if found:
        score += 0.45
        reasons.append("description contains risk keyword(s): " + ", ".join(found))
    score = min(score, 1.0)
    return {
        "is_fraud": score >= 0.65,
        "risk_score": round(score * 100, 2),
        "reason": "; ".join(reasons) if reasons else "No demo risk rule triggered"
    }
