import urllib.request
import re
import json
import os
import xml.etree.ElementTree as ET

JSON_PATH = os.path.join(os.path.dirname(__file__), "live_aarti.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    'Cookie': 'SOCS=CAI; CONSENT=YES+cb.20230531-04-p0.en+FX+999; PREF=hl=en&gl=IN;',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def get_video_title(vid):
    """Uses YouTube oEmbed endpoint for reliable title extraction without consent wall issues."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': HEADERS['User-Agent']})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('title', '')
    except Exception:
        # Fallback to HTML title extraction
        try:
            url = f"https://www.youtube.com/watch?v={vid}"
            req = urllib.request.Request(url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=8).read().decode('utf-8')
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"Error fetching title for {vid}: {e}")
    return ""

def get_live_video_ids_from_rss(channel_id):
    """Fetches latest video IDs via YouTube RSS feed (never blocked by consent wall)."""
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        req = urllib.request.Request(url, headers={'User-Agent': HEADERS['User-Agent']})
        xml_data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        vids = []
        for entry in root.findall('atom:entry', ns):
            vid_elem = entry.find('yt:videoId', ns)
            if vid_elem is not None and vid_elem.text:
                vids.append(vid_elem.text)
        return vids
    except Exception as e:
        print(f"Error fetching RSS for {channel_id}: {e}")
    return []

def get_live_video_ids_from_channel(channel_handle):
    try:
        url = f"https://www.youtube.com/{channel_handle}/streams"
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        return list(dict.fromkeys(matches))
    except Exception as e:
        print(f"Error fetching channel streams for {channel_handle}: {e}")
    return []

def get_live_video_ids_from_search(search_query):
    try:
        url = f"https://www.youtube.com/results?search_query={search_query}&sp=EgJAAQ%253D%253D"
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        return list(dict.fromkeys(matches))
    except Exception as e:
        print(f"Error fetching for {search_query}: {e}")
    return []

QUERIES = {
    "1": {
        "primary": {
            "keywords": ["vaishno", "वैष्णो", "aarti", "आरती", "bhawan", "भवन"],
            "sources": [
                {"type": "rss", "channel_id": "UCziZy6xAlJWPzgIY4duxAeQ"},
                {"type": "channel", "handle": "@MHONESHRADDHA"},
                {"type": "search", "query": "mh+one+shraddha+vaishno+devi+live+darshan"}
            ]
        },
        "secondary": {
            "keywords": ["vaishno", "वैष्णो"],
            "sources": [
                {"type": "rss", "channel_id": "UC3oQ1986eLZ4MhyPBiu54PA"},
                {"type": "channel", "handle": "@SonotekBhakti"},
                {"type": "channel", "handle": "@Sonotek"},
                {"type": "search", "query": "vaishno+devi+live+darshan"}
            ]
        }
    },
    "2": {
        "primary": {
            "keywords": ["mahakal", "महाकाल", "ujjain", "उज्जैन"],
            "sources": [
                {"type": "channel", "handle": "@mahakaleshwar_live"},
                {"type": "search", "query": "mahakaleshwar+live+darshan"}
            ]
        }
    },
    "3": {
        "primary": {
            "keywords": ["banke", "bihari", "बांके", "बिहारी", "krishna", "vrindavan"],
            "sources": [
                {"type": "search", "query": "banke+bihari+live+darshan"}
            ]
        }
    }
}

def fetch_first_valid_video(config, checked_vids):
    if not config:
        return None
        
    keywords = config.get("keywords", [])
    sources = config.get("sources", [])
    
    for source in sources:
        fetched_vids = []
        if source['type'] == 'rss':
            fetched_vids = get_live_video_ids_from_rss(source['channel_id'])
        elif source['type'] == 'channel':
            fetched_vids = get_live_video_ids_from_channel(source['handle'])
        elif source['type'] == 'search':
            fetched_vids = get_live_video_ids_from_search(source['query'])
            
        for vid in fetched_vids:
            if vid and vid not in checked_vids:
                checked_vids.add(vid)
                title = get_video_title(vid)
                if not title:
                    continue
                title_lower = title.lower()
                is_valid = any(kw.lower() in title_lower for kw in keywords)
                if is_valid:
                    print(f"  [MATCHED] Video ID: {vid} | Title: {title} (Source: {source['type']})")
                    return vid
                else:
                    print(f"  [SKIPPED] Video ID: {vid} | Title: {title}")
    return None

def main():
    print(f"Loading JSON from: {JSON_PATH}")
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = False
    for item in data:
        print(f"\nProcessing: {item['temple_name_en']} (Current live_url: {item.get('live_url')})")
        query_data = QUERIES.get(item['id'])
        if query_data:
            checked_vids = set()
            
            primary_vid = fetch_first_valid_video(query_data.get("primary"), checked_vids)
            secondary_vid = fetch_first_valid_video(query_data.get("secondary"), checked_vids)
            
            item_updated = False
            
            if primary_vid:
                new_url = f"https://www.youtube.com/watch?v={primary_vid}"
                new_thumb = f"https://img.youtube.com/vi/{primary_vid}/hqdefault.jpg"
                if item.get('live_url') != new_url:
                    item['live_url'] = new_url
                    item['thumbnail_url'] = new_thumb
                    item_updated = True
                    
            if secondary_vid:
                new_url_2 = f"https://www.youtube.com/watch?v={secondary_vid}"
                if item.get('live_url_2') != new_url_2:
                    item['live_url_2'] = new_url_2
                    item_updated = True
                    
            if item_updated:
                item['status'] = "active"
                print(f"  => SUCCESS: Updated {item['temple_name_en']}")
                print(f"     Server 1 URL: {item.get('live_url')}")
                print(f"     Server 2 URL: {item.get('live_url_2')}")
                print(f"     Thumbnail: {item.get('thumbnail_url')}")
                updated = True
            elif not primary_vid and not secondary_vid:
                print(f"  => WARNING: Could not find valid live video for {item['temple_name_en']}.")
            else:
                print(f"  => {item['temple_name_en']} is already up to date.")

    if updated:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\n[DONE] Successfully wrote updated data into live_aarti.json!")
    else:
        print("\n[DONE] No updates were necessary.")

if __name__ == "__main__":
    main()

