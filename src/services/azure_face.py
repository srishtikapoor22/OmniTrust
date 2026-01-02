"""
OmniTrust Azure Face Service (Sprint 3)
High-Frequency Physics Guard - Light-Bounce Liveness Detection

Implements active "Light-Bounce" verification by flashing RGB colors
and analyzing pixel-level reflections on skin pores to expose 2D/digital injections.
Detects camera auto-correction and deepfake masks through physics-based analysis.
"""

import random
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from collections import deque


class LivenessStatus(Enum):
    """Liveness verification status."""
    HUMAN = "human"
    SPOOF = "spoof"
    UNCERTAIN = "uncertain"


@dataclass
class RGBColor:
    """Represents an RGB color."""
    r: int  # Red component (0-255)
    g: int  # Green component (0-255)
    b: int  # Blue component (0-255)
    
    def __str__(self) -> str:
        return f"RGB({self.r}, {self.g}, {self.b})"
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """Convert to tuple."""
        return (self.r, self.g, self.b)


@dataclass
class StrobeFrame:
    """Represents a single strobe frame with RGB color and timestamp."""
    color: RGBColor
    timestamp_ms: float  # Timestamp in milliseconds
    frame_index: int  # Frame index (0-9)


class StrobeChallenge:
    """
    Generates a strobe challenge with RGB colors and millisecond timestamps.
    
    Creates a sequence of 10 RGB color flashes with precise timing
    to detect camera auto-correction and deepfake smoothing.
    """
    
    # High-contrast RGB colors for better detection
    CHALLENGE_COLORS = [
        RGBColor(255, 0, 0),    # Red
        RGBColor(0, 255, 0),    # Green
        RGBColor(0, 0, 255),    # Blue
        RGBColor(255, 255, 0),  # Yellow
        RGBColor(255, 0, 255),  # Magenta
        RGBColor(0, 255, 255),  # Cyan
        RGBColor(255, 255, 255), # White
        RGBColor(0, 0, 0),      # Black
        RGBColor(255, 128, 0),  # Orange
        RGBColor(128, 0, 255),  # Purple
    ]
    
    def __init__(self, flash_duration_ms: float = 100.0, interval_ms: float = 200.0):
        """
        Initialize Strobe Challenge.
        
        Args:
            flash_duration_ms: Duration of each RGB flash in milliseconds.
            interval_ms: Interval between flashes in milliseconds.
        """
        self.flash_duration_ms = flash_duration_ms
        self.interval_ms = interval_ms
        self.frames: List[StrobeFrame] = []
    
    def generate_challenge(self, start_time_ms: float = 0.0) -> List[StrobeFrame]:
        """
        Generate a sequence of 10 RGB color flashes with timestamps.
        
        Args:
            start_time_ms: Starting timestamp in milliseconds.
        
        Returns:
            List of 10 StrobeFrame objects with colors and timestamps.
        """
        self.frames = []
        current_time = start_time_ms
        
        # Use first 10 colors (or shuffle if desired)
        colors = self.CHALLENGE_COLORS[:10]
        
        for i, color in enumerate(colors):
            frame = StrobeFrame(
                color=color,
                timestamp_ms=current_time,
                frame_index=i
            )
            self.frames.append(frame)
            current_time += self.flash_duration_ms + self.interval_ms
        
        return self.frames
    
    def get_challenge_sequence(self) -> List[Dict[str, Any]]:
        """
        Get challenge sequence as dictionary list for easy serialization.
        
        Returns:
            List of dictionaries with color and timestamp info.
        """
        return [
            {
                "frame_index": frame.frame_index,
                "timestamp_ms": frame.timestamp_ms,
                "color": {
                    "r": frame.color.r,
                    "g": frame.color.g,
                    "b": frame.color.b
                },
                "color_str": str(frame.color)
            }
            for frame in self.frames
        ]


@dataclass
class PixelSample:
    """Represents a pixel sample at a specific timestamp."""
    timestamp_ms: float
    intensity: float  # Average intensity (0.0-1.0)
    r: float  # Red component (0.0-1.0)
    g: float  # Green component (0.0-1.0)
    b: float  # Blue component (0.0-1.0)
    variance: float  # Pixel variance (for pore-level noise detection)


class LivenessVerifier:
    """
    Verifies liveness by analyzing pixel reflection patterns.
    
    Detects:
    - Immediate Reflection Spikes (Human): Sharp, immediate response to RGB flashes
    - Smoothed Transitions (Camera Auto-Correction/Deepfake): Gradual, smoothed response
    - Uniform Reflections (Spoof): Lack of pore-level noise variation
    """
    
    def __init__(
        self,
        spike_threshold: float = 0.3,  # Minimum change for immediate spike
        smoothing_threshold: float = 0.1,  # Maximum change rate for smoothed transition
        specularity_threshold: float = 0.05,  # Minimum variance for pore-level noise
        response_window_ms: float = 50.0  # Window to detect response after flash
    ):
        """
        Initialize Liveness Verifier.
        
        Args:
            spike_threshold: Minimum intensity change to detect immediate spike.
            smoothing_threshold: Maximum change rate to detect smoothing (per ms).
            specularity_threshold: Minimum variance threshold for pore-level noise.
            response_window_ms: Time window to detect response after flash (ms).
        """
        self.spike_threshold = spike_threshold
        self.smoothing_threshold = smoothing_threshold
        self.specularity_threshold = specularity_threshold
        self.response_window_ms = response_window_ms
    
    def verify_liveness(
        self,
        strobe_challenge: StrobeChallenge,
        pixel_samples: List[PixelSample]
    ) -> Dict[str, Any]:
        """
        Verify liveness based on pixel reflection patterns.
        
        Args:
            strobe_challenge: The StrobeChallenge that was presented.
            pixel_samples: List of pixel samples with timestamps and intensities.
        
        Returns:
            Dictionary with:
            - status: LivenessStatus
            - confidence: float (0.0-1.0)
            - immediate_spikes: int (count of immediate reflection spikes)
            - smoothed_transitions: int (count of smoothed transitions)
            - specularity_score: float (variance-based score)
            - analysis: Dict with detailed results
        """
        if not strobe_challenge.frames:
            raise ValueError("StrobeChallenge must have frames generated")
        
        if not pixel_samples:
            return {
                "status": LivenessStatus.UNCERTAIN,
                "confidence": 0.0,
                "immediate_spikes": 0,
                "smoothed_transitions": 0,
                "specularity_score": 0.0,
                "analysis": {"error": "No pixel samples provided"}
            }
        
        # Sort pixel samples by timestamp
        sorted_samples = sorted(pixel_samples, key=lambda x: x.timestamp_ms)
        
        immediate_spikes = 0
        smoothed_transitions = 0
        specularity_scores = []
        
        # Analyze each strobe frame
        for frame in strobe_challenge.frames:
            # Find samples within response window
            frame_start = frame.timestamp_ms
            frame_end = frame.timestamp_ms + self.response_window_ms
            
            # Get baseline (just before flash)
            baseline_samples = [
                s for s in sorted_samples
                if frame_start - 50.0 <= s.timestamp_ms < frame_start
            ]
            
            # Get response samples (during and after flash)
            response_samples = [
                s for s in sorted_samples
                if frame_start <= s.timestamp_ms <= frame_end
            ]
            
            if not baseline_samples or not response_samples:
                continue
            
            baseline_intensity = sum(s.intensity for s in baseline_samples) / len(baseline_samples)
            baseline_variance = self._calculate_variance([s.intensity for s in baseline_samples])
            
            # Check for immediate spike (human response)
            first_response = response_samples[0]
            intensity_change = abs(first_response.intensity - baseline_intensity)
            
            if intensity_change >= self.spike_threshold:
                # Check if it's immediate (within first 20ms)
                time_to_response = first_response.timestamp_ms - frame_start
                if time_to_response <= 20.0:
                    immediate_spikes += 1
            
            # Check for smoothed transition (camera/deepfake)
            if len(response_samples) >= 3:
                transition_smooth = self._check_smoothed_transition(
                    baseline_intensity,
                    [s.intensity for s in response_samples]
                )
                if transition_smooth:
                    smoothed_transitions += 1
            
            # Check specularity (pore-level noise)
            response_variance = self._calculate_variance([s.intensity for s in response_samples])
            response_variance = max(response_variance, self._calculate_variance([s.variance for s in response_samples]))
            specularity_scores.append(response_variance)
        
        # Calculate overall specularity score
        avg_specularity = sum(specularity_scores) / len(specularity_scores) if specularity_scores else 0.0
        
        # Determine liveness status
        total_frames = len(strobe_challenge.frames)
        spike_ratio = immediate_spikes / total_frames if total_frames > 0 else 0.0
        smoothing_ratio = smoothed_transitions / total_frames if total_frames > 0 else 0.0
        
        # Decision logic (prioritize spike detection over specularity)
        status = LivenessStatus.UNCERTAIN
        confidence = 0.5
        
        # High spike ratio = HUMAN (immediate reflections) - strongest indicator
        if spike_ratio > 0.7:
            status = LivenessStatus.HUMAN
            confidence = spike_ratio
            # Even with low specularity, if we have clear spikes, it's likely human
            # (though we note the specularity for additional context)
        # High smoothing ratio = SPOOF (camera auto-correction or deepfake)
        elif smoothing_ratio > 0.6:
            status = LivenessStatus.SPOOF
            confidence = smoothing_ratio
        # Low specularity (uniform reflection) = SPOOF (only if no strong spikes)
        elif avg_specularity < self.specularity_threshold and spike_ratio < 0.5:
            status = LivenessStatus.SPOOF
            confidence = 1.0 - (avg_specularity / self.specularity_threshold)
        # Mixed signals = UNCERTAIN
        else:
            status = LivenessStatus.UNCERTAIN
            confidence = max(spike_ratio, 1.0 - smoothing_ratio)
        
        return {
            "status": status,
            "confidence": confidence,
            "immediate_spikes": immediate_spikes,
            "smoothed_transitions": smoothed_transitions,
            "specularity_score": avg_specularity,
            "spike_ratio": spike_ratio,
            "smoothing_ratio": smoothing_ratio,
            "analysis": {
                "total_frames": total_frames,
                "immediate_spikes": immediate_spikes,
                "smoothed_transitions": smoothed_transitions,
                "avg_specularity": avg_specularity,
                "specularity_threshold": self.specularity_threshold,
                "decision": status.value
            }
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values or len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def _check_smoothed_transition(
        self,
        baseline: float,
        response_intensities: List[float]
    ) -> bool:
        """
        Check if transition is smoothed (gradual change).
        
        Returns True if the transition is too smooth (indicating auto-correction).
        """
        if len(response_intensities) < 3:
            return False
        
        # Calculate change rates between consecutive samples
        change_rates = []
        for i in range(1, len(response_intensities)):
            # Assume samples are roughly evenly spaced (approximation)
            change = abs(response_intensities[i] - response_intensities[i-1])
            change_rates.append(change)
        
        if not change_rates:
            return False
        
        avg_change_rate = sum(change_rates) / len(change_rates)
        
        # If average change rate is too low, it's smoothed
        return avg_change_rate < self.smoothing_threshold
    
    def _calculate_response_time(self, baseline: float, samples: List[PixelSample]) -> Optional[float]:
        """Calculate time to reach significant response."""
        for sample in samples:
            if abs(sample.intensity - baseline) >= self.spike_threshold:
                return sample.timestamp_ms
        return None


def simulate_human_pixel_response(
    strobe_challenge: StrobeChallenge,
    base_intensity: float = 0.5,
    noise_level: float = 0.1
) -> List[PixelSample]:
    """
    Simulate pixel response from a human face (immediate spikes with pore-level noise).
    
    Args:
        strobe_challenge: The strobe challenge to respond to.
        base_intensity: Base pixel intensity.
        noise_level: Level of pore-level noise/variance.
    
    Returns:
        List of PixelSample objects simulating human response.
    """
    samples = []
    sample_rate_ms = 10.0  # Sample every 10ms
    
    # Create samples for entire challenge duration
    if not strobe_challenge.frames:
        return samples
    
    start_time = strobe_challenge.frames[0].timestamp_ms - 50.0
    end_time = strobe_challenge.frames[-1].timestamp_ms + 200.0
    
    current_time = start_time
    frame_index = 0
    
    while current_time <= end_time:
        # Find active frame (if any)
        active_frame = None
        for frame in strobe_challenge.frames:
            if frame.timestamp_ms <= current_time <= frame.timestamp_ms + 100.0:
                active_frame = frame
                break
        
        # Calculate intensity
        if active_frame:
            # Immediate spike for human response
            time_since_flash = current_time - active_frame.timestamp_ms
            if time_since_flash <= 20.0:
                # Sharp spike
                spike_factor = 1.0 - (time_since_flash / 20.0)
                intensity = base_intensity + (0.4 * spike_factor)
            else:
                # Gradual decay
                decay_factor = max(0, 1.0 - ((time_since_flash - 20.0) / 80.0))
                intensity = base_intensity + (0.4 * decay_factor)
        else:
            intensity = base_intensity
        
        # Add pore-level noise (high variance for humans)
        noise = random.uniform(-noise_level, noise_level)
        intensity = max(0.0, min(1.0, intensity + noise))
        
        # Calculate RGB components (simplified)
        if active_frame:
            r = min(1.0, intensity * (active_frame.color.r / 255.0))
            g = min(1.0, intensity * (active_frame.color.g / 255.0))
            b = min(1.0, intensity * (active_frame.color.b / 255.0))
        else:
            r = g = b = intensity
        
        # High variance for pore-level noise (humans have texture)
        variance = random.uniform(noise_level * 0.5, noise_level * 1.5)
        
        sample = PixelSample(
            timestamp_ms=current_time,
            intensity=intensity,
            r=r,
            g=g,
            b=b,
            variance=variance
        )
        samples.append(sample)
        
        current_time += sample_rate_ms
    
    return samples


def simulate_deepfake_pixel_response(
    strobe_challenge: StrobeChallenge,
    base_intensity: float = 0.5,
    smoothing_factor: float = 0.05
) -> List[PixelSample]:
    """
    Simulate pixel response from a deepfake mask (smoothed transitions, low variance).
    
    Args:
        strobe_challenge: The strobe challenge to respond to.
        base_intensity: Base pixel intensity.
        smoothing_factor: Smoothing factor (lower = more smoothing).
    
    Returns:
        List of PixelSample objects simulating deepfake response.
    """
    samples = []
    sample_rate_ms = 10.0
    
    if not strobe_challenge.frames:
        return samples
    
    start_time = strobe_challenge.frames[0].timestamp_ms - 50.0
    end_time = strobe_challenge.frames[-1].timestamp_ms + 200.0
    
    current_time = start_time
    current_intensity = base_intensity
    
    while current_time <= end_time:
        # Find target intensity (what it should be)
        target_intensity = base_intensity
        active_frame = None
        
        for frame in strobe_challenge.frames:
            if frame.timestamp_ms <= current_time <= frame.timestamp_ms + 100.0:
                active_frame = frame
                time_since_flash = current_time - frame.timestamp_ms
                target_intensity = base_intensity + (0.3 * (1.0 - time_since_flash / 100.0))
                break
        
        # Smooth transition (gradual change, not immediate)
        intensity_diff = target_intensity - current_intensity
        current_intensity += intensity_diff * smoothing_factor  # Gradual smoothing
        
        # Low variance (uniform reflection, lacks pore-level noise)
        variance = random.uniform(0.0, 0.01)  # Very low variance
        
        # Calculate RGB
        if active_frame:
            r = min(1.0, current_intensity * (active_frame.color.r / 255.0))
            g = min(1.0, current_intensity * (active_frame.color.g / 255.0))
            b = min(1.0, current_intensity * (active_frame.color.b / 255.0))
        else:
            r = g = b = current_intensity
        
        sample = PixelSample(
            timestamp_ms=current_time,
            intensity=current_intensity,
            r=r,
            g=g,
            b=b,
            variance=variance
        )
        samples.append(sample)
        
        current_time += sample_rate_ms
    
    return samples

