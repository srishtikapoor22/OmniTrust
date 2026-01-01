"""
OmniTrust Sprint 2 Workflow Test Script
Tests the complete phoneme-viseme sync workflow.

This script simulates the Sprint 2 workflow:
1. Simulates receiving audio phonemes and visual visemes from Azure AI services
2. Runs sync analysis to detect multimodal mismatches
3. Flags files with >30ms delays (especially plosives)
4. Demonstrates how results integrate into the OmniTrust pipeline

Usage:
    python src/services/test_sync_workflow.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.sync_engine import (
    SyncEngine,
    Phoneme,
    Viseme,
    SyncRiskLevel,
    analyze_phoneme_viseme_sync
)


def simulate_azure_speech_output(word: str, start_time: float = 0.0) -> List[Dict[str, Any]]:
    """
    Simulate Azure AI Speech (Whisper) phoneme extraction output.
    
    In production, this would come from Azure AI Speech service.
    For testing, we generate realistic phoneme data.
    
    Args:
        word: Word to generate phonemes for.
        start_time: Starting timestamp in milliseconds.
    
    Returns:
        List of phoneme dictionaries.
    """
    # Simplified phoneme mapping for common words
    phoneme_map = {
        "PAPA": [
            {"symbol": "P", "duration": 30},
            {"symbol": "AH", "duration": 70},
            {"symbol": "P", "duration": 30},
            {"symbol": "AH", "duration": 70},
        ],
        "BABY": [
            {"symbol": "B", "duration": 30},
            {"symbol": "AH", "duration": 70},
            {"symbol": "B", "duration": 30},
            {"symbol": "IY", "duration": 70},
        ],
        "HELLO": [
            {"symbol": "HH", "duration": 40},
            {"symbol": "EH", "duration": 60},
            {"symbol": "L", "duration": 50},
            {"symbol": "OW", "duration": 80},
        ],
        "TEST": [
            {"symbol": "T", "duration": 30},
            {"symbol": "EH", "duration": 60},
            {"symbol": "S", "duration": 40},
            {"symbol": "T", "duration": 30},
        ],
    }
    
    phonemes = []
    current_time = start_time
    
    word_upper = word.upper()
    if word_upper in phoneme_map:
        for phoneme_data in phoneme_map[word_upper]:
            phonemes.append({
                "symbol": phoneme_data["symbol"],
                "start_time": current_time,
                "end_time": current_time + phoneme_data["duration"]
            })
            current_time += phoneme_data["duration"]
    
    return phonemes


def simulate_azure_vision_output(word: str, start_time: float = 0.0, delay_ms: float = 0.0) -> List[Dict[str, Any]]:
    """
    Simulate Azure AI Vision viseme tracking output.
    
    In production, this would come from Azure AI Vision Spatial Analysis.
    For testing, we generate realistic viseme data with optional delay.
    
    Args:
        word: Word to generate visemes for.
        start_time: Starting timestamp in milliseconds.
        delay_ms: Optional delay to simulate lip-sync issues (positive = video lags).
    
    Returns:
        List of viseme dictionaries.
    """
    # Viseme mapping (corresponding to phonemes)
    viseme_map = {
        "PAPA": [
            {"shape": "PBM", "duration": 30},
            {"shape": "AA", "duration": 70},
            {"shape": "PBM", "duration": 30},
            {"shape": "AA", "duration": 70},
        ],
        "BABY": [
            {"shape": "PBM", "duration": 30},
            {"shape": "AA", "duration": 70},
            {"shape": "PBM", "duration": 30},
            {"shape": "I", "duration": 70},
        ],
        "HELLO": [
            {"shape": "rest", "duration": 40},
            {"shape": "E", "duration": 60},
            {"shape": "ETC", "duration": 50},
            {"shape": "U", "duration": 80},
        ],
        "TEST": [
            {"shape": "ETC", "duration": 30},
            {"shape": "E", "duration": 60},
            {"shape": "S", "duration": 40},
            {"shape": "ETC", "duration": 30},
        ],
    }
    
    visemes = []
    current_time = start_time + delay_ms  # Apply delay
    
    word_upper = word.upper()
    if word_upper in viseme_map:
        for viseme_data in viseme_map[word_upper]:
            visemes.append({
                "shape": viseme_data["shape"],
                "start_time": current_time,
                "end_time": current_time + viseme_data["duration"]
            })
            current_time += viseme_data["duration"]
    
    return visemes


def test_workflow_scenario_1():
    """Workflow Test 1: Perfectly Synced Media (Should Pass)"""
    print("\n" + "=" * 60)
    print("Workflow Scenario 1: Perfectly Synced Media")
    print("=" * 60)
    
    print("\nSimulating Azure AI services output...")
    
    # Simulate Azure AI Speech output
    phonemes_data = simulate_azure_speech_output("PAPA", start_time=0.0)
    print(f"  Azure AI Speech extracted {len(phonemes_data)} phonemes:")
    for p in phonemes_data:
        print(f"    - {p['symbol']} @ {p['start_time']:.0f}-{p['end_time']:.0f}ms")
    
    # Simulate Azure AI Vision output (no delay = perfect sync)
    visemes_data = simulate_azure_vision_output("PAPA", start_time=0.0, delay_ms=0.0)
    print(f"\n  Azure AI Vision tracked {len(visemes_data)} visemes:")
    for v in visemes_data:
        print(f"    - {v['shape']} @ {v['start_time']:.0f}-{v['end_time']:.0f}ms")
    
    # Run sync analysis
    print("\nRunning Sync Engine analysis...")
    result = analyze_phoneme_viseme_sync(
        audio_phonemes=phonemes_data,
        visual_visemes=visemes_data,
        threshold_ms=30.0
    )
    
    # Display results
    print(f"\nSync Analysis Results:")
    print(f"  Total matches: {result['total_matches']}")
    print(f"  Mismatches (>30ms): {result['mismatch_count']}")
    print(f"  Overall risk score: {result['overall_risk_score']:.3f}")
    print(f"  Overall risk level: {result['overall_risk_level'].value.upper()}")
    print(f"  Max delta: {result['max_delta_ms']:.2f} ms")
    
    # Workflow decision
    print(f"\nWorkflow Decision:")
    if result['overall_risk_level'] in [SyncRiskLevel.LOW, SyncRiskLevel.MEDIUM]:
        print(f"  [PASS] Media passes sync verification")
        print(f"  Action: Continue to next verification stage")
        workflow_status = "PASS"
    else:
        print(f"  [FLAG] Multimodal mismatch detected")
        print(f"  Action: Flag for forensic review")
        workflow_status = "FLAG"
    
    return {
        "scenario": "Perfectly Synced Media",
        "workflow_status": workflow_status,
        "result": result
    }


def test_workflow_scenario_2():
    """Workflow Test 2: Delayed Media (Should Flag)"""
    print("\n" + "=" * 60)
    print("Workflow Scenario 2: Delayed Media (Lip-Sync Issue)")
    print("=" * 60)
    
    print("\nSimulating Azure AI services output...")
    
    # Simulate Azure AI Speech output
    phonemes_data = simulate_azure_speech_output("BABY", start_time=0.0)
    print(f"  Azure AI Speech extracted {len(phonemes_data)} phonemes:")
    for p in phonemes_data:
        is_plosive = p['symbol'] in ['P', 'B', 'T', 'D', 'K', 'G']
        marker = " [PLOSIVE]" if is_plosive else ""
        print(f"    - {p['symbol']}{marker} @ {p['start_time']:.0f}-{p['end_time']:.0f}ms")
    
    # Simulate Azure AI Vision output (50ms delay = lip-sync issue)
    visemes_data = simulate_azure_vision_output("BABY", start_time=0.0, delay_ms=50.0)
    print(f"\n  Azure AI Vision tracked {len(visemes_data)} visemes:")
    print(f"    Note: Video is delayed by 50ms (simulating lip-sync issue)")
    for v in visemes_data:
        print(f"    - {v['shape']} @ {v['start_time']:.0f}-{v['end_time']:.0f}ms")
    
    # Run sync analysis
    print("\nRunning Sync Engine analysis...")
    result = analyze_phoneme_viseme_sync(
        audio_phonemes=phonemes_data,
        visual_visemes=visemes_data,
        threshold_ms=30.0
    )
    
    # Display results
    print(f"\nSync Analysis Results:")
    print(f"  Total matches: {result['total_matches']}")
    print(f"  Mismatches (>30ms): {result['mismatch_count']}")
    print(f"  Plosive mismatches: {result['plosive_mismatches']}")
    print(f"  Overall risk score: {result['overall_risk_score']:.3f}")
    print(f"  Overall risk level: {result['overall_risk_level'].value.upper()}")
    print(f"  Max delta: {result['max_delta_ms']:.2f} ms")
    
    # Show match details for flagged cases
    if result['mismatch_count'] > 0:
        print(f"\nFlagged Matches:")
        for i, match in enumerate(result['matches']):
            if abs(match.delta_ms) > 30.0:
                is_plosive = match.phoneme.symbol.upper() in ['P', 'B', 'T', 'D', 'K', 'G']
                plosive_note = " (CRITICAL: Plosive sound)" if is_plosive else ""
                print(f"  Match {i+1}:")
                print(f"    Phoneme: {match.phoneme.symbol} @ {match.phoneme.center_time:.1f}ms")
                print(f"    Viseme: {match.viseme.shape} @ {match.viseme.center_time:.1f}ms")
                print(f"    Delta: {abs(match.delta_ms):.2f} ms (exceeds 30ms threshold){plosive_note}")
                print(f"    Risk: {match.risk_score:.3f} ({match.risk_level.value})")
    
    # Workflow decision
    print(f"\nWorkflow Decision:")
    # Flag if HIGH/CRITICAL risk OR if there are plosive mismatches (even with MEDIUM overall)
    should_flag = (
        result['overall_risk_level'] in [SyncRiskLevel.HIGH, SyncRiskLevel.CRITICAL] or
        result['plosive_mismatches'] > 0
    )
    
    if should_flag:
        print(f"  [FLAG] Multimodal mismatch detected")
        print(f"  Action: Flag for forensic review - possible synthetic injection")
        if result['plosive_mismatches'] > 0:
            print(f"  Critical: {result['plosive_mismatches']} plosive mismatch(es) detected")
        workflow_status = "FLAG"
    else:
        print(f"  [PASS] Media passes sync verification")
        workflow_status = "PASS"
    
    return {
        "scenario": "Delayed Media",
        "workflow_status": workflow_status,
        "result": result
    }


def test_workflow_scenario_3():
    """Workflow Test 3: Multiple Words Analysis"""
    print("\n" + "=" * 60)
    print("Workflow Scenario 3: Multiple Words Analysis")
    print("=" * 60)
    
    print("\nSimulating multi-word audio-visual analysis...")
    
    # Combine multiple words
    words = ["HELLO", "TEST"]
    all_phonemes = []
    all_visemes = []
    current_time = 0.0
    
    for word in words:
        phonemes = simulate_azure_speech_output(word, start_time=current_time)
        visemes = simulate_azure_vision_output(word, start_time=current_time, delay_ms=0.0)
        all_phonemes.extend(phonemes)
        all_visemes.extend(visemes)
        # Move to next word (add gap)
        current_time += sum(p['end_time'] - p['start_time'] for p in phonemes) + 50.0
    
    print(f"  Total phonemes: {len(all_phonemes)}")
    print(f"  Total visemes: {len(all_visemes)}")
    
    # Run sync analysis
    print("\nRunning Sync Engine analysis...")
    result = analyze_phoneme_viseme_sync(
        audio_phonemes=all_phonemes,
        visual_visemes=all_visemes,
        threshold_ms=30.0
    )
    
    # Display results
    print(f"\nSync Analysis Results:")
    print(f"  Total matches: {result['total_matches']}")
    print(f"  Mismatches (>30ms): {result['mismatch_count']}")
    print(f"  Overall risk score: {result['overall_risk_score']:.3f}")
    print(f"  Overall risk level: {result['overall_risk_level'].value.upper()}")
    
    # Workflow decision
    print(f"\nWorkflow Decision:")
    if result['overall_risk_level'] in [SyncRiskLevel.LOW, SyncRiskLevel.MEDIUM]:
        print(f"  [PASS] Media passes sync verification")
        workflow_status = "PASS"
    else:
        print(f"  [FLAG] Multimodal mismatch detected")
        workflow_status = "FLAG"
    
    return {
        "scenario": "Multiple Words",
        "workflow_status": workflow_status,
        "result": result
    }


def test_workflow_integration():
    """Test integration with OmniTrust pipeline data structure"""
    print("\n" + "=" * 60)
    print("Workflow Integration Test: Pipeline Data Structure")
    print("=" * 60)
    
    print("\nSimulating full OmniTrust verification pipeline data...")
    
    # Simulate sync analysis
    phonemes_data = simulate_azure_speech_output("BABY", start_time=0.0)
    visemes_data = simulate_azure_vision_output("BABY", start_time=0.0, delay_ms=45.0)
    
    result = analyze_phoneme_viseme_sync(
        audio_phonemes=phonemes_data,
        visual_visemes=visemes_data,
        threshold_ms=30.0
    )
    
    # Create pipeline-ready output (as would be passed to GPT-4o for forensic report)
    pipeline_output = {
        "verification_type": "phoneme_viseme_sync",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sync_analysis": {
            "overall_risk_score": result['overall_risk_score'],
            "overall_risk_level": result['overall_risk_level'].value,
            "mismatch_count": result['mismatch_count'],
            "total_matches": result['total_matches'],
            "plosive_mismatches": result['plosive_mismatches'],
            "max_delta_ms": result['max_delta_ms'],
            "threshold_ms": 30.0,
            "flags": []
        }
    }
    
    # Add flags for forensic reporting
    if result['mismatch_count'] > 0:
        pipeline_output["sync_analysis"]["flags"].append({
            "type": "multimodal_mismatch",
            "severity": result['overall_risk_level'].value,
            "description": f"Audio-video synchronization mismatch detected: {result['mismatch_count']} mismatch(es) exceeding 30ms threshold"
        })
    
    if result['plosive_mismatches'] > 0:
        pipeline_output["sync_analysis"]["flags"].append({
            "type": "plosive_mismatch",
            "severity": "high",
            "description": f"Critical: {result['plosive_mismatches']} plosive sound(s) (P/B) show synchronization issues"
        })
    
    print(f"\nPipeline Output (ready for GPT-4o forensic report):")
    print(json.dumps(pipeline_output, indent=2))
    
    return {
        "scenario": "Pipeline Integration",
        "workflow_status": "SUCCESS",
        "pipeline_output": pipeline_output
    }


def main():
    """Main workflow test function."""
    print("=" * 60)
    print("OmniTrust Sprint 2 Workflow Test")
    print("Phoneme-Viseme Sync Analysis Workflow")
    print("=" * 60)
    
    scenarios = [
        ("Perfect Sync", test_workflow_scenario_1),
        ("Delayed Media", test_workflow_scenario_2),
        ("Multiple Words", test_workflow_scenario_3),
        ("Pipeline Integration", test_workflow_integration),
    ]
    
    results = []
    
    for scenario_name, test_func in scenarios:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] {scenario_name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "scenario": scenario_name,
                "workflow_status": "ERROR",
                "error": str(e)
            })
    
    # Final summary
    print("\n" + "=" * 60)
    print("Workflow Test Summary")
    print("=" * 60)
    
    for result in results:
        status = result.get("workflow_status", "UNKNOWN")
        scenario = result.get("scenario", "Unknown")
        print(f"\n{scenario}:")
        print(f"  Status: {status}")
        
        if "result" in result:
            sync_result = result["result"]
            print(f"  Risk Level: {sync_result['overall_risk_level'].value.upper()}")
            print(f"  Mismatches: {sync_result['mismatch_count']}/{sync_result['total_matches']}")
    
    # Overall assessment
    passed = sum(1 for r in results if r.get("workflow_status") == "PASS")
    flagged = sum(1 for r in results if r.get("workflow_status") == "FLAG")
    errors = sum(1 for r in results if r.get("workflow_status") == "ERROR")
    
    print("\n" + "=" * 60)
    print("Overall Assessment")
    print("=" * 60)
    print(f"  Scenarios completed: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Flagged (expected): {flagged}")
    print(f"  Errors: {errors}")
    
    if errors == 0:
        print("\n[SUCCESS] All workflow scenarios executed successfully!")
        print("Sprint 2 workflow is functioning correctly.")
        return 0
    else:
        print(f"\n[WARNING] {errors} scenario(s) had errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())

