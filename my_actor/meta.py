"""Aggregate gallery-dl per-file metadata into a single ordered meta dict.

Ported from the Claude Code plugin's scripts/build_meta.py — same field logic,
returns a dict instead of writing meta.json to disk.
"""
from __future__ import annotations

import datetime
import glob
import json
import os

EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.mp4')


def _get(d: dict, *keys: str, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, ''):
            return v
    return default


def build_meta(dest: str, url: str, shortcode: str) -> dict:
    media = sorted(f for f in os.listdir(dest) if f.lower().endswith(EXTS))

    post: dict = {}
    raw_jsons = sorted(glob.glob(os.path.join(dest, '*.json')))
    for mf in raw_jsons:
        try:
            with open(mf, encoding='utf-8') as fh:
                d = json.load(fh)
        except Exception:
            continue
        if not post:
            post = d

    video_count = sum(1 for f in media if f.lower().endswith('.mp4'))
    if video_count and len(media) == 1:
        ptype = 'reel'
    elif len(media) > 1:
        ptype = 'carousel'
    else:
        ptype = 'post'

    pages = [
        {'index': i, 'file': f, 'kind': 'video' if f.lower().endswith('.mp4') else 'image'}
        for i, f in enumerate(media, 1)
    ]

    meta = {
        'shortcode': shortcode,
        'url': url,
        'type': ptype,
        'author': _get(post, 'username', 'owner_username', 'fullname', default=''),
        'caption': _get(post, 'description', 'caption', 'title', default=''),
        'posted_at': str(_get(post, 'date', 'post_date', default='')),
        'likes': _get(post, 'likes', 'like_count', default=None),
        'pages': pages,
        'page_count': len(pages),
        'has_video': any(p['kind'] == 'video' for p in pages),
        'ingested_at': datetime.datetime.now().astimezone().isoformat(),
    }

    for mf in raw_jsons:
        try:
            os.remove(mf)
        except OSError:
            pass

    return meta
