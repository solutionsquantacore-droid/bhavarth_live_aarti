#!/usr/bin/env python3
"""
Fetch YouTube videos from specified channels and output a JSON array of:
[
  {
    "title_hindi": "...",
    "title_english": "...",
    "youtube_url": "https://www.youtube.com/watch?v=..."
  }
]
"""

import os
import re
import json
import time
import ssl
import certifi
import yt_dlp
from deep_translator import GoogleTranslator, MyMemoryTranslator

# Ensure SSL certificates work properly across macOS, Linux, and Windows
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
try:
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except Exception:
    pass

# Target channels
CHANNELS = [
    "@GokulBhawanAyodhya",
    "@shree_radhe603"
]

OUTPUT_FILE = os.getenv("OUTPUT_FILE", "videos.json")
MAX_VIDEOS_PER_CHANNEL = int(os.getenv("MAX_VIDEOS_PER_CHANNEL", "20"))
MAX_VIDEOS_PER_CHANNEL = int(os.getenv("MAX_VIDEOS_PER_CHANNEL", "0")) # 0 = no limit, fetches all videos
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Primary & Fallback Translators
google_to_en = GoogleTranslator(source='auto', target='en')
google_to_hi = GoogleTranslator(source='auto', target='hi')
mymemory_to_en = MyMemoryTranslator(source='hi-IN', target='en-GB')
mymemory_to_hi = MyMemoryTranslator(source='en-GB', target='hi-IN')


def has_devanagari(text: str) -> bool:
    """Returns True if text contains Hindi (Devanagari) characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))


def has_latin(text: str) -> bool:
    """Returns True if text contains English (Latin) characters."""
    return bool(re.search(r'[a-zA-Z]', text))


def clean_title(title: str) -> str:
    """Removes hashtags, emojis, and extraneous trailing punctuation."""
    # Remove hashtags
    cleaned = re.sub(r'#\S+', '', title)
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' |-\t\n')
    return cleaned


def split_bilingual_title(title: str):
    """
    Checks if title already contains separate Hindi and English segments
    (e.g., 'अजामिल उद्धार | Ajamila's Liberation').
    """
    for sep in ['|', '//', '—', ' - ']:
        if sep in title:
            parts = [p.strip() for p in title.split(sep) if p.strip()]
            hindi_parts = [p for p in parts if has_devanagari(p)]
            english_parts = [p for p in parts if has_latin(p) and not has_devanagari(p)]
            if hindi_parts and english_parts:
                return " ".join(hindi_parts), " ".join(english_parts)
    return None, None


def translate_with_gemini(text: str, target_lang: str) -> str:
    """Optional spiritual translation using Gemini API if GEMINI_API_KEY is provided."""
    if not GEMINI_API_KEY:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (
            f"Translate the following spiritual YouTube video title into natural, respectful {target_lang}. "
            f"Preserve devotional terminology accurately (e.g. Katha, Lila, Bhakti, Naam Jap, Liberation). "
            f"Return ONLY the translated title text without quotes or explanations.\n\n"
            f"Title: {text}"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip().strip('"').strip("'")
    except Exception as e:
        print(f"    [Gemini API] Note ({e}), using fallback translator.")
    return ""


def translate_text(text: str, target_lang: str) -> str:
    """
    Translates text with automatic multi-provider fallback:
    1. Gemini API (if key provided)
    2. GoogleTranslator
    3. MyMemoryTranslator
    """
    # 1. Gemini
    gemini_result = translate_with_gemini(text, target_lang)
    if gemini_result:
        return gemini_result

    # 2. GoogleTranslator
    try:
        if target_lang == "English":
            return google_to_en.translate(text)
        else:
            return google_to_hi.translate(text)
    except Exception:
        pass

    # 3. MyMemoryTranslator fallback
    try:
        if target_lang == "English":
            return mymemory_to_en.translate(text)
        else:
            return mymemory_to_hi.translate(text)
    except Exception as e:
        print(f"    [MyMemoryTranslator fallback error] {e}")

    # Fallback to original text if all failed
    return text


def get_translations(raw_title: str):
    """
    Extracts or translates title into both Hindi and English.
    """
    title = clean_title(raw_title)

    # Check for existing bilingual segments
    hi_part, en_part = split_bilingual_title(title)
    if hi_part and en_part:
        return hi_part, en_part

    # If primarily Hindi
    if has_devanagari(title):
        title_hindi = title
        title_english = translate_text(title, "English")
        return title_hindi, title_english

    # If primarily English
    title_english = title
    title_hindi = translate_text(title, "Hindi")
    return title_hindi, title_english


def fetch_channel_videos(channel_handle: str, max_videos: int = 20):
def fetch_channel_videos(channel_handle: str, max_videos: int = 0):
    """
    Fetches videos from a channel's /videos tab using yt-dlp.
    Passing max_videos=0 fetches all available videos without limit.
    """
    handle_clean = channel_handle.strip().lstrip('/')
    url = f"https://www.youtube.com/{handle_clean}/videos"
    print(f"\nScanning channel: {url}...")
    limit_msg = f"latest {max_videos}" if max_videos > 0 else "all available"
    print(f"\nScanning channel ({limit_msg} videos): {url}...")

    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        'playlistend': max_videos if max_videos > 0 else None,
    }

    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if not info:
                print(f"  Warning: No metadata found for {channel_handle}")
                return []
            
            entries = info.get('entries', [])
            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get('id')
                title = entry.get('title')
                if not video_id or not title:
                    continue

                if title in ['[Private video]', '[Deleted video]']:
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"
                videos.append({
                    "id": video_id,
                    "title": title,
                    "youtube_url": video_url
                })
        except Exception as e:
            print(f"  Error accessing channel {channel_handle}: {e}")

    print(f"  Found {len(videos)} videos from {channel_handle}")
    return videos


def main():
    existing_items = []
    known_urls = set()

    # Load existing JSON if present
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
                if isinstance(existing_items, list):
                    for item in existing_items:
                        if isinstance(item, dict) and "youtube_url" in item:
                            known_urls.add(item["youtube_url"])
            print(f"Loaded {len(existing_items)} existing videos from '{OUTPUT_FILE}'.")
        except Exception as e:
            print(f"Could not parse existing '{OUTPUT_FILE}': {e}")
            existing_items = []

    new_entries = []

    for channel in CHANNELS:
        videos = fetch_channel_videos(channel, MAX_VIDEOS_PER_CHANNEL)
        for vid in videos:
            url = vid["youtube_url"]
            if url in known_urls:
                continue

            raw_title = vid["title"]
            print(f"  [New Video] {raw_title}")
            title_hindi, title_english = get_translations(raw_title)

            entry = {
                "title_hindi": title_hindi,
                "title_english": title_english,
                "youtube_url": url
            }
            new_entries.append(entry)
            known_urls.add(url)
            print(f"    -> Hindi:   {title_hindi}")
            print(f"    -> English: {title_english}")
            time.sleep(0.5)

            # Save progress every 10 videos so no work is lost on large runs
            if len(new_entries) % 10 == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_entries + existing_items, f, ensure_ascii=False, indent=2)

            time.sleep(0.3)

    if not new_entries:
        print("\nAll videos are up to date. No changes needed.")
        return

    print(f"\nAdding {len(new_entries)} new entries.")
    # Place newest first, followed by previous items
    updated_data = new_entries + existing_items

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully wrote {len(updated_data)} total videos to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()
