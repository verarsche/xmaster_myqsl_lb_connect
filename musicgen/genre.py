"""
genre.py — Deterministic genre-style processing pipeline.

Supported styles
----------------
rock  – Soft-clipping distortion, mid-range EQ boost, heavy compression,
        synthetic rock drum layer.
rap   – Sub-bass boost, hi-hat rhythm, sidechain-style pumping,
        slight room reverb.
metal – Hard-clipping distortion, extreme compression, presence boost (2–5 kHz),
        blast-beat drum layer.

Architecture notes
------------------
Each style is implemented as a chain of DSP functions (filters, clippers,
compressors, drum generators) that operate on NumPy arrays.  This keeps the
pipeline 100 % local and dependency-free beyond NumPy/SciPy.

To integrate an AI model (e.g. MusicGen, Stable Audio) replace or extend
``_ai_hook()`` at the end of each style function.  The hook receives and
returns ``(samples: np.ndarray, rate: int)`` so the signature is stable.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

import numpy as np
from scipy import signal as sp_signal

from .utils import read_wav, write_wav, ensure_wav, SAMPLE_RATE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SUPPORTED_STYLES = ("rock", "rap", "metal")


def apply_genre(
    audio_path: str,
    style: str,
    output_path: str,
) -> Path:
    """
    Load *audio_path*, apply *style* genre processing, save to *output_path*.

    Parameters
    ----------
    audio_path  : Source audio (.wav or any format ffmpeg can read).
    style       : ``"rock"`` | ``"rap"`` | ``"metal"``
    output_path : Destination WAV file.

    Returns
    -------
    Path to the output file.
    """
    style = style.lower().strip()
    if style not in SUPPORTED_STYLES:
        raise ValueError(
            f"Unknown style '{style}'.  "
            f"Choose from: {', '.join(SUPPORTED_STYLES)}"
        )

    wav_src = ensure_wav(audio_path)
    samples, rate = read_wav(wav_src)

    # Ensure stereo
    if samples.shape[0] == 1:
        samples = np.vstack([samples, samples])

    processors = {
        "rock":  _process_rock,
        "rap":   _process_rap,
        "metal": _process_metal,
    }
    out_samples = processors[style](samples, rate)

    # AI hook (no-op by default – replace to integrate an external model)
    out_samples = _ai_hook(out_samples, rate, style)

    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    write_wav(dst, out_samples, rate)
    print(f"✓ [{style.upper()}] processed  →  {dst}")
    return dst


# ---------------------------------------------------------------------------
# Genre processors
# ---------------------------------------------------------------------------

def _process_rock(samples: np.ndarray, rate: int) -> np.ndarray:
    """
    Rock pipeline
    -------------
    1. High-pass filter at 80 Hz (remove rumble)
    2. Soft-clipping distortion (tanh) at drive=4
    3. Mid-range EQ boost +6 dB at 1 kHz (presence / attack)
    4. RMS compressor  ratio=4:1, threshold=-18 dBFS
    5. Synthetic rock drum layer (kick + snare + hi-hat at 120 BPM)
    6. Normalise to -1 dBFS
    """
    s = _highpass(samples, 80, rate)
    s = _soft_clip(s, drive=4.0)
    s = _peaking_eq(s, rate, fc=1000, gain_db=6.0, q=1.0)
    s = _compress(s, threshold_db=-18, ratio=4.0, rate=rate)
    drums = _rock_drums(samples.shape[1], rate, bpm=120)
    s = _mix(s, drums, gain=0.35)
    s = _normalise(s, target_db=-1.0)
    return s


def _process_rap(samples: np.ndarray, rate: int) -> np.ndarray:
    """
    Rap pipeline
    ------------
    1. Sub-bass boost +8 dB at 80 Hz
    2. High-shelf cut above 12 kHz (warm top-end)
    3. Room reverb (short, 40 ms)
    4. RMS compressor ratio=6:1, threshold=-20 dBFS
    5. Synthetic trap/boom-bap drum layer at 90 BPM
    6. Normalise to -1 dBFS
    """
    s = _peaking_eq(samples, rate, fc=80, gain_db=8.0, q=0.7)
    s = _high_shelf(s, rate, fc=12000, gain_db=-4.0)
    s = _reverb(s, rate, delay_ms=40, decay=0.25)
    s = _compress(s, threshold_db=-20, ratio=6.0, rate=rate)
    drums = _rap_drums(samples.shape[1], rate, bpm=90)
    s = _mix(s, drums, gain=0.45)
    s = _normalise(s, target_db=-1.0)
    return s


def _process_metal(samples: np.ndarray, rate: int) -> np.ndarray:
    """
    Metal pipeline
    --------------
    1. High-pass filter at 100 Hz (tight low-end)
    2. Hard-clipping distortion at drive=10
    3. Presence boost +8 dB at 3 kHz
    4. Heavy compressor ratio=10:1, threshold=-24 dBFS
    5. Short plate reverb (60 ms)
    6. Synthetic blast-beat drum layer at 180 BPM
    7. Normalise to -1 dBFS
    """
    s = _highpass(samples, 100, rate)
    s = _hard_clip(s, drive=10.0)
    s = _peaking_eq(s, rate, fc=3000, gain_db=8.0, q=1.5)
    s = _compress(s, threshold_db=-24, ratio=10.0, rate=rate)
    s = _reverb(s, rate, delay_ms=60, decay=0.15)
    drums = _metal_drums(samples.shape[1], rate, bpm=180)
    s = _mix(s, drums, gain=0.5)
    s = _normalise(s, target_db=-1.0)
    return s


# ---------------------------------------------------------------------------
# DSP primitives
# ---------------------------------------------------------------------------

def _highpass(samples: np.ndarray, fc: float, rate: int, order: int = 4) -> np.ndarray:
    sos = sp_signal.butter(order, fc, btype="high", fs=rate, output="sos")
    return np.array([sp_signal.sosfilt(sos, ch) for ch in samples])


def _lowpass(samples: np.ndarray, fc: float, rate: int, order: int = 4) -> np.ndarray:
    sos = sp_signal.butter(order, fc, btype="low", fs=rate, output="sos")
    return np.array([sp_signal.sosfilt(sos, ch) for ch in samples])


def _peaking_eq(
    samples: np.ndarray, rate: int, fc: float, gain_db: float, q: float
) -> np.ndarray:
    """Peaking EQ filter (second-order)."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * fc / rate
    alpha = math.sin(w0) / (2 * q)
    b0 =  1 + alpha * A
    b1 = -2 * math.cos(w0)
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * math.cos(w0)
    a2 =  1 - alpha / A
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0,     a1 / a0, a2 / a0])
    return np.array([sp_signal.lfilter(b, a, ch) for ch in samples])


def _high_shelf(
    samples: np.ndarray, rate: int, fc: float, gain_db: float
) -> np.ndarray:
    """High-shelf filter (first order, simplified)."""
    A  = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * fc / rate
    alpha = math.sin(w0) / (2 * math.sqrt(2))
    cosw0 = math.cos(w0)
    b0 =      A * ((A + 1) + (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cosw0)
    b2 =      A * ((A + 1) + (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha)
    a0 =           (A + 1) - (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha
    a1 =  2 *     ((A - 1) - (A + 1) * cosw0)
    a2 =           (A + 1) - (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0,     a1 / a0, a2 / a0])
    return np.array([sp_signal.lfilter(b, a, ch) for ch in samples])


def _soft_clip(samples: np.ndarray, drive: float = 4.0) -> np.ndarray:
    """Tanh soft-clipping distortion."""
    return np.tanh(samples * drive) / math.tanh(drive)


def _hard_clip(samples: np.ndarray, drive: float = 10.0) -> np.ndarray:
    """Hard clipping distortion (amplify then clip to ±1)."""
    return np.clip(samples * drive, -1.0, 1.0)


def _compress(
    samples: np.ndarray,
    threshold_db: float,
    ratio: float,
    rate: int,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
) -> np.ndarray:
    """Simple feed-forward RMS compressor."""
    threshold = 10 ** (threshold_db / 20.0)
    attack  = math.exp(-1.0 / (rate * attack_ms  / 1000.0))
    release = math.exp(-1.0 / (rate * release_ms / 1000.0))

    out = np.empty_like(samples)
    for c, ch in enumerate(samples):
        env = 0.0
        result = np.empty_like(ch)
        for i, x in enumerate(ch):
            level = abs(x)
            if level > env:
                env = attack  * env + (1 - attack)  * level
            else:
                env = release * env + (1 - release) * level
            if env > threshold:
                gain = threshold + (env - threshold) / ratio
                gain /= env if env > 1e-9 else 1e-9
            else:
                gain = 1.0
            result[i] = x * gain
        out[c] = result
    return out


def _reverb(
    samples: np.ndarray,
    rate: int,
    delay_ms: float = 40.0,
    decay: float = 0.3,
    n_taps: int = 6,
) -> np.ndarray:
    """Simple Schroeder-style comb reverb."""
    delay_samples = int(rate * delay_ms / 1000)
    out = samples.copy()
    for tap in range(1, n_taps + 1):
        tap_delay = delay_samples * tap
        d = decay ** tap
        padded = np.pad(samples, ((0, 0), (tap_delay, 0)))
        out = out + d * padded[:, : samples.shape[1]]
    # Normalise reverb tail so it doesn't overload
    peak = np.max(np.abs(out))
    if peak > 1e-9:
        out *= (np.max(np.abs(samples)) / peak)
    return out


def _normalise(samples: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    target = 10 ** (target_db / 20.0)
    peak = np.max(np.abs(samples))
    if peak > 1e-9:
        samples = samples * (target / peak)
    return samples


def _mix(
    base: np.ndarray,
    layer: np.ndarray,
    gain: float = 0.5,
) -> np.ndarray:
    """Mix *layer* into *base* with given *gain*, trimming to base length."""
    n = base.shape[1]
    l = layer[:, :n]
    if l.shape[1] < n:
        l = np.pad(l, ((0, 0), (0, n - l.shape[1])))
    return base + gain * l


# ---------------------------------------------------------------------------
# Synthetic drum generators
# ---------------------------------------------------------------------------

def _make_transient(
    rate: int, duration_ms: float = 10.0, freq: float = 200.0, decay: float = 30.0
) -> np.ndarray:
    """Synthesise a single drum hit as a decaying sine burst."""
    n = int(rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n)
    env = np.exp(-decay * t)
    hit = env * np.sin(2 * math.pi * freq * t)
    return hit


def _beat_grid(
    pattern: list[bool],
    hit: np.ndarray,
    total_frames: int,
    rate: int,
    bpm: float,
    subdivision: int = 16,
) -> np.ndarray:
    """
    Place *hit* at positions indicated by *pattern* (one step per beat subdivision).

    Parameters
    ----------
    pattern      : Boolean list whose length **must equal** *subdivision*.
                   Each ``True`` entry triggers one drum hit at that grid step.
    hit          : 1-D array containing the synthesised transient waveform.
    total_frames : Total output length in samples.
    rate         : Sample rate in Hz.
    bpm          : Tempo in beats per minute.
    subdivision  : Number of equal grid steps per bar (default 16 = sixteenth notes).
    """
    if len(pattern) != subdivision:
        raise ValueError(
            f"pattern length ({len(pattern)}) must equal subdivision ({subdivision})"
        )
    beat_frames   = int(rate * 60.0 / bpm)
    step_frames   = beat_frames // (subdivision // 4)
    grid          = np.zeros(total_frames)
    hit_len       = len(hit)
    n_bars        = max(1, total_frames // (beat_frames * 4))

    for bar in range(n_bars):
        for step, active in enumerate(pattern):
            if active:
                pos = bar * beat_frames * 4 + step * step_frames
                end = min(pos + hit_len, total_frames)
                if pos < total_frames:
                    grid[pos:end] += hit[: end - pos]
    return grid


def _to_stereo(mono: np.ndarray) -> np.ndarray:
    return np.vstack([mono, mono])


def _rock_drums(total_frames: int, rate: int, bpm: float = 120) -> np.ndarray:
    kick  = _make_transient(rate, 40,  70,  20)
    snare = _make_transient(rate, 25, 200,  40)
    hihat = _make_transient(rate, 10, 800, 100)

    # 4/4 rock pattern  (16 steps = 1 bar)
    kick_pat  = [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0]
    snare_pat = [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0]
    hihat_pat = [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0]

    drums = (
        0.9 * _beat_grid(kick_pat,  kick,  total_frames, rate, bpm)
      + 0.7 * _beat_grid(snare_pat, snare, total_frames, rate, bpm)
      + 0.4 * _beat_grid(hihat_pat, hihat, total_frames, rate, bpm)
    )
    return _to_stereo(drums)


def _rap_drums(total_frames: int, rate: int, bpm: float = 90) -> np.ndarray:
    kick  = _make_transient(rate, 60,  55,  15)
    snare = _make_transient(rate, 30, 180,  30)
    hihat = _make_transient(rate, 8,  900, 120)

    # Boom-bap pattern (16 steps)
    kick_pat  = [1,0,0,0, 0,0,1,0, 0,0,0,0, 0,1,0,0]
    snare_pat = [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0]
    hihat_pat = [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0]

    drums = (
        0.9 * _beat_grid(kick_pat,  kick,  total_frames, rate, bpm)
      + 0.6 * _beat_grid(snare_pat, snare, total_frames, rate, bpm)
      + 0.3 * _beat_grid(hihat_pat, hihat, total_frames, rate, bpm)
    )
    return _to_stereo(drums)


def _metal_drums(total_frames: int, rate: int, bpm: float = 180) -> np.ndarray:
    kick  = _make_transient(rate, 25,  80,  35)
    snare = _make_transient(rate, 15, 250,  60)
    hihat = _make_transient(rate, 5,  1000, 150)

    # Blast-beat pattern (16 steps per bar)
    kick_pat  = [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0]
    snare_pat = [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1]
    hihat_pat = [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1]

    drums = (
        0.95 * _beat_grid(kick_pat,  kick,  total_frames, rate, bpm)
       + 0.8 * _beat_grid(snare_pat, snare, total_frames, rate, bpm)
       + 0.35 * _beat_grid(hihat_pat, hihat, total_frames, rate, bpm)
    )
    return _to_stereo(drums)


# ---------------------------------------------------------------------------
# AI model hook
# ---------------------------------------------------------------------------

def _ai_hook(samples: np.ndarray, rate: int, style: str) -> np.ndarray:
    """
    Pluggable hook for AI-based genre transformation.

    Replace this function to integrate an external model such as
    MusicGen (https://github.com/facebookresearch/audiocraft) or
    Stable Audio.

    The function receives and must return ``(samples, rate)`` where
    ``samples`` is a ``(channels, frames)`` float64 NumPy array.

    Example integration (pseudo-code)::

        from audiocraft.models import MusicGen

        def _ai_hook(samples, rate, style):
            model = MusicGen.get_pretrained("facebook/musicgen-melody")
            prompt = {
                "rock":  "electric guitar, drums, rock music",
                "rap":   "hip hop beat, bass, trap",
                "metal": "heavy metal, distorted guitar, blast beat",
            }[style]
            out = model.generate_with_chroma(
                descriptions=[prompt],
                melody_wavs=torch.tensor(samples).unsqueeze(0),
                melody_sample_rate=rate,
            )
            return out[0].numpy()
    """
    return samples  # no-op: return input unchanged
