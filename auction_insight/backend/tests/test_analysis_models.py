from app.analysis import models as analysis_models  # noqa: F401
from app.analysis.money import detect_digit_errors


def test_import_analysis_models():
    assert analysis_models.AuctionItem.__tablename__ == "analysis_auction_items"


def test_digit_sentinel_pair():
    """Canonical example from product brief: 40,200,000 vs 402,000,000."""
    w = detect_digit_errors(appraisal_won=402_000_000, min_bid_won=40_200_000)
    assert any(x["code"] == "DIGIT_FACTOR" for x in w)
