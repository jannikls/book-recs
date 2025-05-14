import pytest
import httpx
from bs4 import BeautifulSoup

def test_fetch_jannikschilling_bookshelf():
    url = "https://www.jannikschilling.com/bookshelf/"
    resp = httpx.get(url)
    assert resp.status_code == 200
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    # Grab all book/essay/memo list items
    items = soup.select("ol li, ul li")
    texts = [li.get_text(strip=True) for li in items]
    # Just check we get a nontrivial number of entries
    assert len(texts) > 5
    # Print a few for debug
    print("Sample bookshelf items:", texts[:5])
