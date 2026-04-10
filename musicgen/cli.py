"""
cli.py — Command-line interface for the musicgen toolkit.

Commands
--------
extract-audio  <video> -o <out.wav>
    Extract audio from a video file.

separate  <audio> --vocals <voc.wav> --instrumental <inst.wav>
    Split audio into vocals and instrumental stems.

genre  <audio> --style rock|rap|metal -o <out.wav>
    Apply genre-style processing to an audio file.

Usage examples
--------------
  python -m musicgen extract-audio myvideo.mp4 -o audio.wav
  python -m musicgen separate audio.wav --vocals voc.wav --instrumental inst.wav
  python -m musicgen genre audio.wav --style rock -o rock_out.wav
  python -m musicgen genre audio.wav --style rap  -o rap_out.wav
  python -m musicgen genre audio.wav --style metal -o metal_out.wav
"""

from __future__ import annotations

import argparse
import sys


def _cmd_extract(args: argparse.Namespace) -> None:
    from .extract import extract_audio
    extract_audio(
        video_path=args.video,
        output_path=args.output,
        sample_rate=args.sample_rate,
        channels=args.channels,
    )


def _cmd_separate(args: argparse.Namespace) -> None:
    from .separate import separate
    separate(
        audio_path=args.audio,
        vocals_out=args.vocals,
        instrumental_out=args.instrumental,
        backend=args.backend,
    )


def _cmd_genre(args: argparse.Namespace) -> None:
    from .genre import apply_genre
    apply_genre(
        audio_path=args.audio,
        style=args.style,
        output_path=args.output,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m musicgen",
        description="Video-to-Music-Genre toolkit",
    )
    parser.add_argument(
        "--version", action="version", version="musicgen 0.1.0"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ---- extract-audio ----
    p_extract = sub.add_parser(
        "extract-audio",
        help="Extract audio track from a video file",
    )
    p_extract.add_argument("video", help="Path to the source video file")
    p_extract.add_argument(
        "-o", "--output", required=True,
        help="Output audio file (e.g. audio.wav)",
    )
    p_extract.add_argument(
        "--sample-rate", type=int, default=44100,
        help="Target sample rate in Hz (default: 44100)",
    )
    p_extract.add_argument(
        "--channels", type=int, default=2, choices=[1, 2],
        help="Number of output channels (1=mono, 2=stereo, default: 2)",
    )
    p_extract.set_defaults(func=_cmd_extract)

    # ---- separate ----
    p_sep = sub.add_parser(
        "separate",
        help="Separate audio into vocals and instrumental",
    )
    p_sep.add_argument("audio", help="Path to the source audio file")
    p_sep.add_argument(
        "--vocals", required=True,
        help="Output path for the vocals stem",
    )
    p_sep.add_argument(
        "--instrumental", required=True,
        help="Output path for the instrumental stem",
    )
    p_sep.add_argument(
        "--backend", default="auto",
        choices=["auto", "demucs", "builtin"],
        help=(
            "Separation backend: 'auto' tries demucs first then falls back to "
            "the built-in spectral separator (default: auto)"
        ),
    )
    p_sep.set_defaults(func=_cmd_separate)

    # ---- genre ----
    p_genre = sub.add_parser(
        "genre",
        help="Apply genre-style processing (rock / rap / metal)",
    )
    p_genre.add_argument("audio", help="Path to the source audio file")
    p_genre.add_argument(
        "--style", required=True,
        choices=["rock", "rap", "metal"],
        help="Target genre style",
    )
    p_genre.add_argument(
        "-o", "--output", required=True,
        help="Output WAV file",
    )
    p_genre.set_defaults(func=_cmd_genre)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
