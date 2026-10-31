from datetime import datetime, timedelta, timezone

import pytest

from dataload.generators import (
    alerts_history,
    chat_feedback,
    chat_sessions,
    consumption_summary,
    device_status,
    pulses_raw,
    user_preferences,
)


def test_consumption_summary_has_five_minute_windows_and_threshold_consistency():
    documents = consumption_summary.gerar(25)

    assert len(documents) == 25
    assert len({document["device_id"] for document in documents}) == 25
    assert [document["user_id"] for document in documents] == list(range(200, 225))
    for document in documents:
        assert document["window_finished_at"] - document["window_started_at"] == timedelta(
            minutes=5
        )
        assert document["window_started_at"].utcoffset() == timedelta(0)
        assert document["consumption_liters"] >= 0
        assert document["lpm_average"] == document["consumption_liters"] / 5
        assert document["anomaly_detected"] is (
            document["consumption_liters"] >= 15.0
        )
    assert documents[0]["window_started_at"] > documents[-1]["window_started_at"]


def test_device_status_samples_unique_devices_with_coherent_states():
    documents = device_status.gerar(6)

    assert len(documents) == 6
    assert len({document["device_id"] for document in documents}) == 6
    states = {document["connectivity_status"]: document for document in documents}
    assert set(states) == {"online", "unstable", "offline"}
    assert states["online"]["unavailability_reason"] is None
    assert states["unstable"]["unavailability_reason"] == "SINAL WI-FI INSTÁVEL"
    assert states["offline"]["unavailability_reason"] == "SEM CONEXÃO COM O DISPOSITIVO"
    observed_ping_ages = {
        status: round((datetime.now(timezone.utc) - item["last_ping_at"]).total_seconds() / 60)
        for status, item in states.items()
    }
    assert observed_ping_ages == {"online": 2, "unstable": 15, "offline": 90}
    assert all(document["last_ping_at"].utcoffset() == timedelta(0) for document in documents)


def test_user_preferences_have_unique_int32_safe_users_and_supported_quiet_hours():
    documents = user_preferences.gerar(50)

    user_ids = [document["user_id"] for document in documents]
    assert len(user_ids) == len(set(user_ids))
    assert all(1_000 <= user_id < 2_000_000_000 for user_id in user_ids)
    for document in documents:
        assert 100 <= document["daily_liters_target"] <= 500
        assert isinstance(document["notifications_enabled"], bool)
        assert isinstance(document["dark_mode_enabled"], bool)
        assert document["quiet_hours"] in user_preferences.HORARIOS_SILENCIOSOS
    assert len({id(document["quiet_hours"]) for document in documents}) == len(documents)


def test_alerts_match_type_severity_and_resolution_never_precedes_trigger(monkeypatch):
    original_choice = alerts_history.random.choice
    resolution_choices = iter([True, False, True, False])

    def controlled_choice(values):
        if values == (True, False):
            return next(resolution_choices)
        return original_choice(values)

    monkeypatch.setattr(alerts_history.random, "choice", controlled_choice)
    documents = alerts_history.gerar(4)
    now = datetime.now(timezone.utc)

    assert any(document["resolved_at"] is None for document in documents)
    assert any(document["resolved_at"] is not None for document in documents)
    for document in documents:
        assert document["severity"] in alerts_history.SEVERIDADES_POR_ALERTA[
            document["alert_type"]
        ]
        assert now - timedelta(days=30) <= document["triggered_at"] <= now
        if document["resolved_at"] is not None:
            assert document["triggered_at"] < document["resolved_at"] <= now


def test_chat_sessions_keep_messages_ordered_and_active_sessions_open(monkeypatch):
    states = iter([True, True, False, True, False, False])

    def controlled_choice(values):
        if isinstance(values, (tuple, list)) and values == [True, False]:
            return next(states)
        return values[0]

    monkeypatch.setattr(chat_sessions.random, "choice", controlled_choice)
    documents = chat_sessions.gerar(4)

    assert [document["started_at"] for document in documents] == sorted(
        document["started_at"] for document in documents
    )
    assert any(document["is_open"] for document in documents)
    assert any(not document["is_open"] for document in documents)
    for document in documents:
        user_message, bot_message = document["messages"]
        assert user_message["role"] == "user"
        assert bot_message["role"] == "bot"
        assert document["started_at"] < user_message["sent_at"] < bot_message["sent_at"]
        assert document["last_activity_at"] == bot_message["sent_at"]
        assert not document["is_active"] or document["is_open"]
        assert document["is_deleted"] is False


def test_chat_feedback_uses_existing_session_ids_and_newest_first(monkeypatch):
    class Sessions:
        def find(self, query, projection):
            assert query == {}
            assert projection == {"_id": 1}
            return [{"_id": "session-a"}, {"_id": "session-b"}]

    monkeypatch.setattr(chat_feedback, "obter_colecao", lambda *args: Sessions())
    feedback = chat_feedback.gerar(4)

    assert all(item["session_id"] in {"session-a", "session-b"} for item in feedback)
    assert all(isinstance(item["is_satisfied"], bool) for item in feedback)
    assert [item["created_at"] for item in feedback] == sorted(
        (item["created_at"] for item in feedback), reverse=True
    )
    assert len({item["created_at"] for item in feedback}) == 4


def test_chat_feedback_fails_clearly_when_there_are_no_sessions(monkeypatch):
    class EmptySessions:
        def find(self, query, projection):
            return []

    monkeypatch.setattr(chat_feedback, "obter_colecao", lambda *args: EmptySessions())

    with pytest.raises(chat_feedback.SemSessoesChatError, match="chat_sessions"):
        chat_feedback.gerar(1)


def test_raw_pulse_packets_preserve_window_delta_and_uptime_order():
    documents = pulses_raw.gerar(8)
    assert len({document["device_id"] for document in documents}) == 1
    assert [document["sent_at"] for document in documents] == sorted(
        document["sent_at"] for document in documents
    )

    last_uptime = 0
    for document in documents:
        assert document["window_minutes"] == 5
        assert 1 <= document["total_pulses"] <= 8
        assert len(document["pulses"]) == document["total_pulses"]
        previous = None
        for pulse in document["pulses"]:
            assert document["sent_at"] - timedelta(minutes=5) < pulse["pulsed_at"] < document["sent_at"]
            assert pulse["ms_since_boot"] > last_uptime
            if previous is None:
                assert pulse["delta_ms"] == 0
            else:
                delta = pulse["pulsed_at"] - previous["pulsed_at"]
                assert pulse["delta_ms"] == delta // timedelta(milliseconds=1)
            previous = pulse
            last_uptime = pulse["ms_since_boot"]


def test_continuous_pulses_sleep_only_until_deadline_and_reject_nonpositive_interval(
    monkeypatch,
):
    clock = {"now": 0.0}
    sleeps = []
    monkeypatch.setattr(pulses_raw.time, "monotonic", lambda: clock["now"])

    def sleep(seconds):
        sleeps.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(pulses_raw.time, "sleep", sleep)
    packets = list(pulses_raw.gerar_continuo(intervalo_segundos=2, tempo_maximo=3))

    assert len(packets) == 2
    assert packets[0]["device_id"] == packets[1]["device_id"]
    assert sleeps == [2, 1]
    assert list(pulses_raw.gerar_continuo(intervalo_segundos=1, tempo_maximo=0)) == []

    with pytest.raises(ValueError, match="intervalo_segundos"):
        next(pulses_raw.gerar_continuo(intervalo_segundos=0, tempo_maximo=1))


def test_continuous_pulses_stop_without_sleep_when_deadline_is_reached(monkeypatch):
    clock_values = iter([0.0, 0.0, 3.0])
    sleeps = []
    monkeypatch.setattr(pulses_raw.time, "monotonic", lambda: next(clock_values))
    monkeypatch.setattr(pulses_raw.time, "sleep", sleeps.append)

    packets = list(pulses_raw.gerar_continuo(intervalo_segundos=5, tempo_maximo=3))

    assert len(packets) == 1
    assert sleeps == []
