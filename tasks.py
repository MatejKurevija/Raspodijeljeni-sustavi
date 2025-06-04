# tasks.py

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from db import SessionLocal
from models import Task
from sites_config import SITES


# ===================================
# 1. Glavna funkcija: execute_task
# ===================================
def execute_task(task):

    try:
        if task.type == 'count_primes':
            n = int(task.parameters)
            return count_primes(n)

        elif task.type == 'reverse':
            return task.parameters[::-1]

        elif task.type == 'uppercase':
            return task.parameters.upper()

        elif task.type == 'scrape':
            url = task.parameters.strip()
            return dispatch_scrape_subtasks(task.id, url)

        elif task.type == 'scrape_url':
            url = task.parameters.strip()
            return scrape_single_url(url)

        elif task.type == 'compare_offers':
            product_name = task.parameters.strip()
            return compare_offers(product_name)

        elif task.type == 'compare_skin_offers':
            skin_name = task.parameters.strip()
            return compare_skin_offers(skin_name)

        else:
            return f"Unknown task type: {task.type}"
    except Exception as e:
        return f"Error while executing {task.type}: {str(e)}"


# ===================================
# 2. count_primes i is_prime
# ===================================
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


# =======================================
# 3. dispatch_scrape_subtasks i scrape_single_url
# =======================================
def dispatch_scrape_subtasks(parent_task_id, url):
    session = SessionLocal()
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        anchors = soup.find_all('a', href=True)

        links = set()
        for a in anchors:
            href = a['href']
            if href.startswith('http://') or href.startswith('https://'):
                links.add(href)

        count_subtasks = 0
        for link in links:
            sub = Task(type='scrape_url', parameters=link, status='pending')
            session.add(sub)
            count_subtasks += 1

        parent = session.query(Task).filter_by(id=parent_task_id).first()
        if parent:
            parent.status = 'completed'
            parent.result = f"Dispatched {count_subtasks} subtasks"
        session.commit()
        return f"Dispatched {count_subtasks} subtasks"
    except Exception as e:
        return f"Error in dispatch_scrape_subtasks: {str(e)}"
    finally:
        session.close()

def scrape_single_url(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else '(no title)'
        length = len(resp.text)
        return f"Title: {title} (length {length} chars)"
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"


# ======================================
# 4. compare_offers i generički scraper
# ======================================
def compare_offers(product_name: str):
    query = re.sub(r'\s+', '+', product_name.strip())
    full_phrase = product_name.strip().lower()
    keywords = [w.lower() for w in product_name.strip().split()]

    offers = []
    for site_name, cfg in SITES.items():
        # Ako je site CS2 (SkinBaron ili SkinPort), preskoči ga
        if site_name in ("SkinBaron", "SkinPort"):
            continue

        search_url = cfg["search_url"].format(query=query)
        price, link = scrape_site(search_url, cfg, full_phrase, keywords)
        if price is not None:
            offers.append({"site": site_name, "price": price, "url": link})
        else:
            offers.append({"site": site_name, "price": float('inf'), "url": search_url})

    best = min(offers, key=lambda x: x["price"])["site"]
    result = {"offers": offers, "best": best}
    return json.dumps(result)


def scrape_site(search_url: str, cfg: dict, full_phrase: str, keywords: list):

    try:
        resp = requests.get(search_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Dodaj točku ispred item_selector ako već ne počinje s njom
        raw_item_sel = cfg["item_selector"]
        css_item_selector = raw_item_sel if raw_item_sel.startswith('.') else "." + raw_item_sel
        all_items = soup.select(css_item_selector)
        if not all_items:
            return None, search_url

        # 1) Full-match po nazivu
        match_item = None
        for item in all_items:
            if cfg.get("title_attr"):
                title_text = item.get(cfg["title_attr"], "").lower()
            elif cfg.get("title_in_span"):
                span = item.select_one("span")
                title_text = span.get_text(strip=True).lower() if span else ""
            else:
                title_text = ""

            if full_phrase in title_text:
                match_item = item
                break

        # 2) Fallback match po svim riječima
        if not match_item:
            for item in all_items:
                if cfg.get("title_attr"):
                    title_text = item.get(cfg["title_attr"], "").lower()
                elif cfg.get("title_in_span"):
                    span = item.select_one("span")
                    title_text = span.get_text(strip=True).lower() if span else ""
                else:
                    title_text = ""

                if all(k in title_text for k in keywords):
                    match_item = item
                    break

        if not match_item:
            return None, search_url

        href = match_item.get("href", "")
        if href.startswith("http"):
            link = href
        else:
            link = cfg["url_prefix"].rstrip("/") + href

        # Dodaj točku ispred price_selector ako već ne počinje s njom; ako ima space, zamijeni space u točku
        raw_price_sel = cfg["price_selector"]
        price_sel = raw_price_sel.replace(" ", ".")
        css_price_selector = price_sel if price_sel.startswith('.') else "." + price_sel
        price_elem = match_item.select_one(css_price_selector)
        if not price_elem:
            price_elem_text = match_item.find_next(string=re.compile(r"€"))
            if not price_elem_text:
                return None, link
            price_text = price_elem_text.strip()
        else:
            price_text = price_elem.get_text(strip=True)

        price_value = parse_price_eur(price_text)
        return price_value, link

    except Exception:
        return None, search_url


def parse_price_eur(text: str) -> float:
    clean = re.sub(r"[€EUR\s]", "", text)
    clean = re.sub(r"[^\d,\.]", "", clean)
    clean = clean.replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


# ===========================================
# 5. compare_skin_offers – samo SkinBaron i SkinPort, najjeftinija ponuda
# ===========================================
def scrape_skinbaron(item_name: str) -> list:
    """
    Scrapea SkinBaron i vraća listu ponuda (site, market_price, url).
    Ako ništa ne pronađe, vraća prazan popis.
    """
    offers = []
    base = "https://skinbaron.de/en/csgo"
    encoded = quote_plus(item_name, safe="")
    url = f"{base}?str={encoded}&sort=PA"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cfg = SITES["SkinBaron"]

    raw_item_sel = cfg["item_selector"]
    css_item_selector = raw_item_sel if raw_item_sel.startswith('.') else "." + raw_item_sel
    cards = soup.select(css_item_selector)

    for card in cards:
        a_tag = card.select_one("a." + cfg["item_selector"])
        if not a_tag or not a_tag.get("href"):
            continue
        product_url = cfg["url_prefix"].rstrip("/") + a_tag["href"]

        raw_price_sel = cfg["price_selector"]
        price_sel = raw_price_sel.replace(" ", ".")
        css_price_selector = price_sel if price_sel.startswith('.') else "." + price_sel
        price_elem = card.select_one(css_price_selector)
        if not price_elem:
            continue

        price_text = price_elem.get_text(strip=True)
        cleaned = re.sub(r"[^\d\,\.]", "", price_text).replace(".", "").replace(",", ".")
        try:
            price = float(cleaned)
        except ValueError:
            continue

        offers.append({
            "site": "SkinBaron",
            "market_price": price,
            "url": product_url
        })

    return offers


def scrape_skinport(item_name: str) -> list:
    """
    Scrapea SkinPort i vraća listu ponuda (site, market_price, url).
    Ako ništa ne pronađe, vraća prazan popis.
    """
    offers = []
    base = "https://skinport.com/market"
    encoded = quote_plus(item_name, safe="")
    url = f"{base}?search={encoded}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cfg = SITES["SkinPort"]

    raw_item_sel = cfg["item_selector"]
    css_item_selector = raw_item_sel if raw_item_sel.startswith('.') else "." + raw_item_sel
    cards = soup.select(css_item_selector)

    for card in cards:
        a_tag = card.select_one("a." + cfg["item_selector"])
        if not a_tag or not a_tag.get("href"):
            continue
        product_url = cfg["url_prefix"].rstrip("/") + a_tag["href"]

        raw_price_sel = cfg["price_selector"]
        price_sel = raw_price_sel.replace(" ", ".")
        css_price_selector = price_sel if price_sel.startswith('.') else "." + price_sel
        price_elem = card.select_one(css_price_selector)
        if not price_elem:
            continue

        price_text = price_elem.get_text(strip=True)
        cleaned = re.sub(r"[^\d\,\.]", "", price_text).replace(".", "").replace(",", ".")
        try:
            price = float(cleaned)
        except ValueError:
            continue

        offers.append({
            "site": "SkinPort",
            "market_price": price,
            "url": product_url
        })

    return offers


def compare_skin_offers(item_name: str) -> str:
    """
    Scrapea SkinBaron i SkinPort, pronađe najjeftiniju ponudu i vraća JSON:
      {
        "best": {
          "site": "<naziv_sitea>",
          "market_price": <float>,
          "url": "<link_do_proizvoda>"
        }
      }
    Ako ne pronađe niti jednu ponudu, vratiti će:
      { "best": null }
    """
    sb_offers = scrape_skinbaron(item_name)
    sp_offers = scrape_skinport(item_name)

    all_offers = sb_offers + sp_offers

    if not all_offers:
        return json.dumps({"best": None})

    cheapest = min(all_offers, key=lambda o: o["market_price"])
    result = {"best": cheapest}
    return json.dumps(result)
