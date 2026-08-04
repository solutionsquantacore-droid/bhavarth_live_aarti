import urllib.request
import re
import json
import os

JSON_PATH = "live_aarti.json"

def get_live_video_id(search_query):
    try:
        url = f"https://www.youtube.com/results?search_query={search_query}&sp=EgJAAQ%253D%253D"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        # Find the first video ID in the search results
        match = re.search(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching for {search_query}: {e}")
    return None

QUERIES = {
    "1": "vaishno+devi+live+darshan",
    "2": "mahakaleshwar+live+darshan",
    "3": "banke+bihari+live+darshan"
}

def main():
    # Make sure we're running from the project root
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        print("Please run this script from the root of the Android project.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = False
    for item in data:
        q = QUERIES.get(item['id'])
        if q:
            vid = get_live_video_id(q)
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

    if updated:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Successfully saved updated JSON.")
    else:
        print("No updates were necessary.")

if __name__ == "__main__":
    main()
