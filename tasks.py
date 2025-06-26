# tasks.py

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import quote_plus

from db import get_conn
from sites_config import SITES


def execute_task(task):
    """
    Prema task.type poziva odgovarajuću funkciju.
    'task' je objekt s atributima id, type, parameters, itd.
    """
    try:
        t = task.type
        params = task.parameters.strip()

        if t == 'count_primes':
            return count_primes(int(params))

        elif t == 'reverse':
            return params[::-1]

        elif t == 'uppercase':
            return params.upper()

        elif t == 'scrape':
            return dispatch_scrape_subtasks(task.id, params)

        elif t == 'scrape_url':
            return scrape_single_url(params)

        elif t == 'compare_offers':
            return compare_offers(params)

        elif t == 'compare_skin_offers':
            return compare_skin_offers(params)

        else:
            return f"Unknown task type: {t}"
    except Exception as e:
        return f"Error while executing {task.type}: {e}"


# === 1. count_primes i is_prime ===

def count_primes(n):
    count = 0
    for num in range(2, n + 1):
        if is_prime(num):
            count += 1
    return count

def is_prime(x):
    if x < 2:
        return False
    if x == 2:
        return True
    if x % 2 == 0:
        return False
    limit = int(x**0.5) + 1
    d = 3
    while d <= limit:
        if x % d == 0:
            return False
        d += 2
    return True


# === 2. dispatch_scrape_subtasks i scrape_single_url ===

def dispatch_scrape_subtasks(parent_task_id, url):
    """
    Scrapea URL i za svaki <a href=...> kreira novi subtask.
    Parent task se potom označi kao completed s rezultatom.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        anchors = soup.find_all('a', href=True)

        links = {a['href'] for a in anchors
                 if a['href'].startswith(('http://', 'https://'))}
        count = 0

        with get_conn() as conn:
            with conn.cursor() as cur:
                for link in links:
                    cur.execute(
                        """
                        INSERT INTO tasks(type, parameters, status, created_at, updated_at)
                        VALUES (%s, %s, 'pending', now(), now())
                        """,
                        ('scrape_url', link)
                    )
                    count += 1

                cur.execute(
                    """
                    UPDATE tasks
                       SET status='completed',
                           result=%s,
                           updated_at=now()
                     WHERE id = %s
                    """,
                    (f"Dispatched {count} subtasks", parent_task_id)
                )
            conn.commit()

        return f"Dispatched {count} subtasks"

    except Exception as e:
        return f"Error in dispatch_scrape_subtasks: {e}"


def scrape_single_url(url):
    """
    Scrapea URL i vraća njegov <title> i duljinu HTML sadržaja.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text
        soup = BeautifulSoup(text, 'html.parser')
        title = soup.find('title')
        title_text = title.text.strip() if title else '(no title)'
        return f"Title: {title_text} (length {len(text)} chars)"
    except Exception as e:
        return f"Error scraping {url}: {e}"


# === 3. compare_offers i generički scraper ===

def compare_offers(product_name: str) -> str:
    """
    Scrapea Links i Instar, vraća JSON:
      { "offers":[{"site",price,url},…], "best":site_name }
    Preskače sve gdje price=None, best=None ako nema ponuda.
    """
    query = re.sub(r'\s+', '+', product_name.strip())
    full_phrase = product_name.strip().lower()
    keywords = [w.lower() for w in product_name.strip().split()]

    offers = []
    for site_name, cfg in SITES.items():
        if site_name not in ("Links", "Instar"):
            continue

        search_url = cfg["search_url"].format(query=query)
        price, link = scrape_site(search_url, cfg, full_phrase, keywords)
        if price is not None:
            offers.append({
                "site": site_name,
                "price": price,
                "url": link
            })

    if not offers:
        return json.dumps({"offers": [], "best": None})

    best_offer = min(offers, key=lambda o: o["price"])
    return json.dumps({"offers": offers, "best": best_offer["site"]})


def scrape_site(search_url: str, cfg: dict, full_phrase: str, keywords: list):
    """
    Generički scraper: koristi cfg['item_selector'] i cfg['price_selector'].
    Vraća (float price or None, product_url).
    """
    try:
        resp = requests.get(search_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # koristi točno onaj selector iz konfiguracije
        items = soup.select(cfg["item_selector"])
        if not items:
            return None, search_url

        # pokušaj prvo full-phrase match
        match = None
        for it in items:
            if cfg.get("title_attr"):
                title_text = it.get(cfg["title_attr"], "").lower()
            elif cfg.get("title_in_span"):
                span = it.select_one("span")
                title_text = span.get_text(strip=True).lower() if span else ""
            else:
                title_text = ""
            if full_phrase in title_text:
                match = it
                break

        # fallback: match po svim ključnim riječima
        if not match:
            for it in items:
                if cfg.get("title_attr"):
                    title_text = it.get(cfg["title_attr"], "").lower()
                elif cfg.get("title_in_span"):
                    span = it.select_one("span")
                    title_text = span.get_text(strip=True).lower() if span else ""
                else:
                    title_text = ""
                if all(k in title_text for k in keywords):
                    match = it
                    break

        if not match:
            return None, search_url

        href = match.get("href", "")
        link = href if href.startswith("http") else cfg["url_prefix"].rstrip("/") + href

        # parsaj cijenu
        price_elem = match.select_one(cfg["price_selector"])
        price_text = price_elem.get_text(strip=True) if price_elem else None
        if not price_text:
            nxt = match.find_next(string=re.compile(r"€"))
            price_text = nxt.strip() if nxt else None

        if not price_text:
            return None, link

        # očisti i konvertiraj na float
        clean = re.sub(r"[^\d,\.]", "", price_text).replace(".", "").replace(",", ".")
        try:
            return float(clean), link
        except ValueError:
            return None, link

    except Exception:
        return None, search_url


# === 4. helpers za CS2 skinove ===

def scrape_skinbaron(item_name: str) -> list:
    cfg = SITES["SkinBaron"]
    query = re.sub(r'\s+', '+', item_name.strip())
    url = cfg["search_url"].format(query=query)
    price, link = scrape_site(url, cfg, item_name.lower(), [w.lower() for w in item_name.split()])
    return [{"site": "SkinBaron", "market_price": price, "url": link}] if price is not None else []

def scrape_skinport(item_name: str) -> list:
    cfg = SITES["SkinPort"]
    query = re.sub(r'\s+', '+', item_name.strip())
    url = cfg["search_url"].format(query=query)
    price, link = scrape_site(url, cfg, item_name.lower(), [w.lower() for w in item_name.split()])
    return [{"site": "SkinPort", "market_price": price, "url": link}] if price is not None else []

def compare_skin_offers(item_name: str) -> str:
    sb = scrape_skinbaron(item_name)
    sp = scrape_skinport(item_name)
    all_offers = sb + sp
    if not all_offers:
        return json.dumps({"best": None})
    cheapest = min(all_offers, key=lambda o: o["market_price"])
    return json.dumps({"best": cheapest})
