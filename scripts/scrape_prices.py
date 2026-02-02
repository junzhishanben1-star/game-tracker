#!/usr/bin/env python3
"""
ゲーム機買取率トラッカー - スクレイパー v6
モバイル一番(mobile-ichiban.com)から買取価格を自動取得

改善点 (v5 → v6):
- FUJIFILM instaxカテゴリ（チェキ・写ルンです）を正式スクレイピング対象に追加
- IQOSカテゴリも追加
- ページネーション完全対応（全ページ自動巡回）
- 「要問合せ」商品を正しくスキップ
- EMBEDDED_DATA補完ロジック改善（買取0円の場合のみフォールバック適用）
- カテゴリ自動判定の精度向上（Joy-Con 2 → Switch 2）
"""

import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[ERROR] playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# =============================================================================
# スクレイピング対象カテゴリ
# URLパターン: /Prod/{kid}/{bid}/{mid}
# ページネーション: /G01_ProdutShow/Index/{page}?kid={kid}&bid={bid}&mid={mid}
# =============================================================================
CATEGORIES = [
    # --- ゲーム ---
    {"name": "ゲーム全体", "url": "https://www.mobile-ichiban.com/Prod/2/01",
     "pagination": "https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page}?kid=2&bid=01",
     "category": "auto"},
    # --- カメラ > FUJIFILM instax（チェキ・写ルンです）---
    {"name": "FUJIFILM instax", "url": "https://www.mobile-ichiban.com/Prod/2/09/15",
     "pagination": "https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page}?kid=2&bid=09&mid=15",
     "category": "その他"},
    # --- IQOS ---
    {"name": "IQOS ILUMA ONE", "url": "https://www.mobile-ichiban.com/Prod/2/17/01",
     "pagination": "https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page}?kid=2&bid=17&mid=01",
     "category": "その他"},
    {"name": "IQOS ILUMA PRIME", "url": "https://www.mobile-ichiban.com/Prod/2/17/02",
     "pagination": "https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page}?kid=2&bid=17&mid=02",
     "category": "その他"},
    {"name": "IQOS ILUMA KIT", "url": "https://www.mobile-ichiban.com/Prod/2/17/03",
     "pagination": "https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page}?kid=2&bid=17&mid=03",
     "category": "その他"},
]

# 定価データ（主要商品）
RETAIL_PRICES = {
    "4902370548501": 37980,  "4902370548495": 37980,
    "4948872416320": 119980, "4948872415934": 79980,
    "0815820025238": 48400,  "0814585022308": 99800,
    "0199291152984": 139800,
    "4902370553505": 49980,  "4902370552683": 69980,
    "4902370553024": 49980,  "4902370553031": 55980,
    "4902370552843": 9878,   "4902370552744": 9878,
    "4902370552706": 5478,   "4902370552720": 5478,
    "4902370552911": 12980,  "4523052030185": 6578,
    "8806095700670": 6578,   "4902370550733": 32978,
    # FUJIFILM instax
    "4547410562293": 47300,  "4547410529975": 26730,
    "4547410529845": 30580,  "4547410377231": 2100,
    "4547410377224": 1100,   "4547410369137": 2178,
    "4547410550955": 2178,   "4547410370003": 2100,
    "4547410348613": 1100,   "4547410260649": 28600,
    "4547410269307": 28600,
    "4547410489149": 16800,  "4547410489118": 16800,
    "4547410489156": 16800,  "4547410489132": 16800,
    "4547410489125": 16800,  "4547410557954": 16800,
    "4547410534122": 16800,  "4547410555844": 41580,
    "4547410520088": 34650,
}

# フォールバック買取価格（スクレイピング失敗時用）
FALLBACK_BUYBACK = {
    "4547410377231": 2680,  # チェキフィルム 20枚
    "4547410377224": 1300,  # チェキフィルム 10枚
    "4547410369137": 2600,  # 写ルンです
    "4547410550955": 2500,  # 写ルンです 2025版
    "4547410370003": 2400,  # チェキスクエア 20枚
    "4547410348613": 1200,  # チェキスクエア 10枚
}


def detect_category(name):
    """商品名からカテゴリを自動判定"""
    nl = name.lower()
    if "switch 2" in nl or "switch2" in nl:
        return "Switch 2"
    if "joy-con 2" in nl or "joy-con2" in nl:
        return "Switch 2"
    if "switch" in nl or "joy-con" in nl:
        return "Switch"
    if "playstation" in nl or "ps5" in nl or "ps4" in nl or "dualsense" in nl:
        return "PS5"
    if "xbox" in nl or "rog" in nl:
        return "その他"
    if "meta quest" in nl or "quest" in nl:
        return "Meta Quest"
    if "steam deck" in nl:
        return "Steam Deck"
    return "その他"


def get_max_page(page):
    """ページネーションの最大ページ番号を取得"""
    try:
        last = page.query_selector('a:has-text("最後")')
        if last:
            href = last.get_attribute('href') or ""
            m = re.search(r'/(\d+)\?', href)
            if m:
                return int(m.group(1))
        # フォールバック: ページ番号リンクの最大値
        links = page.query_selector_all('.pagination a, a[href*="ProdutShow"]')
        mx = 1
        for link in links:
            t = link.inner_text().strip()
            if t.isdigit():
                mx = max(mx, int(t))
        return mx
    except Exception:
        return 1


def extract_products(page):
    """ページのテキストから商品名・JAN・買取価格を抽出"""
    products = []
    text = page.inner_text('body')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        jan_match = re.search(r'JAN[:：]?\s*(\d{8,13})', lines[i])
        if jan_match:
            jan = jan_match.group(1)
            # 前方探索: 商品名
            name = ""
            for back in range(1, min(8, i + 1)):
                c = lines[i - back]
                if len(c) < 3 or c in ('強', '化', '強化', '新品'):
                    continue
                if re.search(r'JAN[:：]', c):
                    continue
                if re.match(r'^\d{1,3}(,\d{3})*円$', c):
                    continue
                if c.startswith('来店'):
                    continue
                name = re.sub(r'^(強\s*化\s*)', '', c).strip()
                break
            # 後方探索: 買取価格
            buyback = 0
            for fwd in range(1, min(10, len(lines) - i)):
                c = lines[i + fwd]
                if '要問合せ' in c:
                    break
                pm = re.match(r'^(\d{1,3}(?:,\d{3})*)円$', c)
                if pm:
                    buyback = int(pm.group(1).replace(',', ''))
                    break
            if name and buyback > 0:
                products.append({"name": name, "jan": jan, "buyback": buyback})
        i += 1
    return products


def scrape_all():
    """全カテゴリ・全ページをスクレイピング"""
    all_products = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800},
        )
        pg = ctx.new_page()

        for cat in CATEGORIES:
            print(f"\n[SCRAPE] {cat['name']}: {cat['url']}")
            try:
                pg.goto(cat['url'], wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(2000)
                max_page = get_max_page(pg)
                print(f"  Pages: {max_page}")

                # ページ1
                prods = extract_products(pg)
                print(f"  Page 1: {len(prods)} products")
                for pr in prods:
                    key = pr['jan'] or pr['name']
                    c = cat['category'] if cat['category'] != 'auto' else detect_category(pr['name'])
                    if key not in all_products or pr['buyback'] > all_products[key]['buyback']:
                        all_products[key] = {**pr, "category": c}

                # ページ2+
                for n in range(2, max_page + 1):
                    url = cat['pagination'].format(page=n)
                    try:
                        pg.goto(url, wait_until="networkidle", timeout=30000)
                        pg.wait_for_timeout(2000)
                        prods = extract_products(pg)
                        print(f"  Page {n}: {len(prods)} products")
                        for pr in prods:
                            key = pr['jan'] or pr['name']
                            c = cat['category'] if cat['category'] != 'auto' else detect_category(pr['name'])
                            if key not in all_products or pr['buyback'] > all_products[key]['buyback']:
                                all_products[key] = {**pr, "category": c}
                    except Exception as e:
                        print(f"  [ERR] Page {n}: {e}")
            except Exception as e:
                print(f"  [ERR] {cat['name']}: {e}")

        browser.close()

    result = list(all_products.values())

    # フォールバック適用
    jans = {p['jan'] for p in result}
    for jan, fb_price in FALLBACK_BUYBACK.items():
        found = next((p for p in result if p['jan'] == jan), None)
        if found and found['buyback'] == 0:
            print(f"  [FALLBACK] {found['name']}: 0 → ¥{fb_price}")
            found['buyback'] = fb_price

    # 定価・買取率を追加
    for p in result:
        retail = RETAIL_PRICES.get(p['jan'], 0)
        p['retail'] = retail
        p['rate'] = round(p['buyback'] / retail * 100, 2) if retail > 0 else 0

    print(f"\n[TOTAL] {len(result)} unique products")
    return result


def update_embedded_data(products, html_path):
    """index.html の EMBEDDED_DATA を更新（買取0円のものは既存値を維持）"""
    if not os.path.exists(html_path):
        print(f"[SKIP] {html_path} not found")
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 既存EMBEDDED_DATAから買取価格を取得（0円補完用）
    existing = {}
    m = re.search(r'const\s+EMBEDDED_DATA\s*=\s*(\[[\s\S]*?\]);', html)
    if m:
        try:
            existing_data = json.loads(m.group(1))
            for item in existing_data:
                if item.get('jan') and item.get('buyback', 0) > 0:
                    existing[item['jan']] = item['buyback']
        except json.JSONDecodeError:
            pass

    # 新データ生成（0円の場合は既存値を使用）
    items = []
    for p in products:
        buyback = p['buyback']
        if buyback == 0 and p['jan'] in existing:
            buyback = existing[p['jan']]
        if buyback > 0:
            items.append({
                "name": p['name'], "jan": p.get('jan', ''),
                "buyback": buyback, "retail": p.get('retail', 0),
                "rate": round(buyback / p['retail'] * 100, 2) if p.get('retail', 0) > 0 else 0,
                "category": p.get('category', 'その他')
            })

    embedded_json = json.dumps(items, ensure_ascii=False, indent=2)
    new_html = re.sub(
        r'const\s+EMBEDDED_DATA\s*=\s*\[[\s\S]*?\];',
        f'const EMBEDDED_DATA = {embedded_json};',
        html
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f"[UPDATED] EMBEDDED_DATA: {len(items)} products")


def main():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    products = scrape_all()

    # prices.json 出力
    output = {
        "updated": datetime.now().isoformat(),
        "source": "mobile-ichiban.com",
        "count": len(products),
        "products": products,
    }
    out_path = data_dir / "prices.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {out_path}")

    # index.html 更新
    update_embedded_data(products, "index.html")

    # サマリー
    print("\n=== SUMMARY ===")
    cats = {}
    for p in products:
        cats.setdefault(p['category'], []).append(p)
    for c, items in sorted(cats.items()):
        above100 = sum(1 for i in items if i.get('rate', 0) >= 100)
        print(f"  {c}: {len(items)}商品 (買取率100%以上: {above100})")


if __name__ == "__main__":
    main()
