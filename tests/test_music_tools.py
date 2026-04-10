"""
tests/test_music_tools.py — smoke tests for the musicgen toolkit.

These tests do NOT require a real video or audio file; they synthesise
minimal WAV data on the fly and exercise each processing stage.
"""

from __future__ import annotations

import math
import os
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

# Make sure the repo root is on sys.path regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100


def _sine_wav(path: str, duration_s: float = 1.0, freq: float = 440.0) -> Path:
    """Write a short stereo 440 Hz sine-wave WAV file for testing."""
    n = int(SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    wave_data = (np.sin(2 * math.pi * freq * t) * 0.5).astype(np.float64)
    pcm = (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm])

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo.tobytes())
    return p


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------

class TestUtils:
    def test_read_write_roundtrip(self, tmp_path):
        from musicgen.utils import read_wav, write_wav

        src = _sine_wav(str(tmp_path / "in.wav"))
        samples, rate = read_wav(src)

        assert rate == SAMPLE_RATE
        assert samples.ndim == 2
        assert samples.shape[0] == 2     # stereo
        assert samples.shape[1] == SAMPLE_RATE  # 1 second

        dst = tmp_path / "out.wav"
        write_wav(dst, samples, rate)
        assert dst.exists()

        samples2, rate2 = read_wav(dst)
        assert rate2 == rate
        # Values should be very close after 16-bit round-trip
        assert np.max(np.abs(samples - samples2)) < 1e-3

    def test_is_wav(self, tmp_path):
        from musicgen.utils import is_wav

        assert is_wav("audio.wav") is True
        assert is_wav("video.mp4") is False
        assert is_wav("track.WAV") is True

    def test_check_ffmpeg_raises_when_missing(self, monkeypatch):
        """check_ffmpeg() should raise RuntimeError when ffmpeg is absent."""
        import shutil
        from musicgen import utils

        monkeypatch.setattr(shutil, "which", lambda _: None)
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            utils.check_ffmpeg()


# ---------------------------------------------------------------------------
# CLI argument parsing (no side-effects)
# ---------------------------------------------------------------------------

class TestCLIParsing:
    def _parse(self, argv):
        from musicgen.cli import build_parser
        return build_parser().parse_args(argv)

    def test_extract_audio_args(self):
        args = self._parse(["extract-audio", "myvideo.mp4", "-o", "audio.wav"])
        assert args.command == "extract-audio"
        assert args.video == "myvideo.mp4"
        assert args.output == "audio.wav"
        assert args.sample_rate == 44100
        assert args.channels == 2

    def test_separate_args(self):
        args = self._parse([
            "separate", "audio.wav",
            "--vocals", "voc.wav",
            "--instrumental", "inst.wav",
            "--backend", "builtin",
        ])
        assert args.command == "separate"
        assert args.backend == "builtin"

    def test_genre_args_rock(self):
        args = self._parse(["genre", "audio.wav", "--style", "rock", "-o", "out.wav"])
        assert args.style == "rock"

    def test_genre_args_invalid_style(self):
        from musicgen.cli import build_parser
        import argparse
        with pytest.raises(SystemExit):
            build_parser().parse_args(["genre", "a.wav", "--style", "jazz", "-o", "o.wav"])


# ---------------------------------------------------------------------------
# extract – no video, tests file-not-found error
# ---------------------------------------------------------------------------

class TestExtract:
    def test_missing_video_raises(self, tmp_path):
        import shutil
        from musicgen.extract import extract_audio

        if shutil.which("ffmpeg") is None:
            pytest.skip("ffmpeg not installed – skipping extract test")

        with pytest.raises(FileNotFoundError):
            extract_audio(
                str(tmp_path / "nonexistent.mp4"),
                str(tmp_path / "out.wav"),
            )


# ---------------------------------------------------------------------------
# separate – built-in backend (no demucs needed)
# ---------------------------------------------------------------------------

class TestSeparateBuiltin:
    def test_separate_produces_two_files(self, tmp_path):
        from musicgen.separate import separate

        src   = _sine_wav(str(tmp_path / "src.wav"))
        voc   = str(tmp_path / "voc.wav")
        inst  = str(tmp_path / "inst.wav")

        voc_p, inst_p = separate(str(src), voc, inst, backend="builtin")

        assert voc_p.exists(),  "vocals file not created"
        assert inst_p.exists(), "instrumental file not created"

    def test_separate_mono_input(self, tmp_path):
        """Built-in separator should handle mono input without crashing."""
        from musicgen.utils import write_wav
        from musicgen.separate import separate

        # Create a mono WAV
        n = SAMPLE_RATE
        t = np.linspace(0, 1.0, n, endpoint=False)
        mono = np.sin(2 * math.pi * 440 * t).reshape(1, -1)
        src  = tmp_path / "mono.wav"
        write_wav(src, mono, SAMPLE_RATE)

        voc  = str(tmp_path / "voc.wav")
        inst = str(tmp_path / "inst.wav")
        separate(str(src), voc, inst, backend="builtin")
        assert Path(voc).exists()
        assert Path(inst).exists()


# ---------------------------------------------------------------------------
# genre – DSP pipeline
# ---------------------------------------------------------------------------

class TestGenre:
    @pytest.mark.parametrize("style", ["rock", "rap", "metal"])
    def test_genre_produces_output(self, style, tmp_path):
        from musicgen.genre import apply_genre

        src = _sine_wav(str(tmp_path / "src.wav"), duration_s=2.0)
        dst = str(tmp_path / f"{style}.wav")

        result = apply_genre(str(src), style, dst)

        assert result.exists(), f"{style} output file not created"
        assert result.stat().st_size > 0

    def test_genre_unknown_style_raises(self, tmp_path):
        from musicgen.genre import apply_genre

        src = _sine_wav(str(tmp_path / "src.wav"))
        with pytest.raises(ValueError, match="Unknown style"):
            apply_genre(str(src), "jazz", str(tmp_path / "out.wav"))

    def test_genre_outputs_are_distinct(self, tmp_path):
        """Rock, rap, and metal outputs should be meaningfully different."""
        from musicgen.genre import apply_genre
        from musicgen.utils import read_wav

        src = _sine_wav(str(tmp_path / "src.wav"), duration_s=2.0)

        outputs = {}
        for style in ("rock", "rap", "metal"):
            dst = str(tmp_path / f"{style}.wav")
            apply_genre(str(src), style, dst)
            samples, _ = read_wav(dst)
            outputs[style] = samples

        def rms(s):
            return float(np.sqrt(np.mean(s ** 2)))

        # At least two of three outputs should differ measurably
        values = [rms(outputs[s]) for s in ("rock", "rap", "metal")]
        # They should not all be identical
        assert len(set(round(v, 5) for v in values)) > 1, (
            "All genre outputs have identical RMS – processing had no effect"
        )

    @pytest.mark.parametrize("style", ["rock", "rap", "metal"])
    def test_genre_no_clipping(self, style, tmp_path):
        """Output samples must stay within [-1, 1]."""
        from musicgen.genre import apply_genre
        from musicgen.utils import read_wav

        src = _sine_wav(str(tmp_path / "src.wav"), duration_s=1.0)
        dst = str(tmp_path / f"{style}_clip.wav")
        apply_genre(str(src), style, dst)
        samples, _ = read_wav(dst)
        assert np.max(np.abs(samples)) <= 1.0 + 1e-4


# ---------------------------------------------------------------------------
# DSP primitives (unit tests)
# ---------------------------------------------------------------------------

class TestDSPPrimitives:
    def _stereo(self, duration_s: float = 0.5, freq: float = 440.0) -> tuple:
        n = int(SAMPLE_RATE * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        mono = 0.5 * np.sin(2 * math.pi * freq * t)
        return np.vstack([mono, mono]), SAMPLE_RATE

    def test_soft_clip_bounded(self):
        from musicgen.genre import _soft_clip

        samples, _ = self._stereo()
        out = _soft_clip(samples, drive=4.0)
        assert np.max(np.abs(out)) <= 1.0 + 1e-9

    def test_hard_clip_bounded(self):
        from musicgen.genre import _hard_clip

        samples, _ = self._stereo()
        out = _hard_clip(samples, drive=10.0)
        assert np.max(np.abs(out)) <= 1.0

    def test_normalise(self):
        from musicgen.genre import _normalise

        samples, _ = self._stereo()
        samples *= 0.1   # make quiet
        out = _normalise(samples, target_db=-1.0)
        target = 10 ** (-1.0 / 20.0)
        assert abs(np.max(np.abs(out)) - target) < 1e-6

    def test_compress_reduces_peak(self):
        from musicgen.genre import _compress

        samples, rate = self._stereo()
        # Amplify to make peaks stand out
        loud = samples * 2.0
        out  = _compress(loud, threshold_db=-6, ratio=4.0, rate=rate)
        assert np.max(np.abs(out)) < np.max(np.abs(loud))
