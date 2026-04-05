"""
Tests for voice-alert-service/service.py
All tests run without Twilio or AWS credentials — mock mode only.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from service import (
    build_twiml_message,
    VoiceAlerter,
    VoiceAlertService,
    Settings,
)


def make_threat(**kw):
    base = dict(
        threat_id="voice-test-001",
        severity="critical",
        classification="Ransomware Communication",
        source_ip="10.0.0.99",
        destination_ip="203.0.113.42",
        source_port=54321,
        destination_port=4444,
        protocol="TCP",
        confidence_score=0.98,
        description="Critical C2 beacon detected",
        tenant_id=1,
    )
    base.update(kw)
    return base


# ── TwiML generation ──────────────────────────────────────────

def test_twiml_is_valid_xml():
    threat = make_threat()
    twiml = build_twiml_message(threat)
    assert twiml.strip().startswith("<?xml")
    assert "<Response>" in twiml
    assert "</Response>" in twiml


def test_twiml_contains_severity():
    threat = make_threat(severity="critical")
    twiml = build_twiml_message(threat)
    assert "CRITICAL" in twiml


def test_twiml_contains_classification():
    threat = make_threat(classification="Data Exfiltration")
    twiml = build_twiml_message(threat)
    assert "Data Exfiltration" in twiml


def test_twiml_contains_source_ip():
    threat = make_threat(source_ip="192.168.99.1")
    twiml = build_twiml_message(threat)
    assert "192.168.99.1" in twiml


def test_twiml_contains_destination_ip():
    threat = make_threat(destination_ip="1.2.3.4")
    twiml = build_twiml_message(threat)
    assert "1.2.3.4" in twiml


def test_twiml_contains_confidence():
    threat = make_threat(confidence_score=0.95)
    twiml = build_twiml_message(threat)
    assert "95" in twiml


def test_twiml_has_polly_voice():
    threat = make_threat()
    twiml = build_twiml_message(threat)
    assert "Polly" in twiml or "voice=" in twiml


def test_twiml_repeats_message():
    """TwiML should Say the message twice for clarity."""
    threat = make_threat()
    twiml = build_twiml_message(threat)
    assert twiml.count("<Say") >= 2


def test_twiml_all_severities():
    for sev in ["critical", "high", "medium", "low"]:
        threat = make_threat(severity=sev)
        twiml = build_twiml_message(threat)
        assert sev.upper() in twiml
        assert "<Response>" in twiml


def test_twiml_missing_fields_handled():
    """Minimal threat dict should not raise."""
    minimal = {"severity": "high"}
    twiml = build_twiml_message(minimal)
    assert "<Response>" in twiml


# ── VoiceAlerter ─────────────────────────────────────────────

def test_voice_alerter_mock_mode():
    """With TWILIO_ACCOUNT_SID=mock, alerter should be in mock mode."""
    alerter = VoiceAlerter()
    assert alerter.mock_mode is True


def test_voice_alerter_call_does_not_raise_in_mock():
    """Mock call should complete without error."""
    alerter = VoiceAlerter()
    threat = make_threat()
    alerter.call(threat)  # should not raise


def test_voice_alerter_call_all_severities():
    alerter = VoiceAlerter()
    for sev in ["critical", "high", "medium", "low"]:
        threat = make_threat(severity=sev)
        alerter.call(threat)  # no exception in mock mode


# ── VoiceAlertService ────────────────────────────────────────

def test_voice_alert_service_instantiates():
    svc = VoiceAlertService()
    assert svc.alerter is not None
    assert svc.calls_made == 0


# ── Settings ─────────────────────────────────────────────────

def test_settings_defaults():
    s = Settings()
    assert s.KAFKA_TOPIC_VOICE == "voice-alerts"
    assert s.KAFKA_CONSUMER_GROUP == "voice-alert"
    assert s.ENVIRONMENT == "development"


def test_settings_mock_twilio_default():
    s = Settings()
    assert s.TWILIO_ACCOUNT_SID == "mock"


# ── Stress: TwiML generation (100 iterations) ─────────────────

def test_twiml_stress_100():
    import random
    ips = [f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
           for _ in range(20)]
    classifications = [
        "Data Exfiltration", "Command & Control", "Ransomware Communication",
        "Port Scan", "Brute Force SSH", "DDoS", "SQL Injection", "Lateral Movement",
    ]
    severities = ["critical", "high", "medium", "low"]
    failures = []

    for i in range(100):
        threat = make_threat(
            severity=random.choice(severities),
            classification=random.choice(classifications),
            source_ip=random.choice(ips),
            destination_ip=random.choice(ips),
            confidence_score=random.uniform(0.5, 1.0),
        )
        twiml = build_twiml_message(threat)
        ok = (
            isinstance(twiml, str) and
            len(twiml) > 100 and
            "<?xml" in twiml and
            "<Response>" in twiml and
            "</Response>" in twiml and
            "<Say" in twiml
        )
        if not ok:
            failures.append(f"Iteration {i}: invalid TwiML")

    assert len(failures) == 0, f"Failures: {failures}"
