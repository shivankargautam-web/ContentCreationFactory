import pytest
from pydantic import ValidationError

from app.schemas.agent_outputs import SEOResult
from app.schemas.auth import RegisterRequest
from app.schemas.campaign import CampaignCreate


def test_hashtags_normalized_and_deduped() -> None:
    seo = SEOResult(title="t", description="d", hashtags=["kafka", "#Kafka", "#system design!", "#shorts"])
    assert seo.hashtags == ["#kafka", "#systemdesign", "#shorts"]
    assert seo.caption.endswith("#kafka #systemdesign #shorts")


def test_register_requires_letters_and_digits() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.co", password="onlyletters")


def test_campaign_create_rejects_bad_timezone() -> None:
    with pytest.raises(ValidationError):
        CampaignCreate(instruction="Generate 3 shorts about x", timezone="Mars/Olympus")
