"""Instagram Ingest Scraper — Apify Actor.

Downloads an Instagram reel/post/carousel, transcribes any video with
faster-whisper (falling back to sample frames only when a reel has no
usable audio), and pushes structured metadata + media to this run's
dataset/key-value store. An AI agent (Claude Code, Codex, ...) drives this
via the Apify MCP, then reads the media/transcript itself and writes the
extracted content to Notion via Composio — this Actor only handles the
scrape + transcribe step.
"""
from __future__ import annotations

import mimetypes
import os
import re
import tempfile
from pathlib import Path

from apify import Actor

from .downloader import DownloadError, download
from .frames import extract_frames
from .meta import build_meta
from .transcriber import transcribe

LOGIN_HINT_RE = re.compile(
    r'login required|challenge|checkpoint|rate.?limit|429|401|403|not logged in',
    re.IGNORECASE,
)


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        instagram_url = actor_input.get('instagramUrl')
        if not instagram_url:
            raise RuntimeError('instagramUrl is required.')

        whisper_model = actor_input.get('whisperModel') or 'base'

        cookies_content = actor_input.get('cookies') or os.environ.get('IG_COOKIES')
        if not cookies_content:
            raise RuntimeError(
                'No Instagram cookies available. Either pass "cookies" in the input, or '
                '(recommended) set the IG_COOKIES environment variable once in this Actor\'s '
                'Settings so future runs never need it passed again.'
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cookies_path = tmp_path / 'cookies.txt'
            cookies_path.write_text(cookies_content, encoding='utf-8')

            gallery_dl_conf = Path(__file__).resolve().parent / 'gallery-dl.conf'

            Actor.log.info(f'Downloading {instagram_url} ...')
            try:
                dest, shortcode = download(instagram_url, cookies_path, gallery_dl_conf, tmp_path)
            except DownloadError as e:
                hint = ''
                if LOGIN_HINT_RE.search(e.log_text):
                    hint = (' Instagram cookies look expired/blocked — re-export a fresh '
                             'cookies.txt from a logged-in (ideally burner) account.')
                raise RuntimeError(f'{e}{hint}') from e

            meta = build_meta(str(dest), instagram_url, shortcode)
            Actor.log.info(f"Downloaded {meta['page_count']} item(s), type={meta['type']}")

            transcript = ''
            frame_paths: list[Path] = []
            if meta['has_video']:
                Actor.log.info(f"Transcribing with faster-whisper ({whisper_model}) ...")
                transcript = transcribe(dest, whisper_model)
                if not transcript.strip():
                    Actor.log.info('No usable transcript — extracting fallback frames.')
                    frame_paths = extract_frames(dest)

            kv_store = await Actor.open_key_value_store()

            pages_out = []
            for page in meta['pages']:
                fpath = dest / page['file']
                content_type = mimetypes.guess_type(page['file'])[0] or 'application/octet-stream'
                await kv_store.set_value(page['file'], fpath.read_bytes(), content_type=content_type)
                pages_out.append({'index': page['index'], 'kind': page['kind'], 'kvsKey': page['file']})

            frames_out = []
            for fpath in frame_paths:
                # KVS record keys may not contain '/' (allowed: a-zA-Z0-9!-_.'()),
                # so namespace frames with a dash prefix, not a slash path.
                key = f'frames-{fpath.name}'
                await kv_store.set_value(key, fpath.read_bytes(), content_type='image/jpeg')
                frames_out.append({'kvsKey': key})

            item = {
                'shortcode': meta['shortcode'],
                'url': meta['url'],
                'type': meta['type'],
                'author': meta['author'],
                'caption': meta['caption'],
                'posted_at': meta['posted_at'],
                'likes': meta['likes'],
                'page_count': meta['page_count'],
                'has_video': meta['has_video'],
                'ingested_at': meta['ingested_at'],
                'pages': pages_out,
                'transcript': transcript or None,
                'frames': frames_out,
            }
            await Actor.push_data(item)
            Actor.log.info('Done.')
