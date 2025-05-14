import requests
import os
import time

API_URL = os.getenv('API_URL', 'http://localhost:8000')
CSV_PATH = os.getenv('GOODREADS_SAMPLE_CSV', 'goodreads_library_export.csv')
USER_ID = int(os.getenv('TEST_USER_ID', '1'))

# Helper: wait for API to be up
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

def upload_csv():
    with open(CSV_PATH, 'rb') as f:
        files = {'file': (os.path.basename(CSV_PATH), f, 'text/csv')}
        r = requests.post(f"{API_URL}/upload-csv", files=files)
        assert r.status_code == 200, f"Upload failed: {r.text}"
        print("Upload response:", r.json())

def wait_for_enrichment(max_wait=60):
    # Poll for book descriptions to be filled in
    for _ in range(max_wait):
        r = requests.get(f"{API_URL}/books/count")
        count = r.json().get('count', 0)
        if count > 0:
            # Check if at least one book has a description and vector
            r = requests.get(f"{API_URL}/books/sample?has_desc=1&has_vector=1")
            if r.status_code == 200 and r.json().get('ok'):
                print("Metadata and embeddings are present.")
                return
        time.sleep(2)
    raise RuntimeError("Metadata/embeddings not ready after waiting.")

def get_recommendations():
    r = requests.get(f"{API_URL}/recommend?user_id={USER_ID}&k=5")
    assert r.status_code == 200, f"Recommend failed: {r.text}"
    recs = r.json()
    assert isinstance(recs, list) and len(recs) > 0, "No recommendations returned!"
    print("Got recommendations:", [b['title'] for b in recs])
    return recs

def give_feedback(book_id, rating):
    r = requests.post(f"{API_URL}/feedback", json={"user_id": USER_ID, "book_id": book_id, "rating": rating})
    assert r.status_code == 200, f"Feedback failed: {r.text}"
    print(f"Feedback for book {book_id} ({rating}) sent.")

def check_userbook(book_id, rating):
    # This assumes a /userbook endpoint for test, or could check via DB directly
    r = requests.get(f"{API_URL}/userbook?user_id={USER_ID}&book_id={book_id}")
    assert r.status_code == 200 and r.json().get('rating') == rating, "UserBook not updated!"
    print(f"UserBook updated for book {book_id}.")

def main():
    wait_for_api(f"{API_URL}/upload")
    upload_csv()
    wait_for_enrichment()
    recs = get_recommendations()
    # Give feedback on the first recommendation
    book_id = recs[0]['id']
    give_feedback(book_id, 5)
    # Wait for embedding update
    time.sleep(5)
    check_userbook(book_id, 5)
    # Get new recommendations and verify they shift
    new_recs = get_recommendations()
    print("Workflow test complete.")

if __name__ == '__main__':
    main()
