"""
Deterministic Noise Generator with HMAC-based Seeding

Implements cryptographically secure deterministic noise for differential privacy.
Prevents averaging attacks while maintaining DP guarantees.

Security Pattern:
    seed = HMAC-SHA256(secret_key, query_id || time_window)
    noise = Laplace(PRNG(seed), scale=sensitivity/epsilon)

Key Properties:
    ✅ Same query + time window = same noise (deterministic)
    ✅ Different queries = different noise (unique seeds)
    ✅ Cryptographically unpredictable without secret key
    ✅ Periodic rotation prevents long-term averaging attacks
"""

import hmac
import hashlib
import numpy as np
from datetime import datetime, timezone
from django.conf import settings
from typing import Union


class DeterministicNoiseGenerator:
    """
    Generates deterministic Laplace noise using HMAC-based seeding
    
    Usage:
        noise = DeterministicNoiseGenerator.generate_laplace_noise(
            scale=1.0,
            query_id="abc123",
            size=1
        )
    """
    
    @staticmethod
    def get_time_window() -> str:
        """
        Get current time window for seed rotation
        
        Returns:
            Time window string (e.g., "2026-02-05-00" for daily rotation)
        
        Examples:
            Daily rotation (24h):   "2026-02-05-00"
            Hourly rotation (1h):   "2026-02-05-14"
            Weekly rotation (168h): "2026-W05"
        """
        rotation_hours = getattr(settings, 'DP_SEED_ROTATION_HOURS', 24)
        now = datetime.now(timezone.utc)
        
        if rotation_hours == 24:
            # Daily rotation: YYYY-MM-DD-00
            return now.strftime("%Y-%m-%d-00")
        elif rotation_hours == 1:
            # Hourly rotation: YYYY-MM-DD-HH
            return now.strftime("%Y-%m-%d-%H")
        elif rotation_hours == 168:
            # Weekly rotation: YYYY-Www
            return now.strftime("%Y-W%U")
        else:
            # Custom rotation: bucket by rotation_hours
            hours_since_epoch = int(now.timestamp() / 3600)
            bucket = hours_since_epoch // rotation_hours
            return f"bucket-{bucket}"
    
    @staticmethod
    def derive_seed(query_id: str, time_window: str) -> int:
        """
        Derive cryptographic seed using HMAC-SHA256
        
        Args:
            query_id: Unique identifier for the query
            time_window: Current time window (from get_time_window())
        
        Returns:
            Integer seed for PRNG (32-bit unsigned)
        
        Security:
            - Uses HMAC-SHA256 with secret server key
            - Combines query_id and time_window
            - Output is cryptographically unpredictable
        """
        # Get secret key from settings
        secret_key = getattr(
            settings,
            'DP_NOISE_SECRET_KEY',
            'INSECURE_DEFAULT_KEY_CHANGE_IN_PRODUCTION'
        ).encode('utf-8')
        
        # Combine query_id and time_window
        message = f"{query_id}||{time_window}".encode('utf-8')
        
        # Compute HMAC-SHA256
        hmac_digest = hmac.new(secret_key, message, hashlib.sha256).digest()
        
        # Convert first 4 bytes to unsigned 32-bit integer
        seed = int.from_bytes(hmac_digest[:4], byteorder='big', signed=False)
        
        return seed
    
    @staticmethod
    def generate_laplace_noise(
        scale: float,
        query_id: str,
        size: int = 1,
        time_window: str = None
    ) -> np.ndarray:
        """
        Generate deterministic Laplace noise
        
        Args:
            scale: Laplace scale parameter (sensitivity / epsilon)
            query_id: Unique query identifier
            size: Number of noise samples to generate
            time_window: Optional time window (auto-computed if None)
        
        Returns:
            NumPy array of Laplace noise samples
        
        Example:
            >>> noise = generate_laplace_noise(scale=1.0, query_id="query123")
            >>> print(noise)
            array([0.42])  # Deterministic for same query_id + time_window
        """
        # Get current time window if not provided
        if time_window is None:
            time_window = DeterministicNoiseGenerator.get_time_window()
        
        # Derive cryptographic seed
        seed = DeterministicNoiseGenerator.derive_seed(query_id, time_window)
        
        # Create seeded random generator
        rng = np.random.RandomState(seed)
        
        # Generate Laplace noise using inverse CDF method
        # Laplace(0, b) = -b * sign(u) * log(1 - 2|u|) where u ~ Uniform(-0.5, 0.5)
        uniform_samples = rng.uniform(-0.5, 0.5, size=size)
        laplace_noise = -scale * np.sign(uniform_samples) * np.log(1 - 2 * np.abs(uniform_samples))
        
        return laplace_noise
    
    @staticmethod
    def generate_gaussian_noise(
        scale: float,
        query_id: str,
        size: int = 1,
        time_window: str = None
    ) -> np.ndarray:
        """
        Generate deterministic Gaussian noise (for Gaussian DP)
        
        Args:
            scale: Gaussian standard deviation (sigma)
            query_id: Unique query identifier
            size: Number of noise samples to generate
            time_window: Optional time window (auto-computed if None)
        
        Returns:
            NumPy array of Gaussian noise samples
        """
        if time_window is None:
            time_window = DeterministicNoiseGenerator.get_time_window()
        
        seed = DeterministicNoiseGenerator.derive_seed(query_id, time_window)
        rng = np.random.RandomState(seed)
        
        gaussian_noise = rng.normal(loc=0.0, scale=scale, size=size)
        
        return gaussian_noise


# Convenience functions
def get_deterministic_laplace_noise(scale: float, query_id: str) -> float:
    """
    Get single deterministic Laplace noise value
    
    Args:
        scale: Laplace scale (sensitivity / epsilon)
        query_id: Query identifier
    
    Returns:
        Single noise value
    """
    return DeterministicNoiseGenerator.generate_laplace_noise(
        scale=scale,
        query_id=query_id,
        size=1
    )[0]


def get_deterministic_gaussian_noise(scale: float, query_id: str) -> float:
    """
    Get single deterministic Gaussian noise value
    
    Args:
        scale: Gaussian sigma
        query_id: Query identifier
    
    Returns:
        Single noise value
    """
    return DeterministicNoiseGenerator.generate_gaussian_noise(
        scale=scale,
        query_id=query_id,
        size=1
    )[0]
