import urllib.request
import re
import json
import os

JSON_PATH = "live_aarti.json"

def get_live_video_id_from_search(search_query):
    try:
        url = f"https://www.youtube.com/results?search_query={search_query}&sp=EgJAAQ%253D%253D"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
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

QUERIES = {
    "1": {
        "handle": "@MHONESHRADDHA", 
        "type": "channel",
        "fallback": {"query": "vaishno+devi+live+aarti+sonotek", "type": "search"}
    },
    "2": {"query": "mahakaleshwar+live+darshan", "type": "search"},
    "3": {"query": "banke+bihari+live+darshan", "type": "search"}
}

def main():
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        print("Please run this script from the root of the Android project.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = False
    for item in data:
        q_info = QUERIES.get(item['id'])
        if q_info:
            vid = None
            if q_info['type'] == "channel":
                vid = get_live_video_id_from_channel(q_info['handle'])
            else:
                vid = get_live_video_id_from_search(q_info['query'])
                
            # Fallback logic
            if not vid and 'fallback' in q_info:
                fallback = q_info['fallback']
                print(f"Primary source failed for {item['temple_name_en']}, trying fallback...")
                if fallback['type'] == "channel":
                    vid = get_live_video_id_from_channel(fallback['handle'])
                else:
                    vid = get_live_video_id_from_search(fallback['query'])

            if vid:
                new_url = f"https://www.youtube.com/watch?v={vid}"
                new_thumbnail = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                
                if item.get('live_url') != new_url:
                    item['live_url'] = new_url
                    item['thumbnail_url'] = new_thumbnail
                    print(f"Updated {item['temple_name_en']} to new Video ID: {vid}")
                    updated = True
                else:
                    print(f"{item['temple_name_en']} is already up to date ({vid})")
            else:
                print(f"Could not find live video for {item['temple_name_en']} even after fallback.")

    if updated:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Successfully saved updated JSON.")
    else:
        print("No updates were necessary.")

if __name__ == "__main__":
    main()
