"""
OmniTrust Forensic Reporter (Sprint 4)
The Forensic Brain - GPT-4o integration for human-readable forensic reports.

Acts as a Senior Digital Forensic Investigator to analyze correlations
between three security layers (Ledger, Sync Engine, Physics Guard) and
generate Veritas Certificates with explainable AI reasoning.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum


class VeritasStatus(Enum):
    """Veritas Certificate status categories."""
    VERIFIED = "verified"
    INCONCLUSIVE = "inconclusive"
    SUSPICIOUS = "suspicious"
    MANIPULATED = "manipulated"


def gather_sensor_data(
    ledger_data: Optional[Dict[str, Any]] = None,
    sync_data: Optional[Dict[str, Any]] = None,
    liveness_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Gather sensor data from all three security layers into Investigation Payload.
    
    Step 1: Data Aggregator - Collects outputs from:
    - Sprint 1 (Ledger): Hash verification results
    - Sprint 2 (Sync Engine): Phoneme-viseme synchronization analysis
    - Sprint 3 (Physics Guard): Light-Bounce liveness detection
    
    Args:
        ledger_data: Ledger verification data (from LedgerMonitorService.verify_hash or similar)
        sync_data: Sync analysis data (from SyncEngine.analyze_sync)
        liveness_data: Liveness verification data (from LivenessVerifier.verify_liveness)
        metadata: Additional metadata (media ID, timestamp, etc.)
    
    Returns:
        Investigation Payload JSON object with all sensor data.
    """
    payload = {
        "investigation_id": metadata.get("investigation_id") if metadata else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "sensor_data": {
            "ledger": ledger_data or {},
            "sync_engine": sync_data or {},
            "liveness": liveness_data or {}
        }
    }
    
    return payload


class ForensicInvestigator:
    """
    Senior Digital Forensic Investigator - Analyzes correlations between security layers.
    
    Step 2: Forensic Reasoning (The 'Brain')
    Uses detailed system prompt logic (simulated GPT-4o) to analyze sensor data
    and detect correlations that indicate fraud or manipulation.
    """
    
    SYSTEM_PROMPT = """You are a Senior Digital Forensic Investigator analyzing multi-layer security sensor data.

Your task is to identify correlations and anomalies across three security layers:
1. Ledger (Hash Verification): Detects tampering via immutable hash comparisons
2. Sync Engine (Phoneme-Viseme): Detects audio-video synchronization issues
3. Liveness (Light-Bounce Physics): Detects camera auto-correction and deepfake masks

CRITICAL CORRELATION RULES:
- If Sync fails BUT Network Jitter is high (>50ms), LOWER the risk score (technical noise)
- If Liveness fails AND Ledger is mismatched, ESCALATE to Critical Fraud (multi-layer failure)
- If Liveness fails BUT Sync passes, mark as SUSPICIOUS (possible high-quality deepfake)
- If all layers pass, mark as VERIFIED
- If technical noise detected (jitter/HDR smoothing) but no clear manipulation, mark as INCONCLUSIVE

Analyze the evidence trail and provide:
1. Overall verdict (VERIFIED/INCONCLUSIVE/SUSPICIOUS/MANIPULATED)
2. Confidence score (0.0-1.0)
3. Narrative explanation of findings
4. Key correlations detected
"""
    
    def __init__(self, use_gpt4_simulation: bool = True):
        """
        Initialize Forensic Investigator.
        
        Args:
            use_gpt4_simulation: If True, uses simulated GPT-4o logic (for testing).
                                If False, would call actual Azure OpenAI GPT-4o.
        """
        self.use_gpt4_simulation = use_gpt4_simulation
    
    def analyze_investigation_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze investigation payload and determine verdict.
        
        Args:
            payload: Investigation payload from gather_sensor_data()
        
        Returns:
            Dictionary with analysis results including verdict, confidence, and reasoning.
        """
        sensor_data = payload.get("sensor_data", {})
        ledger = sensor_data.get("ledger", {})
        sync = sensor_data.get("sync_engine", {})
        liveness = sensor_data.get("liveness", {})
        
        # Extract key metrics
        ledger_verified = ledger.get("verified", False)
        ledger_status = ledger.get("status", "unknown")
        
        sync_risk_level = sync.get("overall_risk_level", "unknown")
        sync_risk_score = sync.get("overall_risk_score", 0.0)
        sync_mismatch_count = sync.get("mismatch_count", 0)
        sync_max_delta = sync.get("max_delta_ms", 0.0)
        network_jitter = sync.get("network_jitter_ms", 0.0)
        dynamic_threshold = sync.get("dynamic_threshold_ms", 30.0)
        
        liveness_status = liveness.get("status", "unknown")
        liveness_confidence = liveness.get("confidence", 0.0)
        liveness_spike_ratio = liveness.get("spike_ratio", 0.0)
        liveness_smoothing_ratio = liveness.get("smoothing_ratio", 0.0)
        liveness_specularity = liveness.get("specularity_score", 0.0)
        
        # Step 3: Decision Matrix Analysis
        verdict, confidence, reasoning = self._apply_decision_matrix(
            ledger_verified=ledger_verified,
            ledger_status=ledger_status,
            sync_risk_level=sync_risk_level,
            sync_risk_score=sync_risk_score,
            sync_mismatch_count=sync_mismatch_count,
            sync_max_delta=sync_max_delta,
            network_jitter=network_jitter,
            liveness_status=liveness_status,
            liveness_confidence=liveness_confidence,
            liveness_spike_ratio=liveness_spike_ratio,
            liveness_smoothing_ratio=liveness_smoothing_ratio,
            liveness_specularity=liveness_specularity
        )
        
        # Identify key correlations
        correlations = self._identify_correlations(
            ledger_verified=ledger_verified,
            sync_risk_score=sync_risk_score,
            sync_max_delta=sync_max_delta,
            network_jitter=network_jitter,
            liveness_status=liveness_status,
            liveness_confidence=liveness_confidence
        )
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": reasoning,
            "correlations": correlations,
            "raw_analysis": {
                "ledger_status": ledger_status,
                "sync_risk_level": sync_risk_level,
                "liveness_status": liveness_status,
                "network_jitter_ms": network_jitter,
                "sync_max_delta_ms": sync_max_delta
            }
        }
    
    def _apply_decision_matrix(
        self,
        ledger_verified: bool,
        ledger_status: str,
        sync_risk_level: Any,
        sync_risk_score: float,
        sync_mismatch_count: int,
        sync_max_delta: float,
        network_jitter: float,
        liveness_status: Any,
        liveness_confidence: float,
        liveness_spike_ratio: float,
        liveness_smoothing_ratio: float,
        liveness_specularity: float
    ) -> tuple:
        """
        Apply decision matrix to determine verdict.
        
        Returns:
            Tuple of (verdict, confidence, reasoning)
        """
        # Normalize status values (handle Enum or string)
        sync_risk_str = str(sync_risk_level).lower() if sync_risk_level else "unknown"
        if hasattr(sync_risk_level, 'value'):
            sync_risk_str = sync_risk_level.value.lower()
        
        liveness_status_str = str(liveness_status).lower() if liveness_status else "unknown"
        if hasattr(liveness_status, 'value'):
            liveness_status_str = liveness_status.value.lower()
        
        # Decision Matrix Logic
        
        # MANIPULATED: Multiple layers failed or Ledger mismatch
        if not ledger_verified and ledger_status != "hash_not_found":
            # Ledger mismatch is critical
            return (
                VeritasStatus.MANIPULATED,
                0.95,
                "CRITICAL: Ledger hash mismatch detected. This indicates tampering with the original media file. "
                "The immutable ledger entry does not match the current file hash."
            )
        
        failures = 0
        failure_details = []
        
        # Check Sync Engine failure
        sync_failed = (
            sync_risk_str in ["high", "critical"] or
            sync_max_delta > 200.0 or
            (sync_mismatch_count > 0 and sync_max_delta > 100.0)
        )
        
        # Adjust for network jitter (correlation rule: high jitter lowers risk)
        if sync_failed and network_jitter > 50.0:
            # High jitter mitigates sync failure
            sync_failed = False
            failure_details.append(f"Sync issues mitigated by high network jitter ({network_jitter:.1f}ms)")
        elif sync_failed:
            failures += 1
            failure_details.append(f"Sync Engine detected {sync_mismatch_count} mismatch(es) with max delta {sync_max_delta:.1f}ms")
        
        # Check Liveness failure
        liveness_failed = liveness_status_str == "spoof"
        if liveness_failed:
            failures += 1
            failure_details.append(f"Liveness detection failed: {liveness_status_str} (confidence: {liveness_confidence:.2f})")
        
        # Multiple failures = MANIPULATED
        if failures >= 2:
            return (
                VeritasStatus.MANIPULATED,
                0.85 + (failures * 0.05),
                f"MANIPULATED: Multiple security layers failed. {len(failure_details)} failure(s): " +
                "; ".join(failure_details)
            )
        
        # Single significant failure = SUSPICIOUS
        if failures == 1:
            if sync_max_delta > 200.0:
                return (
                    VeritasStatus.SUSPICIOUS,
                    0.75,
                    f"SUSPICIOUS: Significant sync gap detected ({sync_max_delta:.1f}ms). "
                    f"This exceeds normal thresholds and indicates possible manipulation."
                )
            elif liveness_failed:
                return (
                    VeritasStatus.SUSPICIOUS,
                    0.70,
                    f"SUSPICIOUS: Liveness detection failed (Light-Bounce physics test). "
                    f"Possible deepfake or camera auto-correction detected."
                )
            else:
                return (
                    VeritasStatus.SUSPICIOUS,
                    0.65,
                    f"SUSPICIOUS: Security layer failure detected. {failure_details[0]}"
                )
        
        # Technical noise detected = INCONCLUSIVE
        technical_noise = (
            network_jitter > 30.0 or
            (sync_risk_score > 0.3 and sync_risk_score < 0.5) or
            (liveness_smoothing_ratio > 0.3 and liveness_smoothing_ratio < 0.6)
        )
        
        if technical_noise and failures == 0:
            noise_reasons = []
            if network_jitter > 30.0:
                noise_reasons.append(f"high network jitter ({network_jitter:.1f}ms)")
            if liveness_smoothing_ratio > 0.3:
                noise_reasons.append(f"camera smoothing detected (ratio: {liveness_smoothing_ratio:.2f})")
            
            return (
                VeritasStatus.INCONCLUSIVE,
                0.60,
                f"INCONCLUSIVE: Technical noise detected ({', '.join(noise_reasons)}), "
                f"but no clear evidence of manipulation. Results may be affected by network conditions or camera processing."
            )
        
        # All layers pass = VERIFIED
        if ledger_verified and sync_risk_str in ["low", "medium"] and liveness_status_str == "human":
            return (
                VeritasStatus.VERIFIED,
                0.95,
                "VERIFIED: All security layers passed. Ledger hash verified, sync analysis normal, "
                "and liveness detection confirmed human response to Light-Bounce challenge."
            )
        elif sync_risk_str in ["low"] and liveness_status_str == "human":
            # Even without ledger (e.g., new file), if sync and liveness pass
            return (
                VeritasStatus.VERIFIED,
                0.85,
                "VERIFIED: Sync and Liveness layers passed. No evidence of manipulation detected."
            )
        else:
            # Default: UNCERTAIN
            return (
                VeritasStatus.INCONCLUSIVE,
                0.50,
                "INCONCLUSIVE: Mixed signals detected. Unable to definitively verify or reject the media."
            )
    
    def _identify_correlations(
        self,
        ledger_verified: bool,
        sync_risk_score: float,
        sync_max_delta: float,
        network_jitter: float,
        liveness_status: Any,
        liveness_confidence: float
    ) -> List[Dict[str, Any]]:
        """
        Identify key correlations between security layers.
        
        Returns:
            List of correlation dictionaries.
        """
        correlations = []
        
        liveness_status_str = str(liveness_status).lower() if liveness_status else "unknown"
        if hasattr(liveness_status, 'value'):
            liveness_status_str = liveness_status.value.lower()
        
        # Correlation: Sync failure + High Jitter = Technical Noise
        if sync_max_delta > 50.0 and network_jitter > 50.0:
            correlations.append({
                "type": "jitter_mitigation",
                "description": "Sync issues mitigated by high network jitter",
                "impact": "lowers_risk",
                "details": {
                    "sync_delta_ms": sync_max_delta,
                    "network_jitter_ms": network_jitter
                }
            })
        
        # Correlation: Liveness failure + Ledger mismatch = Critical Fraud
        if not ledger_verified and liveness_status_str == "spoof":
            correlations.append({
                "type": "multi_layer_failure",
                "description": "Liveness failure combined with ledger mismatch",
                "impact": "escalates_to_critical",
                "severity": "critical"
            })
        
        # Correlation: Liveness failure + Sync pass = High-Quality Deepfake
        if liveness_status_str == "spoof" and sync_risk_score < 0.4:
            correlations.append({
                "type": "sophisticated_spoof",
                "description": "Liveness failed but sync passed - possible high-quality deepfake",
                "impact": "suspicious",
                "details": {
                    "liveness_status": liveness_status_str,
                    "sync_risk_score": sync_risk_score
                }
            })
        
        return correlations


def generate_veritas_report(
    investigation_payload: Dict[str, Any],
    investigator: Optional[ForensicInvestigator] = None
) -> Dict[str, Any]:
    """
    Generate Veritas Certificate report.
    
    Step 4: The 'Veritas Certificate' Output
    Generates structured summary with:
    - Confidence Score (0.0 to 1.0)
    - Narrative Summary (human-readable explanation)
    - Evidence Trail (raw sensor data for audit)
    
    Args:
        investigation_payload: Investigation payload from gather_sensor_data()
        investigator: ForensicInvestigator instance (creates new one if None)
    
    Returns:
        Veritas Certificate dictionary with confidence, narrative, and evidence trail.
    """
    if investigator is None:
        investigator = ForensicInvestigator()
    
    # Analyze the payload
    analysis = investigator.analyze_investigation_payload(investigation_payload)
    
    # Extract verdict
    verdict = analysis["verdict"]
    if isinstance(verdict, VeritasStatus):
        verdict_str = verdict.value.upper()
    else:
        verdict_str = str(verdict).upper()
    
    # Generate narrative summary
    narrative = _generate_narrative_summary(analysis, investigation_payload)
    
    # Build Veritas Certificate
    certificate = {
        "veritas_certificate": {
            "certificate_id": investigation_payload.get("investigation_id") or f"VERITAS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "timestamp": investigation_payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "verdict": verdict_str,
            "confidence_score": analysis["confidence"],
            "narrative_summary": narrative,
            "correlations": analysis["correlations"],
            "evidence_trail": {
                "ledger": investigation_payload.get("sensor_data", {}).get("ledger", {}),
                "sync_engine": investigation_payload.get("sensor_data", {}).get("sync_engine", {}),
                "liveness": investigation_payload.get("sensor_data", {}).get("liveness", {}),
                "raw_analysis": analysis["raw_analysis"]
            }
        }
    }
    
    return certificate


def _generate_narrative_summary(
    analysis: Dict[str, Any],
    payload: Dict[str, Any]
) -> str:
    """
    Generate human-readable narrative summary.
    
    Args:
        analysis: Analysis results from ForensicInvestigator
        payload: Original investigation payload
    
    Returns:
        Narrative summary string.
    """
    verdict = analysis["verdict"]
    if isinstance(verdict, VeritasStatus):
        verdict_str = verdict.value.upper()
    else:
        verdict_str = str(verdict).upper()
    
    reasoning = analysis.get("reasoning", "Analysis completed.")
    correlations = analysis.get("correlations", [])
    
    narrative_parts = [
        f"FORENSIC ANALYSIS SUMMARY",
        f"Verdict: {verdict_str}",
        f"Confidence: {analysis['confidence']:.1%}",
        "",
        f"FINDINGS:",
        reasoning,
        ""
    ]
    
    if correlations:
        narrative_parts.append("KEY CORRELATIONS DETECTED:")
        for corr in correlations:
            narrative_parts.append(f"- {corr.get('description', 'Unknown correlation')}")
        narrative_parts.append("")
    
    narrative_parts.append("This analysis combines three security layers:")
    narrative_parts.append("1. Ledger Verification: Immutable hash comparison for tampering detection")
    narrative_parts.append("2. Sync Engine: Phoneme-viseme synchronization analysis")
    narrative_parts.append("3. Liveness Detection: Light-Bounce physics challenge")
    
    return "\n".join(narrative_parts)


# Convenience function for end-to-end workflow
def generate_forensic_report(
    ledger_data: Optional[Dict[str, Any]] = None,
    sync_data: Optional[Dict[str, Any]] = None,
    liveness_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate forensic report from individual sensor data.
    
    Args:
        ledger_data: Ledger verification data
        sync_data: Sync analysis data
        liveness_data: Liveness verification data
        metadata: Additional metadata
    
    Returns:
        Veritas Certificate dictionary.
    """
    payload = gather_sensor_data(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata=metadata
    )
    
    return generate_veritas_report(payload)

