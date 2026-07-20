"""Transcribe any video(s) in a post dir with faster-whisper.

Ported from the Claude Code plugin's scripts/transcribe.py — no venv
re-exec needed here since faster-whisper is baked into this image's own
interpreter.
"""
from __future__ import annotations

from pathlib import Path


def transcribe(dest: Path, model_name: str = 'base') -> str:
    """Returns a combined transcript string (empty if no video / no speech)."""
    videos = sorted(dest.glob('*.mp4'))
    if not videos:
        return ''

    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device='cpu', compute_type='int8')

    parts = []
    for v in videos:
        segments, info = model.transcribe(str(v), vad_filter=True)
        text = ' '.join(s.text.strip() for s in segments).strip()
        if text:
            parts.append(f'[{v.name}]\n{text}')

    return '\n\n'.join(parts)
