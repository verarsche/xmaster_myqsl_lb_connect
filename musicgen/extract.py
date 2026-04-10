"""
extract.py — Extract audio track from a video file using ffmpeg.
"""

from __future__ import annotations

from pathlib import Path

from .utils import check_ffmpeg, run_ffmpeg, SAMPLE_RATE


def extract_audio(
    video_path: str,
    output_path: str,
    sample_rate: int = SAMPLE_RATE,
    channels: int = 2,
) -> Path:
    """
    Extract the audio stream from *video_path* and save it to *output_path*.

    Parameters
    ----------
    video_path  : Path to the source video (mp4, mkv, avi, mov …)
    output_path : Destination file.  Extension determines the container
                  (.wav is recommended for downstream processing).
    sample_rate : Target sample-rate in Hz (default 44 100).
    channels    : Number of audio channels (1 = mono, 2 = stereo).

    Returns
    -------
    Path to the created audio file.

    Raises
    ------
    RuntimeError if ffmpeg is not available.
    FileNotFoundError if *video_path* does not exist.
    """
    check_ffmpeg()

    src = Path(video_path)
    if not src.exists():
        raise FileNotFoundError(f"Video file not found: {src}")

    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    run_ffmpeg(
        "-y",                       # overwrite output without asking
        "-i", str(src),             # input
        "-vn",                      # drop video stream
        "-ac", str(channels),       # channel count
        "-ar", str(sample_rate),    # sample rate
        "-acodec", "pcm_s16le",     # 16-bit PCM (WAV)
        str(dst),
    )

    print(f"✓ Audio extracted  →  {dst}")
    return dst
