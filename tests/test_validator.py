from subscription_plans.validator import PlanValidator


def test_basic_plan_cannot_exceed_device_limit():
    payload = {
        "version": "1.0",
        "plans": [
            {
                "id": "basic-1",
                "name": "Basic Plan",
                "region": "US",
                "tier": "Basic",
                "price": {"monthly": 9.0, "currency": "USD"},
                "device_limit": 2,
                "video_quality": "HD",
                "add_ons": [],
            }
        ],
    }

    validator = PlanValidator()
    errors, warnings = validator.validate(payload)

    assert "Basic tier plan 'Basic Plan' exceeds 1 device limit." in errors
    assert warnings == []


def test_schema_validation_catches_missing_fields():
    payload = {"plans": [{"id": "x", "name": "Missing price"}]}
    validator = PlanValidator()
    errors, warnings = validator.validate(payload)

    assert any("price" in error for error in errors)
    assert warnings == []
