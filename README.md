# Instagram Ingest Scraper

An [Apify Actor](https://apify.com/actors) that downloads an Instagram reel, post, or
carousel, transcribes any video with [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
and returns structured metadata + media so an AI agent can extract the real text and file it
somewhere (Notion, in the companion project below).

This Actor only does the **scrape + transcribe** step — it does not interpret content or write
anywhere itself. It's built to be driven by an AI agent over the
[Apify MCP server](https://docs.apify.com/platform/integrations/mcp), typically the
[`instagram-ingest-apify`](https://github.com/riddhimaaan/instagram-ingest-apify) Claude Code
plugin, though nothing here is Claude-specific — any MCP client (or the plain Apify API) can
call it.

## Input

| Field | Required | Notes |
|---|---|---|
| `instagramUrl` | yes | A `/reel/`, `/reels/`, `/p/`, or `/tv/` URL. |
| `cookies` | no | Netscape-format `cookies.txt` content for a logged-in Instagram account. Falls back to the `IG_COOKIES` Actor environment variable if omitted — set that once in Actor Settings to avoid passing cookies on every call. |
| `whisperModel` | no | `tiny` / `base` (default) / `small` / `medium`. |

## Output

One dataset item per run:

```json
{
  "shortcode": "Da5lLU3y3h9",
  "url": "https://www.instagram.com/reel/Da5lLU3y3h9/",
  "type": "reel",
  "author": "someuser",
  "caption": "...",
  "posted_at": "2026-07-17 15:54:02",
  "likes": 705,
  "page_count": 1,
  "has_video": true,
  "transcript": "[01.mp4]\n...",
  "pages": [{"index": 1, "kind": "video", "kvsKey": "01.mp4"}],
  "frames": []
}
```

- `transcript` is a plain string (or `null`) — already usable as-is, no file fetch needed.
- Each `pages`/`frames` entry's `kvsKey` points to the actual media file in this run's
  Key-Value Store. Fetch it with `get-key-value-store-record` (Apify MCP) or the REST API —
  either way you get back a signed URL good for a direct, unauthenticated download.
- `frames` is only populated when `has_video` is true and no usable transcript was produced
  (silent reel fallback) — sampled frames for a caller to read text off manually.

## Why cookies are needed

Instagram blocks anonymous scraping. Export cookies from a logged-in (ideally burner) account
via the [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
browser extension → **Export as Netscape**. Either pass that content as the `cookies` input on
each call, or set it once as the `IG_COOKIES` environment variable in this Actor's own
Settings (Apify Console) if you're running your own deployment of it.

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # .venv\Scripts\pip on Windows
echo '{"instagramUrl": "https://www.instagram.com/reel/XXXXXXXXX/"}' > storage/key_value_stores/default/INPUT.json
IG_COOKIES="$(cat /path/to/cookies.txt)" .venv/bin/python -m my_actor
```

Deploy with the [Apify CLI](https://docs.apify.com/cli):
```bash
apify login
apify push
```

## License

MIT — see [`LICENSE`](LICENSE).
