"""
OmniTrust Forensic Brain Test Script
Tests the Forensic Brain (Sprint 4) integration.

This script tests:
1. Data aggregation from all three security layers
2. Forensic reasoning and correlation detection
3. Decision matrix classification
4. Veritas Certificate generation
5. High-quality deepfake detection scenario
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.forensics.reporter import (
    gather_sensor_data,
    ForensicInvestigator,
    generate_veritas_report,
    generate_forensic_report,
    VeritasStatus
)


def test_data_aggregation():
    """Test 1: Verify data aggregation from all three layers."""
    print("\n" + "=" * 60)
    print("Test 1: Data Aggregation")
    print("=" * 60)
    
    # Mock data from each layer
    ledger_data = {
        "verified": True,
        "transaction_id": "txn_12345",
        "status": "integrity_confirmed",
        "blob_name": "test_video.mp4"
    }
    
    sync_data = {
        "overall_risk_level": "low",
        "overall_risk_score": 0.2,
        "mismatch_count": 0,
        "max_delta_ms": 15.0,
        "network_jitter_ms": 10.0,
        "dynamic_threshold_ms": 45.0,
        "total_matches": 10
    }
    
    liveness_data = {
        "status": "human",
        "confidence": 0.95,
        "spike_ratio": 0.9,
        "smoothing_ratio": 0.1,
        "specularity_score": 0.08
    }
    
    metadata = {
        "investigation_id": "INV-001",
        "media_id": "test_video.mp4",
        "session_type": "live"
    }
    
    payload = gather_sensor_data(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata=metadata
    )
    
    print(f"\nInvestigation Payload Structure:")
    print(f"  Investigation ID: {payload.get('investigation_id')}")
    print(f"  Timestamp: {payload.get('timestamp')}")
    print(f"  Sensor Data Keys: {list(payload.get('sensor_data', {}).keys())}")
    
    # Verify structure
    assert "sensor_data" in payload, "Payload should contain sensor_data"
    assert "ledger" in payload["sensor_data"], "Should contain ledger data"
    assert "sync_engine" in payload["sensor_data"], "Should contain sync_engine data"
    assert "liveness" in payload["sensor_data"], "Should contain liveness data"
    
    print("\n[PASS] Data aggregation correctly formats investigation payload")
    return True


def test_verified_scenario():
    """Test 2: All layers pass - should return VERIFIED."""
    print("\n" + "=" * 60)
    print("Test 2: Verified Scenario (All Layers Pass)")
    print("=" * 60)
    
    ledger_data = {"verified": True, "status": "integrity_confirmed"}
    sync_data = {"overall_risk_level": "low", "overall_risk_score": 0.1, "mismatch_count": 0, "max_delta_ms": 10.0, "network_jitter_ms": 5.0}
    liveness_data = {"status": "human", "confidence": 0.9, "spike_ratio": 0.8, "smoothing_ratio": 0.1}
    
    certificate = generate_forensic_report(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata={"investigation_id": "TEST-VERIFIED"}
    )
    
    verdict = certificate["veritas_certificate"]["verdict"]
    confidence = certificate["veritas_certificate"]["confidence_score"]
    
    print(f"\nVeritas Certificate:")
    print(f"  Verdict: {verdict}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Narrative: {certificate['veritas_certificate']['narrative_summary'][:200]}...")
    
    assert verdict == VeritasStatus.VERIFIED.value.upper(), f"Should be VERIFIED, got {verdict}"
    assert confidence > 0.8, f"Confidence should be high, got {confidence:.2f}"
    
    print("\n[PASS] Verified scenario correctly identified")
    return True


def test_high_quality_deepfake_scenario():
    """Test 3: High-quality deepfake - sync passes but liveness fails."""
    print("\n" + "=" * 60)
    print("Test 3: High-Quality Deepfake Detection")
    print("=" * 60)
    print("Scenario: Sync looks okay, but Light-Bounce physics failed")
    
    # High-quality deepfake: sync is good (passes), but liveness fails
    ledger_data = {"verified": True, "status": "integrity_confirmed"}  # Hash matches
    sync_data = {
        "overall_risk_level": "low",  # Sync passes
        "overall_risk_score": 0.15,   # Low risk
        "mismatch_count": 0,
        "max_delta_ms": 25.0,         # Within threshold
        "network_jitter_ms": 10.0,
        "dynamic_threshold_ms": 45.0
    }
    liveness_data = {
        "status": "spoof",            # Liveness FAILED - key indicator!
        "confidence": 0.85,
        "spike_ratio": 0.2,           # Low spikes (smoothed response)
        "smoothing_ratio": 0.8,       # High smoothing (camera/deepfake)
        "specularity_score": 0.02,    # Low specularity (uniform reflection)
        "immediate_spikes": 2,
        "smoothed_transitions": 8
    }
    
    certificate = generate_forensic_report(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata={"investigation_id": "TEST-DEEPFAKE"}
    )
    
    verdict = certificate["veritas_certificate"]["verdict"]
    confidence = certificate["veritas_certificate"]["confidence_score"]
    correlations = certificate["veritas_certificate"]["correlations"]
    
    print(f"\nVeritas Certificate:")
    print(f"  Verdict: {verdict}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"\n  Key Findings:")
    print(f"    - Ledger: Verified (hash matches)")
    print(f"    - Sync Engine: Low risk (passes)")
    print(f"    - Liveness: SPOOF (Light-Bounce physics failed)")
    
    print(f"\n  Correlations Detected: {len(correlations)}")
    for corr in correlations:
        print(f"    - {corr.get('type')}: {corr.get('description')}")
    
    print(f"\n  Narrative Summary:")
    print(certificate["veritas_certificate"]["narrative_summary"])
    
    # Assertions: Should detect as SUSPICIOUS or MANIPULATED
    assert verdict in [VeritasStatus.SUSPICIOUS.value.upper(), VeritasStatus.MANIPULATED.value.upper()], \
        f"High-quality deepfake should be detected as SUSPICIOUS/MANIPULATED, got {verdict}"
    
    # Should detect the sophisticated spoof correlation
    has_sophisticated_spoof = any(
        corr.get("type") == "sophisticated_spoof" 
        for corr in correlations
    )
    assert has_sophisticated_spoof, \
        "Should detect 'sophisticated_spoof' correlation (liveness failed but sync passed)"
    
    print("\n[PASS] High-quality deepfake correctly detected (Liveness failed, Sync passed)")
    return True


def test_inconclusive_scenario():
    """Test 4: Technical noise - should return INCONCLUSIVE."""
    print("\n" + "=" * 60)
    print("Test 4: Inconclusive Scenario (Technical Noise)")
    print("=" * 60)
    
    ledger_data = {"verified": True, "status": "integrity_confirmed"}
    sync_data = {
        "overall_risk_level": "medium",
        "overall_risk_score": 0.4,
        "mismatch_count": 2,
        "max_delta_ms": 60.0,
        "network_jitter_ms": 80.0,  # High jitter (technical noise)
        "dynamic_threshold_ms": 150.0
    }
    liveness_data = {
        "status": "human",
        "confidence": 0.6,
        "smoothing_ratio": 0.4  # Some smoothing (camera HDR)
    }
    
    certificate = generate_forensic_report(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata={"investigation_id": "TEST-INCONCLUSIVE"}
    )
    
    verdict = certificate["veritas_certificate"]["verdict"]
    confidence = certificate["veritas_certificate"]["confidence_score"]
    
    print(f"\nVeritas Certificate:")
    print(f"  Verdict: {verdict}")
    print(f"  Confidence: {confidence:.2%}")
    
    assert verdict == VeritasStatus.INCONCLUSIVE.value.upper(), \
        f"Technical noise scenario should be INCONCLUSIVE, got {verdict}"
    
    print("\n[PASS] Inconclusive scenario correctly identified (technical noise)")
    return True


def test_manipulated_scenario():
    """Test 5: Multiple failures - should return MANIPULATED."""
    print("\n" + "=" * 60)
    print("Test 5: Manipulated Scenario (Multiple Failures)")
    print("=" * 60)
    
    ledger_data = {"verified": False, "status": "hash_mismatch"}  # Ledger mismatch!
    sync_data = {
        "overall_risk_level": "high",
        "overall_risk_score": 0.8,
        "mismatch_count": 8,
        "max_delta_ms": 150.0,
        "network_jitter_ms": 5.0
    }
    liveness_data = {
        "status": "spoof",
        "confidence": 0.9,
        "smoothing_ratio": 0.9
    }
    
    certificate = generate_forensic_report(
        ledger_data=ledger_data,
        sync_data=sync_data,
        liveness_data=liveness_data,
        metadata={"investigation_id": "TEST-MANIPULATED"}
    )
    
    verdict = certificate["veritas_certificate"]["verdict"]
    confidence = certificate["veritas_certificate"]["confidence_score"]
    correlations = certificate["veritas_certificate"]["correlations"]
    
    print(f"\nVeritas Certificate:")
    print(f"  Verdict: {verdict}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Correlations: {len(correlations)}")
    
    assert verdict == VeritasStatus.MANIPULATED.value.upper(), \
        f"Multiple failures should be MANIPULATED, got {verdict}"
    assert confidence > 0.8, f"Confidence should be high for manipulation, got {confidence:.2f}"
    
    # Should detect multi-layer failure correlation
    has_multi_layer = any(
        corr.get("type") == "multi_layer_failure"
        for corr in correlations
    )
    assert has_multi_layer, "Should detect multi_layer_failure correlation"
    
    print("\n[PASS] Manipulated scenario correctly identified (multiple failures)")
    return True


def test_veritas_certificate_structure():
    """Test 6: Verify Veritas Certificate structure."""
    print("\n" + "=" * 60)
    print("Test 6: Veritas Certificate Structure")
    print("=" * 60)
    
    certificate = generate_forensic_report(
        ledger_data={"verified": True},
        sync_data={"overall_risk_level": "low", "overall_risk_score": 0.1, "mismatch_count": 0, "max_delta_ms": 10.0, "network_jitter_ms": 5.0},
        liveness_data={"status": "human", "confidence": 0.9},
        metadata={"investigation_id": "TEST-STRUCTURE"}
    )
    
    cert = certificate["veritas_certificate"]
    
    # Verify required fields
    required_fields = [
        "certificate_id",
        "timestamp",
        "verdict",
        "confidence_score",
        "narrative_summary",
        "correlations",
        "evidence_trail"
    ]
    
    print(f"\nCertificate Fields:")
    for field in required_fields:
        assert field in cert, f"Certificate should contain '{field}'"
        print(f"  [OK] {field}")
    
    # Verify evidence trail structure
    evidence = cert["evidence_trail"]
    assert "ledger" in evidence, "Evidence trail should contain ledger"
    assert "sync_engine" in evidence, "Evidence trail should contain sync_engine"
    assert "liveness" in evidence, "Evidence trail should contain liveness"
    
    print(f"\n  Confidence Score: {cert['confidence_score']:.2%}")
    print(f"  Narrative Length: {len(cert['narrative_summary'])} characters")
    
    print("\n[PASS] Veritas Certificate structure is correct")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("OmniTrust Forensic Brain Test Suite")
    print("Sprint 4: The Forensic Brain")
    print("=" * 60)
    
    tests = [
        ("Data Aggregation", test_data_aggregation),
        ("Verified Scenario", test_verified_scenario),
        ("High-Quality Deepfake", test_high_quality_deepfake_scenario),
        ("Inconclusive Scenario", test_inconclusive_scenario),
        ("Manipulated Scenario", test_manipulated_scenario),
        ("Certificate Structure", test_veritas_certificate_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, True, None))
        except AssertionError as e:
            print(f"\n[FAIL] {test_name}: {e}")
            results.append((test_name, False, str(e)))
        except Exception as e:
            print(f"\n[ERROR] {test_name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {test_name}")
        if error:
            print(f"    Error: {error}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        print("Forensic Brain is functioning correctly.")
        print("The system can detect high-quality deepfakes even when sync passes.")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

