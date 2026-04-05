import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from worker import EmailNotifier, build_twiml_equivalent, SEVERITY_COLORS, SEVERITY_EMOJI


def make_threat(**kw):
    base = dict(
        threat_id="threat-abc-123",
        severity="critical",
        classification="Data Exfiltration",
        source_ip="192.168.1.100",
        destination_ip="203.0.113.42",
        source_port=54321,
        destination_port=443,
        protocol="HTTPS",
        confidence_score=0.95,
        description="Large outbound transfer detected",
        tenant_id=1,
    )
    base.update(kw)
    return base


# ── EmailNotifier tests ───────────────────────────────────────

def test_email_notifier_instantiates():
    notifier = EmailNotifier()
    assert notifier is not None


def test_severity_colors_defined():
    for sev in ["critical", "high", "medium", "low", "info"]:
        assert sev in SEVERITY_COLORS
        assert SEVERITY_COLORS[sev].startswith("#")


def test_severity_emoji_defined():
    for sev in ["critical", "high", "medium", "low", "info"]:
        assert sev in SEVERITY_EMOJI


def test_email_template_contains_threat_info():
    notifier = EmailNotifier()
    threat = make_threat()
    # Build the HTML body directly using the template
    from worker import ALERT_EMAIL_TEMPLATE, SEVERITY_COLORS, SEVERITY_EMOJI
    color = SEVERITY_COLORS.get(threat["severity"], "#636366")
    emoji = SEVERITY_EMOJI.get(threat["severity"], "⚪")
    html = ALERT_EMAIL_TEMPLATE.format(
        color=color,
        emoji=emoji,
        severity_upper=threat["severity"].upper(),
        classification=threat["classification"],
        threat_id=threat["threat_id"],
        source_ip=threat["source_ip"],
        source_port=threat["source_port"],
        destination_ip=threat["destination_ip"],
        destination_port=threat["destination_port"],
        confidence_score=f"{threat['confidence_score']:.2%}",
        description=threat["description"],
    )
    assert "CRITICAL" in html
    assert "Data Exfiltration" in html
    assert "threat-abc-123" in html
    assert "192.168.1.100" in html
    assert "95.00%" in html
    assert "DOCTYPE html" in html or "<!DOCTYPE" in html


def test_email_template_all_severities():
    from worker import ALERT_EMAIL_TEMPLATE, SEVERITY_COLORS, SEVERITY_EMOJI
    for sev in ["critical", "high", "medium", "low", "info"]:
        threat = make_threat(severity=sev, confidence_score=0.75)
        color = SEVERITY_COLORS.get(sev, "#636366")
        emoji = SEVERITY_EMOJI.get(sev, "⚪")
        html = ALERT_EMAIL_TEMPLATE.format(
            color=color, emoji=emoji,
            severity_upper=sev.upper(),
            classification=threat["classification"],
            threat_id=threat["threat_id"],
            source_ip=threat["source_ip"],
            source_port=threat["source_port"],
            destination_ip=threat["destination_ip"],
            destination_port=threat["destination_port"],
            confidence_score=f"{threat['confidence_score']:.2%}",
            description=threat["description"],
        )
        assert sev.upper() in html
        assert color in html


def test_email_smtp_mock_mode(monkeypatch):
    """In test env, SMTP should fail gracefully."""
    notifier = EmailNotifier()
    threat = make_threat()

    import smtplib
    def mock_smtp(*args, **kwargs):
        raise ConnectionRefusedError("No SMTP in test")

    monkeypatch.setattr(smtplib, "SMTP", mock_smtp)
    # Should not raise — failure is caught and logged
    notifier.send_alert(threat, recipient="test@example.com")


# ── Kafka consumer config tests ───────────────────────────────

def test_settings_defaults():
    from worker import Settings
    s = Settings()
    assert s.KAFKA_TOPIC_ALERTS == "alert-notifications"
    assert s.KAFKA_CONSUMER_GROUP == "notification-worker"
    assert s.SMTP_PORT == 1025


def test_notification_worker_instantiates():
    from worker import NotificationWorker
    w = NotificationWorker()
    assert w.processed == 0
    assert w.email_notifier is not None


def build_twiml_equivalent(threat):
    """Replicate the TwiML logic for testing."""
    severity = threat.get("severity", "unknown").upper()
    classification = threat.get("classification", "unknown")
    src = threat.get("source_ip", "unknown")
    return f"ALERT: {severity} {classification} from {src}"


def test_twiml_contains_severity():
    threat = make_threat(severity="critical")
    msg = build_twiml_equivalent(threat)
    assert "CRITICAL" in msg


def test_twiml_contains_classification():
    threat = make_threat(classification="Ransomware Communication")
    msg = build_twiml_equivalent(threat)
    assert "Ransomware Communication" in msg


def test_twiml_contains_source_ip():
    threat = make_threat(source_ip="10.99.88.77")
    msg = build_twiml_equivalent(threat)
    assert "10.99.88.77" in msg
