#!/usr/bin/env python3
"""
Fetches YouTube videos about "Naam Ki Mahima" (Sant Vani) and outputs
naam_mahima_sant_vani.json matching the Bhavarth Android app's NaamVideo schema:
  {
    "title_hindi": "...",
    "title_english": "...",
    "youtube_url": "https://www.youtube.com/watch?v=...",
    "speaker": "..."
  }

Primary mode: YouTube Data API v3 (set YOUTUBE_API_KEY environment variable).
Fallback mode: yt-dlp ytsearch (no API key required).
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "naam_mahima_sant_vani.json"
MAX_VIDEOS = 100
PER_QUERY_RESULTS = 15

SEARCH_QUERIES = [
    "ram naam ki mahima",
    "radha naam ki mahima",
    "krishna naam jap mahima",
    "hari naam sankirtan mahima",
    "naam jap mahima premanand ji maharaj",
    "naam mahima rajendra das ji maharaj",
    "naam mahima sanatan sant vani",
    "shiv naam ki mahima",
    "naam jap ki mahima swami ramsukhdas",
]

# Keywords to recognize well-known speakers from title/channel
SPEAKER_KEYWORDS = {
    "premanand": "पूज्य प्रेमानंद जी महाराज",
    "प्रेमानंद": "पूज्य प्रेमानंद जी महाराज",
    "bhajan marg": "पूज्य प्रेमानंद जी महाराज",
    "sadhan path": "पूज्य प्रेमानंद जी महाराज",
    "rajendra das": "पूज्य राजेंद्र दास जी महाराज",
    "राजेंद्र दास": "पूज्य राजेंद्र दास जी महाराज",
    "morari bapu": "पूज्य मोरारी बापू",
    "मोरारी बापू": "पूज्य मोरारी बापू",
    "pradeep mishra": "पंडित प्रदीप मिश्रा जी",
    "प्रदीप मिश्रा": "पंडित प्रदीप मिश्रा जी",
    "ramsukhdas": "स्वामी रामसुखदास जी महाराज",
    "रामसुखदास": "स्वामी रामसुखदास जी महाराज",
    "avdheshanand": "स्वामी अवधेशानंद गिरि जी",
    "अवधेशानंद": "स्वामी अवधेशानंद गिरि जी",
    "aniruddhacharya": "पूज्य अनिरुद्धाचार्य जी महाराज",
    "अनिरुद्धाचार्य": "पूज्य अनिरुद्धाचार्य जी महाराज",
    "bageshwar": "पंडित धीरेंद्र कृष्ण शास्त्री जी",
    "dhirendra": "पंडित धीरेंद्र कृष्ण शास्त्री जी",
    "indresh": "पूज्य इंद्रेश उपाध्याय जी",
    "इंद्रेश": "पूज्य इंद्रेश उपाध्याय जी",
    "devkinandan": "पूज्य देवकीनंदन ठाकुर जी",
    "देवकीनंदन": "पूज्य देवकीनंदन ठाकुर जी",
    "jaya kishori": "जया किशोरी जी",
    "जया किशोरी": "जया किशोरी जी",
    "rajan ji": "पूज्य राजन जी महाराज",
    "राजन जी": "पूज्य राजन जी महाराज",
}

BLOCKED_KEYWORDS = [
    "#shorts",
    "status",
    "whatsapp status",
    "ringtone",
    "dj remix",
    "lofi",
    # Non-Hindu religious terms to keep Sant Vani strictly Hindu / Sanatan Dharma
    "jesus",
    "christ",
    "christian",
    "bible",
    "gospel",
    "church",
    "pastor",
    "yeshu",
    "masih",
    "यीशु",
    "ईसा",
    "मसीह",
    "बाइबल",
    "चर्च",
    "jain",
    "jainism",
    "tirthankar",
    "navkar",
    "namokar",
    "जैन",
    "तीर्थंकर",
    "नवकार",
    "णमोकार",
    "पर्युषण",
    "gurbani",
    "waheguru",
    "sikh",
    "गुरबाणी",
    "वाहेगुरु",
    "allah",
    "quran",
    "islamic",
    "अल्लाह",
    "कुरान",
]


def has_devanagari(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


def clean_title(title: str) -> str:
    # Remove common hashtags/clickbait brackets while keeping core title readable
    cleaned = re.sub(r"#\S+", "", title).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned or title.strip()


def translate_mymemory(text: str, source_lang: str, target_lang: str) -> str:
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:450], "langpair": f"{source_lang}|{target_lang}"},
            timeout=10,
        )
        resp.raise_for_status()
        translated = resp.json().get("responseData", {}).get("translatedText", "").strip()
        if translated and "MYMEMORY WARNING" not in translated.upper():
            return translated
    except Exception:
        pass
    return text


def translate_batch_safe(texts: List[str], target_lang: str, chunk_size: int = 12) -> List[str]:
    """Translate a list of strings using Google chunking with MyMemory fallback."""
    if not texts:
        return texts

    results: List[str] = []
    endpoint = "https://translate.googleapis.com/translate_a/single"
    source_lang = "hi" if target_lang == "en" else "en"
    google_blocked = False

    for i in range(0, len(texts), chunk_size):
        chunk = [t.replace("\n", " ").strip() for t in texts[i : i + chunk_size]]
        translated_lines = None

        if not google_blocked:
            joined = "\n".join(chunk)
            try:
                resp = requests.get(
                    endpoint,
                    params={
                        "client": "gtx",
                        "sl": "auto",
                        "tl": target_lang,
                        "dt": "t",
                        "q": joined,
                    },
                    timeout=15,
                )
                if resp.status_code == 429:
                    print(f"[translate:{target_lang}] Google 429; switching to MyMemory fallback...")
                    google_blocked = True
                else:
                    resp.raise_for_status()
                    data = resp.json()
                    full_translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
                    lines = [line.strip() for line in full_translated.split("\n") if line.strip()]
                    if len(lines) == len(chunk):
                        translated_lines = lines
            except Exception as exc:
                print(f"[translate:{target_lang}] Google chunk failed ({exc}); using MyMemory...")

        if translated_lines:
            results.extend(translated_lines)
        else:
            for orig in chunk:
                results.append(translate_mymemory(orig, source_lang, target_lang))
                time.sleep(0.1)

        if i + chunk_size < len(texts):
            time.sleep(0.3)

    return results


def detect_speaker(title: str, channel_name: Optional[str]) -> str:
    combined = f"{title} {channel_name or ''}".lower()
    for keyword, speaker_name in SPEAKER_KEYWORDS.items():
        if keyword in combined:
            return speaker_name
    if channel_name and channel_name.strip():
        return channel_name.strip()
    return "संत वाणी"


def is_valid_video(title: str, channel_name: Optional[str] = None) -> bool:
    combined = f"{title} {channel_name or ''}".lower()
    return not any(bad in combined for bad in BLOCKED_KEYWORDS)


def build_entry(video_id: str, raw_title: str, channel_name: Optional[str]) -> Dict[str, str]:
    title = clean_title(raw_title)
    return {
        "title_hindi": title,
        "title_english": title,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "speaker": detect_speaker(title, channel_name),
    }


def populate_translations(entries: List[Dict[str, str]]) -> None:
    """Batch-translate entries where title_hindi and title_english are still identical."""
    need_en_indices: List[int] = []
    need_en_texts: List[str] = []
    need_hi_indices: List[int] = []
    need_hi_texts: List[str] = []

    for idx, item in enumerate(entries):
        hi = item.get("title_hindi", "").strip()
        en = item.get("title_english", "").strip()
        if hi and en and hi != en:
            continue
        base_title = hi or en
        if not base_title:
            continue
        if has_devanagari(base_title):
            need_en_indices.append(idx)
            need_en_texts.append(base_title)
        else:
            need_hi_indices.append(idx)
            need_hi_texts.append(base_title)

    if need_en_texts:
        print(f"Translating {len(need_en_texts)} Hindi titles to English...")
        en_results = translate_batch_safe(need_en_texts, "en")
        for idx, translated in zip(need_en_indices, en_results):
            entries[idx]["title_english"] = translated

    if need_hi_texts:
        print(f"Translating {len(need_hi_texts)} English titles to Hindi...")
        hi_results = translate_batch_safe(need_hi_texts, "hi")
        for idx, translated in zip(need_hi_indices, hi_results):
            entries[idx]["title_hindi"] = translated


def fetch_via_youtube_api(api_key: str) -> List[Dict[str, str]]:
    endpoint = "https://www.googleapis.com/youtube/v3/search"
    results: List[Dict[str, str]] = []
    seen_ids = set()

    for query in SEARCH_QUERIES:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoEmbeddable": "true",
            "videoDuration": "medium",  # 4-20 min discourses; avoids Shorts
            "relevanceLanguage": "hi",
            "maxResults": PER_QUERY_RESULTS,
            "key": api_key,
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception as exc:
            print(f"[API] Query '{query}' failed: {exc}")
            continue

        for item in items:
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            raw_title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")

            if not video_id or video_id in seen_ids or not is_valid_video(raw_title, channel):
                continue

            seen_ids.add(video_id)
            results.append(build_entry(video_id, raw_title, channel))

    return results


def fetch_via_yt_dlp() -> List[Dict[str, str]]:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed and YOUTUBE_API_KEY is not set.")

    results: List[Dict[str, str]] = []
    seen_ids = set()

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in SEARCH_QUERIES:
            try:
                info = ydl.extract_info(f"ytsearch{PER_QUERY_RESULTS}:{query}", download=False)
                entries = info.get("entries", []) if info else []
            except Exception as exc:
                print(f"[yt-dlp] Query '{query}' failed: {exc}")
                continue

            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get("id")
                raw_title = entry.get("title", "")
                channel = entry.get("channel") or entry.get("uploader") or ""
                duration = entry.get("duration")

                # Skip Shorts (< 90 seconds) when duration is available
                if duration is not None and duration < 90:
                    continue
                if not video_id or video_id in seen_ids or not is_valid_video(raw_title, channel):
                    continue

                seen_ids.add(video_id)
                results.append(build_entry(video_id, raw_title, channel))

    return results


def load_existing_videos() -> List[Dict[str, str]]:
    if not OUTPUT_FILE.exists():
        return []
    try:
        with OUTPUT_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def main() -> None:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if api_key:
        print("Fetching videos using YouTube Data API v3...")
        fetched = fetch_via_youtube_api(api_key)
    else:
        print("YOUTUBE_API_KEY not set; fetching videos using yt-dlp fallback...")
        fetched = fetch_via_yt_dlp()

    existing = load_existing_videos()
    merged: List[Dict[str, str]] = []
    seen_urls = set()

    for item in fetched + existing:
        url = item.get("youtube_url", "").strip()
        if not url or url in seen_urls:
            continue
        if not is_valid_video(
            f"{item.get('title_hindi', '')} {item.get('title_english', '')}",
            item.get("speaker"),
        ):
            continue
        seen_urls.add(url)
        merged.append(item)
        if len(merged) >= MAX_VIDEOS:
            break

    if not merged:
        raise RuntimeError("No videos fetched and no existing videos available. Aborting write.")

    populate_translations(merged)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Successfully wrote {len(merged)} videos to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
