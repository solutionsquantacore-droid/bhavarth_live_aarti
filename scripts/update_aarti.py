import urllib.request
import re
import json
import os

JSON_PATH = "live_aarti.json"

def get_live_video_ids_from_search(search_query):
    try:
        url = f"https://www.youtube.com/results?search_query={search_query}&sp=EgJAAQ%253D%253D"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        return list(dict.fromkeys(matches)) # Return unique IDs in order
    except Exception as e:
        print(f"Error fetching for {search_query}: {e}")
    return []

def get_live_video_ids_from_channel(channel_handle):
    try:
        url = f"https://www.youtube.com/{channel_handle}/streams"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        return list(dict.fromkeys(matches)) # Return unique IDs
    except Exception as e:
        print(f"Error fetching channel streams for {channel_handle}: {e}")
    return []

def get_video_title(vid):
    try:
        url = f"https://www.youtube.com/watch?v={vid}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'<title>(.*?)</title>', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching title for {vid}: {e}")
    return ""

QUERIES = {
    "1": {
        "primary": {
            "keywords": ["vaishno", "वैष्णो", "mh one", "shraddha"],
            "sources": [
                {"type": "channel", "handle": "@MHONESHRADDHA"},
                {"type": "search", "query": "mh+one+shraddha+vaishno+devi+live+darshan"}
            ]
        },
        "secondary": {
            "keywords": ["vaishno", "वैष्णो", "mata", "maa", "माता", "मां"],
            "sources": [
                {"type": "channel", "handle": "@SonotekBhakti"},
                {"type": "channel", "handle": "@Sonotek"},
                {"type": "search", "query": "vaishno+devi+live+darshan"}
            ]
        }
    },
    "2": {
        "primary": {
            "keywords": ["mahakal", "महाकाल"],
            "sources": [
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
        if source['type'] == 'channel':
            fetched_vids = get_live_video_ids_from_channel(source['handle'])
        elif source['type'] == 'search':
            fetched_vids = get_live_video_ids_from_search(source['query'])
            
        for vid in fetched_vids:
            if vid and vid not in checked_vids:
                checked_vids.add(vid)
                title = get_video_title(vid).lower()
                is_valid = False
                for kw in keywords:
                    if kw.lower() in title:
                        is_valid = True
                        break
                if is_valid:
                    return vid
                else:
                    print(f"Skipping video {vid} due to mismatched title: {title}")
    return None

def main():
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        print("Please run this script from the directory containing live_aarti.json.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = False
    for item in data:
        query_data = QUERIES.get(item['id'])
        if query_data:
            checked_vids = set()
            
            primary_vid = fetch_first_valid_video(query_data.get("primary"), checked_vids)
            secondary_vid = fetch_first_valid_video(query_data.get("secondary"), checked_vids)
            
            # Update item if we found valid streams
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
            elif query_data.get("secondary"):
                if 'live_url_2' in item:
                    item.pop('live_url_2', None)
                    item_updated = True
                    
            if not primary_vid and not secondary_vid:
                print(f"Could not find valid live video for {item['temple_name_en']} from any source.")
            elif item_updated:
                item['status'] = "active"
                print(f"Updated {item['temple_name_en']} | Server 1: {primary_vid} | Server 2: {secondary_vid}")
                updated = True
            else:
                print(f"{item['temple_name_en']} is already up to date.")

    if updated:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Successfully saved updated JSON.")
    else:
        print("No updates were necessary.")

if __name__ == "__main__":
    main()
