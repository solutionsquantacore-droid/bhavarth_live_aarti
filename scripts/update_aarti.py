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
        "keywords": ["vaishno", "वैष्णो", "mata", "maa", "माता", "मां"],
        "sources": [
            {"type": "channel", "handle": "@MHONESHRADDHA"},
            {"type": "channel", "handle": "@SonotekBhakti"},
            {"type": "channel", "handle": "@Sonotek"},
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
            checked_vids = set()
            source_fetched_cache = []
            
            # First pass: try to get exactly ONE valid video from each source, in order
            for source in sources:
                if len(vids) >= 2:
                    break
                    
                if source['type'] == 'channel':
                    fetched_vids = get_live_video_ids_from_channel(source['handle'])
                elif source['type'] == 'search':
                    fetched_vids = get_live_video_ids_from_search(source['query'])
                
                source_fetched_cache.append(fetched_vids)
                
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
                            vids.append(vid)
                            break # Found 1 for this source, move to next source to ensure diversity!
                        else:
                            print(f"Skipping video {vid} for {item['temple_name_en']} due to mismatched title: {title}")
                            
            # Second pass: if we still need more videos, go back through the cached lists
            if len(vids) < 2:
                for fetched_vids in source_fetched_cache:
                    if len(vids) >= 2:
                        break
                    for vid in fetched_vids:
                        if len(vids) >= 2:
                            break
                        if vid and vid not in checked_vids:
                            checked_vids.add(vid)
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
