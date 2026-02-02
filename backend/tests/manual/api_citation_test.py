import requests
import json


def check_citation():
    url = "http://127.0.0.1:8000/api/query"
    # specific query about 7.3 to trigger retrieval of that chunk
    payload = {"question": "What are the recordkeeping requirements in 7.3?"}

    print(f"Querying {url}...")
    with requests.post(url, json=payload, stream=True) as r:
        for line in r.iter_lines():
            if not line:
                continue
            decoded_line = line.decode("utf-8")

            if decoded_line.startswith("sources: "):
                sources_str = decoded_line[9:]
                try:
                    sources = json.loads(sources_str)
                    print(f"Received {len(sources)} sources.")
                    for i, s in enumerate(sources):
                        meta = s.get("metadata", {})
                        print(f"Source {i + 1}:")
                        print(f"  Text Snippet: {s['text'][:50]}...")
                        print(f"  Page: {meta.get('page_number')}")
                        print(f"  Header Path: {meta.get('header_path_str')}")
                        print("-" * 20)
                except Exception as e:
                    print(f"Failed to parse sources: {e}")


if __name__ == "__main__":
    check_citation()
