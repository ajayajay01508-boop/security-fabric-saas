"""
ThreatDetector: wraps quantized ML model (or heuristic fallback).
In production, load an ONNX / PyTorch quantized model from models/.
For local dev, a rule-based heuristic engine is used automatically.
"""
import os
import random
import logging
from typing import Optional

logger = logging.getLogger("threat-detector")

THREAT_CLASSIFICATIONS = [
    "Port Scan",
    "DDoS",
    "SQL Injection",
    "Brute Force SSH",
    "Data Exfiltration",
    "Command & Control",
    "DNS Tunneling",
    "Lateral Movement",
    "Ransomware Communication",
    "Zero-Day Exploit Attempt",
]

SEVERITY_MAP = {
    "Port Scan": "low",
    "DDoS": "high",
    "SQL Injection": "high",
    "Brute Force SSH": "medium",
    "Data Exfiltration": "critical",
    "Command & Control": "critical",
    "DNS Tunneling": "medium",
    "Lateral Movement": "high",
    "Ransomware Communication": "critical",
    "Zero-Day Exploit Attempt": "critical",
}

SUSPICIOUS_PORTS = {22, 23, 3389, 445, 1433, 3306, 5432, 6379, 27017, 9200}
SUSPICIOUS_PROTOCOLS = {"telnet", "ftp"}


class ThreatDetector:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.use_heuristics = True

        if model_path and os.path.exists(model_path):
            try:
                self._load_model(model_path)
                self.use_heuristics = False
                logger.info(f"Loaded model from {model_path}")
            except Exception as e:
                logger.warning(f"Could not load model ({e}), using heuristics")
        else:
            logger.info("No model file found — using heuristic detection engine")

    def _load_model(self, path: str):
        """Load ONNX or pickle model."""
        import pickle
        if path.endswith(".pkl"):
            with open(path, "rb") as f:
                self.model = pickle.load(f)
        elif path.endswith(".onnx"):
            import onnxruntime as ort
            self.model = ort.InferenceSession(path)
        else:
            raise ValueError(f"Unsupported model format: {path}")

    def _heuristic_predict(self, event: dict) -> dict:
        """Rule-based threat detection for development."""
        score = 0.0
        reasons = []

        dst_port = event.get("destination_port", 0)
        src_port = event.get("source_port", 0)
        protocol = (event.get("protocol") or "").lower()
        bytes_sent = event.get("bytes_sent", 0)
        packets = event.get("packets", 0)

        if dst_port in SUSPICIOUS_PORTS:
            score += 0.3
            reasons.append(f"suspicious destination port {dst_port}")

        if protocol in SUSPICIOUS_PROTOCOLS:
            score += 0.4
            reasons.append(f"insecure protocol {protocol}")

        if packets > 10000:
            score += 0.35
            reasons.append("high packet rate (potential DDoS)")

        if bytes_sent > 50_000_000:
            score += 0.45
            reasons.append("large data transfer (potential exfiltration)")

        if dst_port == 4444 or dst_port == 1337:
            score += 0.6
            reasons.append("known C2 port")

        # Add some probabilistic noise for realistic simulation
        score += random.uniform(-0.1, 0.15)
        score = max(0.0, min(1.0, score))

        is_threat = score > 0.35

        classification = None
        severity = "info"
        if is_threat:
            if score > 0.75:
                classification = random.choice(["Data Exfiltration", "Command & Control", "Ransomware Communication"])
                severity = "critical"
            elif score > 0.55:
                classification = random.choice(["DDoS", "SQL Injection", "Lateral Movement"])
                severity = "high"
            elif score > 0.40:
                classification = random.choice(["Brute Force SSH", "DNS Tunneling"])
                severity = "medium"
            else:
                classification = "Port Scan"
                severity = "low"

        description = (
            f"Heuristic detection: {', '.join(reasons)}" if reasons
            else "Anomalous traffic pattern detected"
        )

        return {
            "is_threat": is_threat,
            "confidence": round(score, 3),
            "severity": severity,
            "classification": classification or "Unknown",
            "description": description,
        }

    def _model_predict(self, event: dict) -> dict:
        """Run inference through loaded ML model (10-feature vector matching train_model.py)."""
        bytes_sent  = event.get("bytes_sent", 0)
        bytes_recv  = event.get("bytes_received", 0)
        packets     = max(event.get("packets", 1), 1)
        duration    = event.get("duration_ms", 0)
        src_port    = event.get("source_port", 0)
        dst_port    = event.get("destination_port", 0)
        protocol    = (event.get("protocol") or "").lower()

        _SUSP = {22, 23, 3389, 445, 1433, 3306, 5432, 6379, 27017, 9200, 4444, 1337}
        is_susp     = 1 if dst_port in _SUSP else 0
        protocol_id = 1 if protocol in ("telnet", "ftp", "ssh") else 0
        bpp         = bytes_sent / packets
        port_ratio  = src_port / max(dst_port, 1)

        features = [
            bytes_sent, bytes_recv, packets, duration,
            src_port, dst_port, is_susp, protocol_id,
            bpp, port_ratio,
        ]
        # ONNX inference
        if hasattr(self.model, "run"):
            import numpy as np
            inp = np.array([features], dtype=np.float32)
            output = self.model.run(None, {"input": inp})[0]
            confidence = float(output[0][1])
        else:
            confidence = float(self.model.predict_proba([features])[0][1])

        is_threat = confidence > 0.5
        severity = "critical" if confidence > 0.85 else "high" if confidence > 0.65 else "medium" if confidence > 0.50 else "low"
        classification = THREAT_CLASSIFICATIONS[int(confidence * 10) % len(THREAT_CLASSIFICATIONS)]

        return {
            "is_threat": is_threat,
            "confidence": round(confidence, 3),
            "severity": severity,
            "classification": classification,
            "description": f"ML model detected {classification} with {confidence:.1%} confidence",
        }

    def predict(self, event: dict) -> dict:
        if self.use_heuristics:
            return self._heuristic_predict(event)
        return self._model_predict(event)
