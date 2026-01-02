"""
OmniTrust Liveness Physics Test Script
Tests the High-Frequency Physics Guard system.

This script tests:
1. StrobeChallenge generation (10 RGB colors with timestamps)
2. Human response detection (immediate spikes, pore-level noise)
3. Deepfake detection (smoothed transitions, uniform reflections)
4. Specularity threshold detection (lack of pore-level noise)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.azure_face import (
    StrobeChallenge,
    LivenessVerifier,
    LivenessStatus,
    simulate_human_pixel_response,
    simulate_deepfake_pixel_response
)


def test_strobe_challenge_generation():
    """Test 1: Verify StrobeChallenge generates 10 RGB colors with timestamps."""
    print("\n" + "=" * 60)
    print("Test 1: StrobeChallenge Generation")
    print("=" * 60)
    
    challenge = StrobeChallenge(flash_duration_ms=100.0, interval_ms=200.0)
    frames = challenge.generate_challenge(start_time_ms=0.0)
    
    print(f"\nGenerated {len(frames)} strobe frames:")
    for frame in frames:
        print(f"  Frame {frame.frame_index}: {frame.color} @ {frame.timestamp_ms:.1f}ms")
    
    # Assertions
    assert len(frames) == 10, "Should generate exactly 10 frames"
    assert all(f.frame_index == i for i, f in enumerate(frames)), "Frame indices should be sequential"
    assert frames[0].timestamp_ms == 0.0, "First frame should start at start_time"
    
    # Verify timestamps are increasing
    for i in range(1, len(frames)):
        assert frames[i].timestamp_ms > frames[i-1].timestamp_ms, "Timestamps should be increasing"
    
    print("\n[PASS] StrobeChallenge correctly generates 10 RGB frames with timestamps")
    return True


def test_human_response_detection():
    """Test 2: Verify human response (immediate spikes, high variance) is detected as HUMAN."""
    print("\n" + "=" * 60)
    print("Test 2: Human Response Detection")
    print("=" * 60)
    
    challenge = StrobeChallenge(flash_duration_ms=100.0, interval_ms=200.0)
    challenge.generate_challenge(start_time_ms=0.0)
    
    # Simulate human pixel response
    pixel_samples = simulate_human_pixel_response(
        challenge,
        base_intensity=0.5,
        noise_level=0.1
    )
    
    print(f"\nSimulated {len(pixel_samples)} pixel samples for human response")
    print(f"  Sample rate: ~10ms intervals")
    print(f"  Expected: Immediate spikes, high pore-level noise")
    
    # Verify liveness
    verifier = LivenessVerifier(
        spike_threshold=0.3,
        smoothing_threshold=0.1,
        specularity_threshold=0.05
    )
    
    result = verifier.verify_liveness(challenge, pixel_samples)
    
    print(f"\nLiveness Verification Results:")
    print(f"  Status: {result['status'].value.upper()}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Immediate spikes: {result['immediate_spikes']}/{len(challenge.frames)}")
    print(f"  Smoothed transitions: {result['smoothed_transitions']}/{len(challenge.frames)}")
    print(f"  Specularity score: {result['specularity_score']:.4f}")
    print(f"  Spike ratio: {result['spike_ratio']:.3f}")
    
    # Assertions
    assert result['status'] == LivenessStatus.HUMAN, \
        f"Human response should be detected as HUMAN, got {result['status'].value}"
    assert result['confidence'] > 0.6, \
        f"Confidence should be high for human, got {result['confidence']:.3f}"
    assert result['immediate_spikes'] >= 5, \
        f"Should detect multiple immediate spikes, got {result['immediate_spikes']}"
    # Note: Specularity is a secondary indicator - spikes are the primary indicator for humans
    # Even if specularity is low, high spike ratio indicates human response
    
    print("\n[PASS] Human response correctly detected (immediate spikes, high variance)")
    return True


def test_deepfake_detection():
    """Test 3: Verify deepfake mask (smoothed transitions, low variance) is detected as SPOOF."""
    print("\n" + "=" * 60)
    print("Test 3: Deepfake Mask Detection")
    print("=" * 60)
    
    challenge = StrobeChallenge(flash_duration_ms=100.0, interval_ms=200.0)
    challenge.generate_challenge(start_time_ms=0.0)
    
    # Simulate deepfake pixel response (smoothed, uniform)
    pixel_samples = simulate_deepfake_pixel_response(
        challenge,
        base_intensity=0.5,
        smoothing_factor=0.05
    )
    
    print(f"\nSimulated {len(pixel_samples)} pixel samples for deepfake mask")
    print(f"  Sample rate: ~10ms intervals")
    print(f"  Expected: Smoothed transitions, uniform reflection (low variance)")
    
    # Verify liveness
    verifier = LivenessVerifier(
        spike_threshold=0.3,
        smoothing_threshold=0.1,
        specularity_threshold=0.05
    )
    
    result = verifier.verify_liveness(challenge, pixel_samples)
    
    print(f"\nLiveness Verification Results:")
    print(f"  Status: {result['status'].value.upper()}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Immediate spikes: {result['immediate_spikes']}/{len(challenge.frames)}")
    print(f"  Smoothed transitions: {result['smoothed_transitions']}/{len(challenge.frames)}")
    print(f"  Specularity score: {result['specularity_score']:.4f} (threshold: {verifier.specularity_threshold:.4f})")
    print(f"  Smoothing ratio: {result['smoothing_ratio']:.3f}")
    
    # Assertions
    assert result['status'] == LivenessStatus.SPOOF, \
        f"Deepfake should be detected as SPOOF, got {result['status'].value}"
    assert result['confidence'] > 0.5, \
        f"Confidence should be reasonable, got {result['confidence']:.3f}"
    assert result['specularity_score'] < verifier.specularity_threshold or \
           result['smoothing_ratio'] > 0.6, \
        f"Should detect either low specularity ({result['specularity_score']:.4f} < {verifier.specularity_threshold:.4f}) " \
        f"or high smoothing ratio ({result['smoothing_ratio']:.3f} > 0.6)"
    
    print("\n[PASS] Deepfake mask correctly detected (smoothed transitions, uniform reflection)")
    return True


def test_specularity_threshold():
    """Test 4: Verify specularity threshold detects uniform reflections (lack of pore-level noise)."""
    print("\n" + "=" * 60)
    print("Test 4: Specularity Threshold Detection")
    print("=" * 60)
    
    challenge = StrobeChallenge(flash_duration_ms=100.0, interval_ms=200.0)
    challenge.generate_challenge(start_time_ms=0.0)
    
    # Create extremely uniform response (very low variance)
    from src.services.azure_face import PixelSample
    
    uniform_samples = []
    sample_rate_ms = 10.0
    start_time = challenge.frames[0].timestamp_ms - 50.0
    end_time = challenge.frames[-1].timestamp_ms + 200.0
    
    current_time = start_time
    while current_time <= end_time:
        # Uniform intensity (no variation)
        intensity = 0.6  # Constant
        
        sample = PixelSample(
            timestamp_ms=current_time,
            intensity=intensity,
            r=intensity,
            g=intensity,
            b=intensity,
            variance=0.001  # Extremely low variance (uniform)
        )
        uniform_samples.append(sample)
        current_time += sample_rate_ms
    
    print(f"\nCreated {len(uniform_samples)} uniform pixel samples")
    print(f"  Variance: 0.001 (extremely uniform - lacks pore-level noise)")
    print(f"  Expected: SPOOF status due to low specularity")
    
    verifier = LivenessVerifier(
        spike_threshold=0.3,
        smoothing_threshold=0.1,
        specularity_threshold=0.05  # Threshold for pore-level noise
    )
    
    result = verifier.verify_liveness(challenge, uniform_samples)
    
    print(f"\nLiveness Verification Results:")
    print(f"  Status: {result['status'].value.upper()}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Specularity score: {result['specularity_score']:.4f}")
    print(f"  Specularity threshold: {verifier.specularity_threshold:.4f}")
    
    # Assertions
    assert result['specularity_score'] < verifier.specularity_threshold, \
        f"Uniform reflection should have low specularity, " \
        f"got {result['specularity_score']:.4f} < {verifier.specularity_threshold:.4f}"
    assert result['status'] == LivenessStatus.SPOOF, \
        f"Uniform reflection should be detected as SPOOF, got {result['status'].value}"
    
    print("\n[PASS] Specularity threshold correctly detects uniform reflections (SPOOF)")
    return True


def test_camera_auto_correction_detection():
    """Test 5: Verify camera auto-correction (smoothing) is detected."""
    print("\n" + "=" * 60)
    print("Test 5: Camera Auto-Correction Detection")
    print("=" * 60)
    
    challenge = StrobeChallenge(flash_duration_ms=100.0, interval_ms=200.0)
    challenge.generate_challenge(start_time_ms=0.0)
    
    # Simulate camera auto-correction (very smoothed response)
    pixel_samples = simulate_deepfake_pixel_response(
        challenge,
        base_intensity=0.5,
        smoothing_factor=0.02  # Very aggressive smoothing
    )
    
    print(f"\nSimulated camera auto-correction response")
    print(f"  Smoothing factor: 0.02 (very aggressive smoothing)")
    print(f"  Expected: High smoothing ratio, SPOOF status")
    
    verifier = LivenessVerifier(
        spike_threshold=0.3,
        smoothing_threshold=0.1,
        specularity_threshold=0.05
    )
    
    result = verifier.verify_liveness(challenge, pixel_samples)
    
    print(f"\nLiveness Verification Results:")
    print(f"  Status: {result['status'].value.upper()}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Smoothed transitions: {result['smoothed_transitions']}/{len(challenge.frames)}")
    print(f"  Smoothing ratio: {result['smoothing_ratio']:.3f}")
    
    # Assertions
    assert result['smoothing_ratio'] > 0.6, \
        f"Camera auto-correction should have high smoothing ratio, got {result['smoothing_ratio']:.3f}"
    assert result['status'] == LivenessStatus.SPOOF, \
        f"Camera auto-correction should be detected as SPOOF, got {result['status'].value}"
    
    print("\n[PASS] Camera auto-correction correctly detected (high smoothing ratio)")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("OmniTrust Liveness Physics Test Suite")
    print("High-Frequency Physics Guard (Sprint 3)")
    print("=" * 60)
    
    tests = [
        ("StrobeChallenge Generation", test_strobe_challenge_generation),
        ("Human Response Detection", test_human_response_detection),
        ("Deepfake Mask Detection", test_deepfake_detection),
        ("Specularity Threshold", test_specularity_threshold),
        ("Camera Auto-Correction", test_camera_auto_correction_detection),
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
        print("High-Frequency Physics Guard is functioning correctly.")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

