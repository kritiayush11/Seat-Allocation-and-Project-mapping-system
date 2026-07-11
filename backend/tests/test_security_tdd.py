import pytest
from app.config import get_settings

def test_jwt_secret_key_security():
    """TDD: Ensure the JWT secret key is securely generated and not the hardcoded default key."""
    settings = get_settings()
    assert settings.JWT_SECRET_KEY != "ethara_super_secret_signing_key_2026_prod"
    assert len(settings.JWT_SECRET_KEY) >= 32
