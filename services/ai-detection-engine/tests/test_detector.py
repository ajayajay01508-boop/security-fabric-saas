import pytest
import sys
import os
import pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from detector import ThreatDetector


@pytest.fixture
def detector():
    return ThreatDetector()  # heuristic mode (no model file)


def make_event(**kwargs):
    base = {
        "event_id": "test-001",
        "source_ip": "10.0.0.1",
        "destination_ip": "192.168.1.1",
        "source_port": 54321,
        "destination_port": 80,
        "protocol": "TCP",
        "bytes_sent": 1024,
        "bytes_received": 2048,
        "packets": 10,
        "duration_ms": 100,
        "tenant_id": 1,
    }
    base.update(kwargs)
    return base


def test_detector_returns_result(detector):
    event = make_event()
    result = detector.predict(event)
    assert "is_threat" in result
    assert "confidence" in result
    assert "severity" in result
    assert "classification" in result
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0


def test_suspicious_port_raises_score(detector):
    """Events to known suspicious ports should score higher."""
    safe_event    = make_event(destination_port=80)
    suspect_event = make_event(destination_port=4444)  # known C2 port

    safe_result    = detector.predict(safe_event)
    suspect_result = detector.predict(suspect_event)

    assert suspect_result["confidence"] > safe_result["confidence"]


def test_high_packet_count_flags_ddos(detector):
    """Very high packet rate should trigger a threat."""
    event = make_event(packets=50000, destination_port=80)
    results = [detector.predict(event) for _ in range(20)]
    threat_count = sum(1 for r in results if r["is_threat"])
    # At least 50% of runs should flag this as a threat
    assert threat_count >= 10


def test_large_bytes_sent_exfiltration(detector):
    """Large data transfers should push confidence up."""
    event = make_event(bytes_sent=100_000_000)
    results = [detector.predict(event) for _ in range(20)]
    avg_confidence = sum(r["confidence"] for r in results) / len(results)
    assert avg_confidence > 0.4


def test_severity_values_valid(detector):
    valid_severities = {"critical", "high", "medium", "low", "info"}
    for _ in range(50):
        event = make_event(
            destination_port=22,
            packets=100,
            bytes_sent=500,
        )
        result = detector.predict(event)
        assert result["severity"] in valid_severities


def test_non_threat_event(detector):
    """Normal low-volume HTTP traffic should mostly not be flagged."""
    event = make_event(
        destination_port=80,
        protocol="HTTP",
        bytes_sent=1500,
        packets=5,
        duration_ms=50,
    )
    results = [detector.predict(event) for _ in range(30)]
    threat_count = sum(1 for r in results if r["is_threat"])
    # Normal traffic should rarely be flagged
    assert threat_count <= 15  # allow for heuristic noise


def test_c2_port_classification(detector):
    """C2 ports should result in critical/high severity when flagged."""
    event = make_event(destination_port=4444, bytes_sent=5_000_000)
    results = [detector.predict(event) for _ in range(20)]
    threats = [r for r in results if r["is_threat"]]
    if threats:
        assert all(r["severity"] in ("critical", "high") for r in threats)


def test_telnet_protocol_flagged(detector):
    """Telnet protocol should raise threat score."""
    event = make_event(protocol="telnet", destination_port=23)
    results = [detector.predict(event) for _ in range(20)]
    avg = sum(r["confidence"] for r in results) / len(results)
    assert avg > 0.3


class ProbabilityModel:
    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, _features):
        return [[1 - self.probability, self.probability]]


@pytest.mark.parametrize(
    ("confidence", "severity", "is_threat"),
    [(0.90, "critical", True), (0.75, "high", True), (0.55, "medium", True), (0.20, "low", False)],
)
def test_pickle_model_prediction_thresholds(tmp_path, confidence, severity, is_threat):
    model_path = tmp_path / f"model-{confidence}.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(ProbabilityModel(confidence), handle)
    model_detector = ThreatDetector(str(model_path))
    result = model_detector.predict(make_event(destination_port=0, packets=0))
    assert result["confidence"] == confidence
    assert result["severity"] == severity
    assert result["is_threat"] is is_threat


def test_onnx_like_model_prediction_branch():
    class OnnxModel:
        def run(self, _outputs, inputs):
            assert "input" in inputs
            return [[[0.1, 0.9]]]

    model_detector = ThreatDetector()
    model_detector.model = OnnxModel()
    model_detector.use_heuristics = False
    result = model_detector.predict(make_event(protocol="ssh"))
    assert result["confidence"] == 0.9
    assert result["severity"] == "critical"


def test_unsupported_model_format_raises(tmp_path):
    path = tmp_path / "model.txt"
    path.write_text("not a model")
    with pytest.raises(ValueError, match="Unsupported model format"):
        ThreatDetector()._load_model(str(path))


def test_model_load_failure_falls_back_to_heuristics(tmp_path, monkeypatch):
    path = tmp_path / "broken.pkl"
    path.write_bytes(b"broken")
    detector = ThreatDetector(str(path))
    assert detector.use_heuristics is True
