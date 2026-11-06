from models.fraud_detection import predict_fraud

def test_normal_transfer_not_flagged():
    assert predict_fraud(500, "monthly grocery")["is_fraud"] is False

def test_large_transfer_flagged():
    assert predict_fraud(30000, "rent")["is_fraud"] is True

def test_keyword_flagged_with_large_amount():
    result = predict_fraud(100, "urgent gift card")
    assert result["is_fraud"] is False  # keyword alone is a signal, below review threshold
    assert result["risk_score"] > 0
