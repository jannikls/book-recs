import requests
import os
import time

# Path to a sample Goodreads export CSV (should exist in project root or specify path)
CSV_PATH = os.getenv('GOODREADS_SAMPLE_CSV', 'goodreads_sample.csv')
API_URL = os.getenv('API_URL', 'http://localhost:8000')

# Wait for the API to be up (optional, for CI/docker)
def wait_for_api(url, timeout=30):
    for _ in range(timeout):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"API not available at {url}")

def test_upload_and_count():
    wait_for_api(f"{API_URL}/upload")
    with open(CSV_PATH, 'rb') as f:
        files = {'file': (os.path.basename(CSV_PATH), f, 'text/csv')}
        r = requests.post(f"{API_URL}/upload-csv", files=files)
        assert r.status_code == 200, f"Upload failed: {r.text}"
        print("Upload response:", r.json())
    # Wait a moment for DB commit
    time.sleep(2)
    # Query books count
    r = requests.get(f"{API_URL}/books/count")
    assert r.status_code == 200, f"Count failed: {r.text}"
    count = r.json().get('count', 0)
    print(f"Book count: {count}")
    assert count > 0, "No books imported!"

if __name__ == '__main__':
    test_upload_and_count()
    print("Test passed!")
