#!/usr/bin/env python3
"""
モバイル一番 買取価格自動取得スクリプト
GitHub Actions用 - 3時間ごとに実行
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

PAGES = [
    {"url": "https://www.mobile-ichiban.com/Prod/2/01/01", "category": "Nintendo Switch"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/01/02", "category": "PlayStation"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/01/03", "category": "Xbox Series"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/01/04", "category": "Meta Quest"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/01/05", "category": "Steam Deck"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/03/01", "category": "IQOS ILUMA ONE"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/03/02", "category": "IQOS ILUMA PRIME"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/03/03", "category": "IQOS ILUMA KIT"},
    {"url": "https://www.mobile-ichiban.com/Prod/2/09/15", "category": "FUJIFILM instax"},
]

def parse_price(text):
    text = text.replace(',', '').replace('¥', '').replace('円', '').strip()
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0

def scrape_page(url, category):
    products = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    name_text = cells[0].get_text(strip=True)
                    if name_text and any(c.isalpha() or ord(c) > 127 for c in name_text):
                        price_text = cells[-1].get_text(strip=True) if len(cells) > 1 else ""
                        price = parse_price(price_text)
                        if price > 0:
                            products.append({'name': name_text, 'buyback_price': price})

        product_cards = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'product|item|card|list', re.I))
        for card in product_cards:
            name_el = card.find(['h2', 'h3', 'h4', 'span', 'a', 'p'], class_=re.compile(r'name|title|product', re.I))
            price_el = card.find(['span', 'div', 'p', 'td'], class_=re.compile(r'price|cost|amount|value', re.I))
            if name_el and price_el:
                name = name_el.get_text(strip=True)
                price = parse_price(price_el.get_text())
                if name and price > 0:
                    products.append({'name': name, 'buyback_price': price})

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                json_matches = re.findall(r'\[{.*?"(?:name|productName|title)".*?}\]', script.string, re.DOTALL)
                for json_str in json_matches:
                    try:
                        items = json.loads(json_str)
                        for item in items:
                            name = item.get('name') or item.get('productName') or item.get('title', '')
                            price = item.get('price') or item.get('buyPrice') or item.get('buyback_price', 0)
                            if isinstance(price, str): price = parse_price(price)
                            if name and price > 0:
                                products.append({'name': name, 'buyback_price': int(price)})
                    except json.JSONDecodeError:
                        pass

        print(f"  OK {category}: {len(products)} products")
    except Exception as e:
        print(f"  NG {category}: {e}")
    return products

def load_existing():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'prices.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def update_embedded(data):
    path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    pattern = r'const EMBEDDED_DATA = \{.*?\};'
    replacement = f'const EMBEDDED_DATA = {json.dumps(data, ensure_ascii=False, indent=16)};'
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    if new_html != html:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print("index.html updated")

def main():
    print("Update started:", datetime.now(JST).strftime('%Y-%m-%d %H:%M JST'))
    
    existing = load_existing()
    existing_map = {}
    if existing:
        for p in existing.get('all_products', []):
            existing_map[p['name']] = p
    
    all_scraped = []
    for page in PAGES:
        products = scrape_page(page['url'], page['category'])
        all_scraped.extend(products)
    
    print(f"Scraped: {len(all_scraped)} products")
    
    if all_scraped:
        updated = []
        for s in all_scraped:
            if s['name'] in existing_map:
                entry = existing_map.pop(s['name']).copy()
                entry['buyback_price'] = s['buyback_price']
                if entry['official_price'] > 0:
                    entry['rate'] = round(s['buyback_price'] / entry['official_price'] * 100, 2)
                    entry['profit'] = s['buyback_price'] - entry['official_price']
                updated.append(entry)
            else:
                updated.append({'name': s['name'], 'buyback_price': s['buyback_price'], 'brand': 'Unknown', 'official_price': 0, 'rate': 0, 'profit': 0, 'jan': '', 'group': ''})
        for entry in existing_map.values():
            updated.append(entry)
        final = updated
    else:
        final = existing['all_products'] if existing else []
        print("No scrape results, keeping existing data")
    
    output = {"updated_at": datetime.now(JST).strftime('%Y-%m-%dT%H:%M:%S'), "all_products": final}
    
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'prices.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Saved: {len(final)} products")
    update_embedded(output)

if __name__ == '__main__':
    main()
