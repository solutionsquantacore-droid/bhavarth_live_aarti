import urllib.request
import re
import json
import os

JSON_PATH = "live_aarti.json"

def get_live_video_id_from_search(search_query):
    try:
        url = f"https://www.youtube.com/results?search_query={search_query}&sp=EgJAAQ%253D%253D"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching for {search_query}: {e}")
    return None

def get_live_video_id_from_channel(channel_handle):
    try:
        url = f"https://www.youtube.com/{channel_handle}/live"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        
        # Look for canonical link which contains the actual watch URL
        match = re.search(r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">', html)
        if match:
            return match.group(1)
            
        # Fallback to search videoId in json state
        match = re.search(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching channel live for {channel_handle}: {e}")
    return None

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
        "keywords": ["vaishno", "वैष्णो"],
        "sources": [
            {"type": "channel", "handle": "@MHONESHRADDHA"},
            {"type": "search", "query": "vaishno+devi+live+darshan"},
            {"type": "search", "query": "maa+vaishno+devi+live+aarti"}
        ]
    },
    "2": {
        "keywords": ["mahakal", "महाकाल"],
        "sources": [
            {"type": "search", "query": "mahakaleshwar+live+darshan"}
        ]
    },
    "3": {
        "keywords": ["banke", "bihari", "बांके", "बिहारी", "krishna", "vrindavan"],
        "sources": [
            {"type": "search", "query": "banke+bihari+live+darshan"}
        ]
    }
}

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
            sources = query_data["sources"]
            keywords = query_data["keywords"]
            vids = []
            
            # Fetch all available video IDs for this item
            for source in sources:
                vid = None
                if source['type'] == 'channel':
                    vid = get_live_video_id_from_channel(source['handle'])
                elif source['type'] == 'search':
                    vid = get_live_video_id_from_search(source['query'])
                
                if vid and vid not in vids:
                    # Validate title
                    title = get_video_title(vid).lower()
                    is_valid = False
                    for kw in keywords:
                        if kw.lower() in title:
                            is_valid = True
                            break
                    if is_valid:
                        vids.append(vid)
                    else:
                        print(f"Skipping video {vid} for {item['temple_name_en']} due to mismatched title: {title}")
            
            if vids:
                # Primary URL
                new_url = f"https://www.youtube.com/watch?v={vids[0]}"
                new_thumbnail = f"https://img.youtube.com/vi/{vids[0]}/hqdefault.jpg"
                
                # Check if we have a secondary URL
                new_url_2 = f"https://www.youtube.com/watch?v={vids[1]}" if len(vids) > 1 else None
                
                if item.get('live_url') != new_url or item.get('live_url_2') != new_url_2:
                    item['live_url'] = new_url
                    item['thumbnail_url'] = new_thumbnail
                    
                    if new_url_2:
                        item['live_url_2'] = new_url_2
                    else:
                        item.pop('live_url_2', None)
                        
                    item['status'] = "active"
                    print(f"Updated {item['temple_name_en']} to new Video IDs: {vids}")
                    updated = True
                else:
                    print(f"{item['temple_name_en']} is already up to date ({vids})")
            else:
                print(f"Could not find valid live video for {item['temple_name_en']} from any source.")

    if updated:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Successfully saved updated JSON.")
    else:
        print("No updates were necessary.")

if __name__ == "__main__":
    main()
