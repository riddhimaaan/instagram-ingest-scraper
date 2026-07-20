"""Download an Instagram reel/post/carousel into a local dir as 01/02/03...

Ported from the Claude Code plugin's scripts/download.py, adapted to take an
explicit cookies file path (written per-run from Actor input/env) instead of
a fixed local path, and to run against a temp dest dir instead of ~/ig_ingest.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

MEDIA_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.mp4')


class DownloadError(Exception):
    def __init__(self, message: str, log_text: str = ''):
        super().__init__(message)
        self.log_text = log_text


def extract_shortcode(url: str) -> str:
    m = re.search(r'/(reel|reels|p|tv)/([A-Za-z0-9_-]+)', url)
    return m.group(2) if m else f'ig_{int(time.time())}'


def download(url: str, cookies_path: Path, gallery_dl_conf: Path, work_dir: Path) -> tuple[Path, str]:
    """Downloads media for `url` into a fresh subdir of work_dir. Returns (dest, shortcode)."""
    shortcode = extract_shortcode(url)
    dest = work_dir / shortcode
    dest.mkdir(parents=True, exist_ok=True)
    log = dest / '.gdl.log'

    with open(log, 'wb') as fh:
        subprocess.run(
            [
                sys.executable, '-m', 'gallery_dl',
                '--config', str(gallery_dl_conf),
                '--cookies', str(cookies_path),
                '-D', str(dest),
                '-f', '{num:>02}.{extension}',
                '--write-metadata',
                url,
            ],
            stdout=fh, stderr=subprocess.STDOUT,
        )

    media = [p for p in dest.iterdir() if p.suffix.lower() in MEDIA_EXTS]

    if not media:
        with open(log, 'ab') as fh:
            subprocess.run(
                [sys.executable, '-m', 'yt_dlp', '--cookies', str(cookies_path),
                 '-o', str(dest / '01.%(ext)s'), url],
                stdout=fh, stderr=subprocess.STDOUT,
            )
        media = [p for p in dest.iterdir() if p.suffix.lower() in ('.mp4', '.jpg')]

    if not media:
        log_text = log.read_text(encoding='utf-8', errors='ignore') if log.exists() else ''
        raise DownloadError(f'No media downloaded for {url}. See log.', log_text=log_text)

    return dest, shortcode
