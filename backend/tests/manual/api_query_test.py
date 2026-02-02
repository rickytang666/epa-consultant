import requests
import json
import ast


def test_query():
    url = "http://127.0.0.1:8000/api/query"
    payload = {
        "question": "why does a pesticide company need to follow EPA regulations?"
    }

    print(f"Querying {url}...")
    with requests.post(url, json=payload, stream=True) as r:
        if r.status_code != 200:
            print(f"Error: {r.status_code}")
            return

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
                        meta = s["metadata"]
                        print(f"Source {i + 1}:")
                        print(f"  Page: {meta.get('page_number')}")
                        print(f"  Header: {meta.get('header_path_str')}")
                        print(f"  Text: {s['text'][:50]}...")
                except Exception as e:
                    print(f"Failed to parse sources: {e}")


if __name__ == "__main__":
    test_query()
