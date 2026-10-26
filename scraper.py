import json
import re
import time
from collections import Counter
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

# ---------- SETTINGS ----------
BASE_URL = "https://YOUR-BIGBRAINS-SITE.com"  # <-- CHANGE THIS
MAX_PAGES = 40
DELAY_SECONDS = 1
OUTPUT_FILE = "knowledge_base.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (BigBrainsSupportBot; internship project)"}
SKIP_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4", ".css", ".js", ".ico")

CATEGORIES = {
    "courses": ["course", "program", "bootcamp", "curriculum", "training", "class"],
    "internships": ["internship", "intern", "career", "job", "apply"],
    "products": ["product", "pricing", "price", "plan", "shop", "store"],
    "services": ["service", "solution", "consulting", "offer"],
    "learning_resources": ["resource", "blog", "guide", "tutorial", "learn", "faq", "help"],
    "policies": ["policy", "privacy", "terms", "refund", "cancellation", "conditions"],
}


def categorize(url, title):
    text = (url + " " + title).lower()
    for category, keywords in CATEGORIES.items():
        if any(k in text for k in keywords):
            return category
    return "general"


def clean_text(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "iframe"]):
        tag.decompose()
    raw = soup.get_text(separator="\n")
    lines, seen = [], set()
    for line in raw.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 3 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines)


def get_robot_parser(base):
    rp = RobotFileParser()
    try:
        rp.set_url(urljoin(base, "/robots.txt"))
        rp.read()
    except Exception:
        return None
    return rp


def crawl():
    domain = urlparse(BASE_URL).netloc
    robots = get_robot_parser(BASE_URL)
    queue, visited, pages = [BASE_URL], set(), []

    while queue and len(pages) < MAX_PAGES:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if robots and not robots.can_fetch(HEADERS["User-Agent"], url):
            print(f"[blocked by robots.txt] {url}")
            continue

        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code != 200 or "text/html" not in res.headers.get("Content-Type", ""):
                print(f"[skipped {res.status_code}] {url}")
                continue
        except Exception as e:
            print(f"[error] {url} -> {e}")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else url

        # collect links BEFORE cleaning (cleaning removes nav/footer)
        for a in soup.find_all("a", href=True):
            link, _ = urldefrag(urljoin(url, a["href"]))
            parsed = urlparse(link)
            if (parsed.scheme in ("http", "https") and parsed.netloc == domain
                    and not link.lower().endswith(SKIP_EXTENSIONS) and link not in visited):
                queue.append(link)

        content = clean_text(soup)
        if len(content) < 100:
            print(f"[too little text] {url}")
            continue

        pages.append({
            "url": url,
            "title": title,
            "category": categorize(url, title),
            "content": content,
        })
        print(f"[{len(pages)}/{MAX_PAGES}] {title[:60]}  ({len(content)} chars)")
        time.sleep(DELAY_SECONDS)

    return pages


if __name__ == "__main__":
    if "YOUR-BIGBRAINS-SITE" in BASE_URL:
        raise SystemExit("Set BASE_URL at the top of scraper.py first.")
    data = crawl()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(data)} pages to {OUTPUT_FILE}")
    for cat, n in Counter(p["category"] for p in data).items():
        print(f"  {cat}: {n}")