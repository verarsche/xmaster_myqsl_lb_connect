"""
Shared utility helpers for musicgen.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Tuple

import numpy as np


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def check_ffmpeg() -> str:
    """Return the path to the ffmpeg binary or raise RuntimeError."""
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise RuntimeError(
            "ffmpeg not found on PATH.\n"
            "Install it with:\n"
            "  Ubuntu/Debian : sudo apt install ffmpeg\n"
            "  macOS (brew)  : brew install ffmpeg\n"
            "  Windows       : https://ffmpeg.org/download.html"
        )
    return binary


def run_ffmpeg(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run ffmpeg with the given arguments, forwarding stderr to the terminal."""
    binary = check_ffmpeg()
    cmd = [binary, "-hide_banner", "-loglevel", "warning", *args]
    return subprocess.run(cmd, check=check)


# ---------------------------------------------------------------------------
# WAV I/O helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100


def read_wav(path: str | Path) -> Tuple[np.ndarray, int]:
    """
    Read a WAV file (mono or stereo, 16-bit PCM).

    Returns
    -------
    samples : np.ndarray  – float64 in [-1.0, 1.0], shape (channels, N)
    rate    : int
    """
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth, np.int16)
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)

    # Normalise to [-1, 1]
    max_val = float(2 ** (sampwidth * 8 - 1))
    samples /= max_val

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).T  # (channels, frames)
    else:
        samples = samples.reshape(1, -1)

    return samples, rate


def write_wav(path: str | Path, samples: np.ndarray, rate: int) -> None:
    """
    Write float64 samples (channels, frames) to a 16-bit PCM WAV file.
    Clipping is applied before conversion.
    """
    # Transpose from (channels, frames) to (frames, channels) for wave output
    if samples.ndim == 2:
        out = samples.T
    else:
        out = samples.reshape(-1, 1)

    clipped = np.clip(out, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        if pcm.ndim == 2:
            wf.setnchannels(pcm.shape[1])
        else:
            wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def ensure_wav(path: str | Path, output: str | Path | None = None) -> Path:
    """
    If *path* is not a WAV file, convert it with ffmpeg and return the path to
    the converted file.  If it is already WAV, return *path* as a Path.
    """
    src = Path(path)
    if src.suffix.lower() == ".wav":
        return src
    dst = Path(output) if output else src.with_suffix(".wav")
    run_ffmpeg("-y", "-i", str(src), "-ac", "2", "-ar", str(SAMPLE_RATE),
               "-acodec", "pcm_s16le", str(dst))
    return dst


def is_wav(path: str | Path) -> bool:
    return Path(path).suffix.lower() == ".wav"
