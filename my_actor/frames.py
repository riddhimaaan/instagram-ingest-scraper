"""Extract ~12 evenly-spread frames from each video into <dest>/frames/.

Ported from the Claude Code plugin's scripts/frames.py. Only used as the
silent-reel fallback, same as in the plugin — not run when a transcript
was already produced.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

N = 12


def extract_frames(dest: Path) -> list[Path]:
    fdir = dest / 'frames'
    fdir.mkdir(parents=True, exist_ok=True)

    for video in sorted(dest.glob('*.mp4')):
        base = video.stem
        dur = 15
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', str(video)],
            capture_output=True, text=True,
        )
        try:
            parsed = int(float(r.stdout.strip()))
            if parsed >= 1:
                dur = parsed
        except (ValueError, TypeError):
            pass

        rate = f'{N}/{dur}'
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(video), '-vf', f'fps={rate},scale=480:-1',
             str(fdir / f'{base}_%03d.jpg')],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    return sorted(fdir.glob('*.jpg'))
