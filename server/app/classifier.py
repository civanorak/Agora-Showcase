"""
Classifier v1 — YAML signature engine.
Signatures are loaded once at startup and hot-reloadable (P2).
Every result is {verdict, confidence, evidence[]} — never a bare label (P3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from .config import settings

logger = logging.getLogger(__name__)

Verdict = Literal[
    "assistant_browse",
    "crawler_search",
    "crawler_training",
    "shopping_agent",
    "automation_other",
    "human",
    "unknown",
]

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"


@dataclass(frozen=True)
class Signature:
    id: str
    ua_contains: list[str]
    verdict: Verdict
    confidence: float
    notes: str = ""


@dataclass(frozen=True)
class ClassificationResult:
    verdict: Verdict
    confidence: float
    evidence: list[str]
    signature_id: str | None = None


_signatures: list[Signature] = []
_version: str = "unloaded"


def load_signatures(directory: Path = SIGNATURES_DIR) -> int:
    global _signatures, _version
    loaded: list[Signature] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            # Skip demo-only signature files unless AGORA_DEMO_MODE=1 (M1).
            if doc.get("_demo_only") and not settings.demo_mode:
                logger.debug(
                    "Skipping demo-only signature file %s (AGORA_DEMO_MODE not set)", path.name
                )
                continue
            for sig in doc.get("signatures", []):
                loaded.append(
                    Signature(
                        id=sig["id"],
                        ua_contains=[s.lower() for s in sig.get("ua_contains", [])],
                        verdict=sig["verdict"],
                        confidence=float(sig.get("confidence", 0.8)),
                        notes=sig.get("notes", ""),
                    )
                )
        except Exception:
            logger.exception("Failed to load signature file %s", path)
    _signatures = loaded
    _version = "v1"
    logger.info("Loaded %d signatures from %s", len(loaded), directory)
    return len(loaded)


def _is_human_ua(ua: str) -> bool:
    ua_lower = ua.lower()
    human_tokens = ["mozilla/", "chrome/", "safari/", "firefox/", "edge/"]
    return any(t in ua_lower for t in human_tokens)


def classify(ua: str, path: str = "/", headers: dict | None = None) -> ClassificationResult:
    """Classify a single request. Returns verdict + evidence list."""
    if not _signatures:
        load_signatures()

    ua_lower = ua.lower()
    evidence: list[str] = []

    # --- Signature match ---
    for sig in _signatures:
        for token in sig.ua_contains:
            if token in ua_lower:
                evidence.append(f"ua_match:{sig.id}:{token}")
                return ClassificationResult(
                    verdict=sig.verdict,
                    confidence=sig.confidence,
                    evidence=evidence,
                    signature_id=sig.id,
                )

    # --- Behavioral fallback ---
    if ua == "" or ua == "-":
        evidence.append("ua_empty")
        return ClassificationResult(verdict="unknown", confidence=0.6, evidence=evidence)

    if _is_human_ua(ua):
        evidence.append("ua_human_token")

        # no_beacon evidence is deferred to Phase 2 together with the real JS beacon.
        # Emitting it here fired on 100% of human traffic (beacon never injected by
        # collector), carrying zero information and confusing merchants in demos. (M2)

        # robots.txt or sitemap hits from "human" UA = suspicious
        if path in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
            evidence.append(f"probe_path:{path}")
            return ClassificationResult(
                verdict="automation_other", confidence=0.65, evidence=evidence
            )

        return ClassificationResult(verdict="human", confidence=0.80, evidence=evidence)

    # Non-Mozilla, no signature match → unknown automation
    evidence.append("ua_unknown_non_human")
    return ClassificationResult(verdict="automation_other", confidence=0.55, evidence=evidence)
