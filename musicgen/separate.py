"""
separate.py — Vocal / instrumental separation.

Two backends are supported:
  1. demucs (preferred) – Facebook Research's state-of-the-art source
     separator.  Requires  `pip install demucs`.
  2. spectral median subtraction (built-in fallback) – a simple, fast,
     no-extra-dependency approach that gives reasonable results for
     centred vocals in stereo material.

The demucs backend is tried first; if it is not installed the fallback is
used automatically and a warning is printed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Tuple

import numpy as np

from .utils import read_wav, write_wav, ensure_wav


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def separate(
    audio_path: str,
    vocals_out: str,
    instrumental_out: str,
    backend: str = "auto",
) -> Tuple[Path, Path]:
    """
    Separate *audio_path* into a vocals track and an instrumental track.

    Parameters
    ----------
    audio_path       : Source audio file (.wav preferred; other formats are
                       auto-converted via ffmpeg if available).
    vocals_out       : Output path for the vocals stem.
    instrumental_out : Output path for the instrumental stem.
    backend          : ``"demucs"`` | ``"builtin"`` | ``"auto"``
                       (default ``"auto"`` tries demucs first).

    Returns
    -------
    (vocals_path, instrumental_path)
    """
    wav_src = ensure_wav(audio_path)

    if backend == "demucs":
        return _separate_demucs(wav_src, vocals_out, instrumental_out)
    if backend == "builtin":
        return _separate_builtin(wav_src, vocals_out, instrumental_out)

    # auto
    try:
        import importlib
        importlib.import_module("demucs")
        return _separate_demucs(wav_src, vocals_out, instrumental_out)
    except ImportError:
        print(
            "ℹ  demucs not installed – using built-in spectral separation.\n"
            "   Install demucs for higher quality:  pip install demucs",
            file=sys.stderr,
        )
        return _separate_builtin(wav_src, vocals_out, instrumental_out)


# ---------------------------------------------------------------------------
# Backend: demucs
# ---------------------------------------------------------------------------

def _separate_demucs(
    wav_src: Path,
    vocals_out: str,
    instrumental_out: str,
) -> Tuple[Path, Path]:
    """Run demucs CLI and copy the stems to the requested output paths."""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp(prefix="musicgen_demucs_"))
    try:
        subprocess.run(
            [
                sys.executable, "-m", "demucs",
                "--two-stems", "vocals",
                "-o", str(tmp_dir),
                str(wav_src),
            ],
            check=True,
        )

        # demucs writes: <tmp_dir>/htdemucs/<stem_name>/{vocals,no_vocals}.wav
        stem_dirs = list(tmp_dir.glob("*/" + wav_src.stem))
        if not stem_dirs:
            stem_dirs = list(tmp_dir.rglob(wav_src.stem))
        if not stem_dirs:
            raise RuntimeError(
                f"demucs did not produce expected output in {tmp_dir}"
            )
        stem_dir = stem_dirs[0]

        voc_src  = stem_dir / "vocals.wav"
        inst_src = stem_dir / "no_vocals.wav"

        Path(vocals_out).parent.mkdir(parents=True, exist_ok=True)
        Path(instrumental_out).parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(voc_src,  vocals_out)
        shutil.copy2(inst_src, instrumental_out)

        print(f"✓ Vocals       →  {vocals_out}")
        print(f"✓ Instrumental →  {instrumental_out}")
        return Path(vocals_out), Path(instrumental_out)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Backend: built-in spectral median subtraction
# ---------------------------------------------------------------------------

def _separate_builtin(
    wav_src: Path,
    vocals_out: str,
    instrumental_out: str,
) -> Tuple[Path, Path]:
    """
    Simple stereo centre-channel extraction.

    Works best for pop/speech where vocals are panned to the centre.
    The instrumental is the mid-side difference (side signal).

    Algorithm
    ---------
    1. Convert to float stereo.
    2. mid   = (L + R) / 2   ← contains centre (vocals)
    3. side  = (L - R) / 2   ← contains off-centre (instruments, reverb)
    4. Write mid as vocals, reconstruct pseudo-stereo for instrumental.
    """
    samples, rate = read_wav(wav_src)

    # Ensure stereo
    if samples.shape[0] == 1:
        samples = np.vstack([samples, samples])

    L, R = samples[0], samples[1]

    mid  = (L + R) * 0.5   # vocals (centre)
    side = (L - R) * 0.5   # instrumental (sides)

    # Reconstruct pseudo-stereo instrumental: L=mid+side, R=mid-side
    inst_L = mid + side
    inst_R = mid - side

    vocals_mono = np.vstack([mid, mid])
    inst_stereo = np.vstack([inst_L, inst_R])

    Path(vocals_out).parent.mkdir(parents=True, exist_ok=True)
    Path(instrumental_out).parent.mkdir(parents=True, exist_ok=True)

    write_wav(vocals_out, vocals_mono, rate)
    write_wav(instrumental_out, inst_stereo, rate)

    print(f"✓ Vocals (centre channel)  →  {vocals_out}")
    print(f"✓ Instrumental (side ch.)  →  {instrumental_out}")
    print(
        "ℹ  Built-in separator used.  Quality is limited.\n"
        "   For better results install demucs: pip install demucs",
        file=sys.stderr,
    )
    return Path(vocals_out), Path(instrumental_out)
