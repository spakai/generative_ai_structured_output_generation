PLAN_DOCUMENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Streaming Subscription Plans",
    "type": "object",
    "required": ["plans"],
    "properties": {
        "version": {"type": "string"},
        "metadata": {"type": "object"},
        "plans": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "name", "region", "tier", "price", "device_limit", "video_quality"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "region": {"type": "string", "minLength": 1},
                    "tier": {"type": "string", "minLength": 1},
                    "price": {
                        "type": "object",
                        "required": ["monthly", "currency"],
                        "properties": {
                            "monthly": {"type": "number", "minimum": 0},
                            "currency": {"type": "string", "pattern": "^[A-Z]{3}$"}
                        }
                    },
                    "device_limit": {"type": "integer", "minimum": 0, "maximum": 8},
                    "video_quality": {"type": "string", "minLength": 2},
                    "description": {"type": "string"},
                    "add_ons": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "price_delta"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "price_delta": {"type": "number", "minimum": 0},
                                "description": {"type": "string"}
                            }
                        },
                        "uniqueItems": True
                    }
                },
                "additionalProperties": False
            },
            "uniqueItems": True
        }
    },
    "additionalProperties": False
}

