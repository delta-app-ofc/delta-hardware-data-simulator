"""Gerador da coleção user_preferences."""

import random


HORARIOS_SILENCIOSOS = (
    {"start_hour": "21:00", "end_hour": "06:00"},
    {"start_hour": "22:00", "end_hour": "06:00"},
    {"start_hour": "22:30", "end_hour": "07:00"},
    {"start_hour": "23:00", "end_hour": "07:00"},
)


def gerar(quantidade: int) -> list[dict]:
    """Gera preferências com um user_id BSON int32 único por documento."""
    user_ids = random.sample(range(1_000, 2_000_000_000), quantidade)

    return [
        {
            "user_id": user_id,
            "daily_liters_target": random.randint(100, 500),
            "notifications_enabled": random.choice((True, False)),
            "quiet_hours": random.choice(HORARIOS_SILENCIOSOS).copy(),
            "dark_mode_enabled": random.choice((True, False)),
        }
        for user_id in user_ids
    ]
