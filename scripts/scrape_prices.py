#!/usr/bin/env python3
"""
ゲーム機買取率トラッカー - Playwright スクレイピングスクリプト v5
モバイル一番 (mobile-ichiban.com) から最新買取価格を取得

v5: 
- Steam Deck JAN修正 (0814585022308 → サイト上の実JANにマッチ)  
- 商品名の誤検出修正（JAN→名前の紐付けをHTMLのalt属性優先に）
- 小物アクセサリー(充電グリップ、ストラップ、ケース等)はサイト非掲載として除外
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# ============================================
# 商品マスターデータ（JAN → メタ情報）
# name_override: スクレイピングで名前が取れない場合の固定名
# ============================================
PRODUCT_MASTER = {
    # === Nintendo Switch 2 ===
    "4902370552683": {"brand": "Nintendo", "official_price": 69980, "group": "switch2_main", "name_override": "Nintendo Switch 2 多言語対応版"},
    "4902370553024": {"brand": "Nintendo", "official_price": 49980, "group": "switch2_main", "name_override": "Nintendo Switch 2 国内版"},
    "4902370553031": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main", "name_override": "Nintendo Switch 2 マリオカート ワールド セット 国内版"},
    "4902370553505": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main", "name_override": "Nintendo Switch 2 Pokemon LEGENDS Z-A セット 国内版"},
    "4902370552843": {"brand": "Nintendo", "official_price": 9980, "group": "switch2_procon", "name_override": "Nintendo Switch 2 Proコントローラー"},
    "4902370552744": {"brand": "Nintendo", "official_price": 9980, "group": "joycon2_pair", "name_override": "Joy-Con 2 (L)/(R) ライトブルー/ライトレッド"},
    "4902370552911": {"brand": "Nintendo", "official_price": 12980, "group": "switch2_dock", "name_override": "Nintendo Switch 2 ドックセット"},
    "4902370552706": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_left", "name_override": "Joy-Con 2 (L) ライトブルー"},
    "4902370552720": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_right", "name_override": "Joy-Con 2 (R) ライトレッド"},
    "4523052030185": {"brand": "SanDisk", "official_price": 7480, "group": "microsd_256", "name_override": "SanDisk microSD Express Card 256GB for Nintendo Switch 2"},
    "8806095700670": {"brand": "Samsung", "official_price": 7480, "group": "microsd_256", "name_override": "Samsung microSD Express Card 256GB for Nintendo Switch 2"},
    # === Nintendo Switch ===
    "4902370548501": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled", "name_override": "Nintendo Switch (有機ELモデル) ネオンブルー・ネオンレッド"},
    "4902370548495": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled", "name_override": "Nintendo Switch (有機ELモデル) ホワイト"},
    "4902370550733": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard", "name_override": "Nintendo Switch Joy-Con(L) ネオンブルー/(R) ネオンレッド 新型"},
    "4902370551198": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard", "name_override": "Nintendo Switch Joy-Con(L)/(R) グレー 新型"},
    "4902370543278": {"brand": "Nintendo", "official_price": 8778, "group": "ringfit", "name_override": "Nintendo Switch リングフィットアドベンチャー"},
    "4902370550504": {"brand": "Nintendo", "official_price": 7980, "group": "switch_procon", "name_override": "Nintendo Switch Proコントローラー ゼルダの伝説"},
    "4902370551136": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair", "name_override": "Nintendo Switch Joy-Con (L)/(R) パステルパープル/パステルグリーン"},
    "4902370551112": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair", "name_override": "Nintendo Switch Joy-Con (L)/(R) パステルピンク/パステルイエロー"},
    "4902370552027": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair", "name_override": "Nintendo Switch Joy-Con(L)/(R) パステルピンク"},
    # Switch小物（サイト非掲載 → 固定データ）
    "4902370536010": {"brand": "Nintendo", "official_price": 7678, "group": "switch_procon_std", "name_override": "Nintendo Switch Proコントローラー", "not_on_site": True, "fixed_buyback": 5800},
    "4902370544091": {"brand": "Nintendo", "official_price": 2728, "group": "joycon_grip", "name_override": "Joy-Con充電グリップ", "not_on_site": True, "fixed_buyback": 1800},
    "4902370535730": {"brand": "Nintendo", "official_price": 858, "group": "joycon_strap_red", "name_override": "Joy-Conストラップ ネオンレッド", "not_on_site": True, "fixed_buyback": 500},
    "4902370535747": {"brand": "Nintendo", "official_price": 858, "group": "joycon_strap_blue", "name_override": "Joy-Conストラップ ネオンブルー", "not_on_site": True, "fixed_buyback": 500},
    "4902370544114": {"brand": "Nintendo", "official_price": 2178, "group": "switch_case", "name_override": "Nintendo Switchキャリングケース", "not_on_site": True, "fixed_buyback": 1500},
    "4902370544060": {"brand": "Nintendo", "official_price": 3278, "group": "switch_ac", "name_override": "Nintendo Switch ACアダプター", "not_on_site": True, "fixed_buyback": 2200},
    # === PlayStation ===
    "4948872417075": {"brand": "Sony", "official_price": 119980, "group": "ps5_pro", "name_override": "PlayStation 5 Pro CFI-7100B01 2TB 2025版"},
    "4948872415934": {"brand": "Sony", "official_price": 79980, "group": "ps5_slim", "name_override": "PlayStation 5 slim CFI-2000A01"},
    # === Steam Deck ===
    "0814585022308": {"brand": "Valve", "official_price": 99800, "group": "steam_deck", "name_override": "Steam Deck OLED 1TB"},
    # === Meta Quest ===
    "0815820025238": {"brand": "Meta", "official_price": 48400, "group": "meta_quest3s", "name_override": "Meta Quest 3S 128GB"},
    # === FUJIFILM ===
    "4547410377224": {"brand": "FUJIFILM", "official_price": 1100, "group": "cheki_film_10", "name_override": "FUJIFILM チェキフィルム 10枚入 INSTAX MINI JP 1"},
    "4547410377231": {"brand": "FUJIFILM", "official_price": 2100, "group": "cheki_film_20", "name_override": "FUJIFILM チェキフィルム 20枚入 INSTAX MINI JP 2"},
    "4547410369137": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu", "name_override": "FUJIFILM 写ルンです シンプルエース 27枚撮り"},
    "4547410550955": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu_2025", "name_override": "FUJIFILM 写ルンです シンプルエース 27枚撮り 2025版"},
    "4547410348613": {"brand": "FUJIFILM", "official_price": 1320, "group": "cheki_sq_10", "name_override": "FUJIFILM チェキスクエア フィルム 10枚 WW1"},
    "4547410370003": {"brand": "FUJIFILM", "official_price": 2480, "group": "cheki_sq_20", "name_override": "FUJIFILM チェキスクエア フィルム 20枚 WW2"},
    "4547410489132": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12", "name_override": "instax mini 12 ミントグリーン"},
    "4547410489149": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12", "name_override": "instax mini 12 クレイホワイト"},
    # === IQOS ONE ===
    "7622100834717": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_green", "name_override": "IQOS イルマ i ワン リーフグリーン"},
    "7622100834687": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_terracotta", "name_override": "IQOS イルマ i ワン ビビッドテラコッタ"},
    "7622100834724": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_violet", "name_override": "IQOS イルマ i ワン デジタルバイオレット"},
    "7622100834663": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_blue", "name_override": "IQOS イルマ i ワン ブリーズブルー"},
    "7622100834649": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_black", "name_override": "IQOS イルマ i ワン ミッドナイトブラック"},
    "7622100547938": {"brand": "IQOS", "official_price": 6980, "group": "iqos_one_seletti", "name_override": "IQOS イルマ i ワン セレッティ モデル"},
    "7622100547525": {"brand": "IQOS", "official_price": 4980, "group": "iqos_one_minera", "name_override": "IQOS イルマ i ワン ミネラ モデル"},
    "7622100547020": {"brand": "IQOS", "official_price": 5980, "group": "iqos_one_anniversary", "name_override": "IQOS イルマ i ワン アニバーサリーモデル"},
    # === IQOS KIT ===
    "7622100548096": {"brand": "IQOS", "official_price": 6980, "group": "iqos_kit_galaxy", "name_override": "IQOS イルマ i ギャラクシーブルー"},
    "7622100834601": {"brand": "IQOS", "official_price": 6980, "group": "iqos_kit_green", "name_override": "IQOS イルマ i リーフグリーン"},
    "7622100547488": {"brand": "IQOS", "official_price": 9980, "group": "iqos_kit_minera", "name_override": "IQOS イルマ i ミネラ モデル"},
    "7622100547044": {"brand": "IQOS", "official_price": 9980, "group": "iqos_kit_anniversary", "name_override": "IQOS イルマ i アニバーサリーモデル 錫セット"},
    "7622100547976": {"brand": "IQOS", "official_price": 14980, "group": "iqos_kit_seletti", "name_override": "IQOS イルマ i セレッティ モデル"},
    # === IQOS PRIME ===
    "7622100834465": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_blue", "name_override": "IQOS イルマ i プライム ブリーズブルー"},
    "7622100834380": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_black", "name_override": "IQOS イルマ i プライム ミッドナイトブラック"},
    "7622100834502": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_aspen", "name_override": "IQOS イルマ i プライム アスペングリーン"},
    "7622100834540": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_garnet", "name_override": "IQOS イルマ i プライム ガーネットレッド限定モデル"},
    "7622100547464": {"brand": "IQOS", "official_price": 14980, "group": "iqos_prime_minera", "name_override": "IQOS イルマ i プライム ミネラ モデル"},
    "7622100546993": {"brand": "IQOS", "official_price": 17980, "group": "iqos_prime_anniversary", "name_override": "IQOS イルマ i プライム アニバーサリーモデル 錫セット"},
    "7622100547952": {"brand": "IQOS", "official_price": 24980, "group": "iqos_prime_seletti", "name_override": "IQOS イルマ i プライム セレッティ モデル"},
}

# Steam Deck: サイト上のJAN → PRODUCT_MASTER JAN マッピング
# サイトでは別JANで掲載されている可能性があるため、名前マッチも使う
STEAM_DECK_NAME_MATCH = {
    "Steam Deck OLED 1TB": "0814585022308",
    "OLED 1TB": "0814585022308",
}

MENU_CATEGORIES = [
    {"name": "Nintendo Switch 2", "menu_clicks": ["家電買取", "ゲーム", "Nintendo Switch 2"]},
    {"name": "Nintendo Switch", "menu_clicks": ["家電買取", "ゲーム", "Nintendo Switch"]},
    {"name": "PlayStation", "menu_clicks": ["家電買取", "ゲーム", "PlayStation"]},
    {"name": "Meta Quest", "menu_clicks": ["家電買取", "ゲーム", "Meta Quest"]},
    {"name": "Steam Deck", "menu_clicks": ["家電買取", "ゲーム", "Steam Deck"]},
    {"name": "FUJIFILM instax", "menu_clicks": ["家電買取", "カメラ", "FUJIFILM instax"]},
    {"name": "IQOS ILUMA ONE", "menu_clicks": ["家電買取", "IQOS", "IQOS ILUMA ONE"]},
    {"name": "IQOS ILUMA PRIME", "menu_clicks": ["家電買取", "IQOS", "IQOS ILUMA PRIME"]},
    {"name": "IQOS ILUMA KIT", "menu_clicks": ["家電買取", "IQOS", "IQOS ILUMA KIT"]},
]


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def extract_products_from_html(html):
    """HTMLソースからJAN+商品名+買取価格を抽出"""
    results = []
    jan_pattern = re.compile(r'JAN[：:]\s*(\d{7,14})')
    jan_matches = list(jan_pattern.finditer(html))

    for i, m in enumerate(jan_matches):
        jan = m.group(1)
        jan_pos = m.start()

        if i + 1 < len(jan_matches):
            end_pos = jan_matches[i + 1].start()
        else:
            end_pos = min(jan_pos + 3000, len(html))

        after_jan = html[jan_pos:end_pos]

        buyback_price = 0
        shinpin_match = re.search(r'新品.*?(\d{1,3}(?:,\d{3})+)円', after_jan, re.DOTALL)
        if shinpin_match:
            buyback_price = int(shinpin_match.group(1).replace(',', ''))
        else:
            price_matches = re.findall(r'(\d{1,3}(?:,\d{3})+)円', after_jan)
            if price_matches:
                buyback_price = int(price_matches[-1].replace(',', ''))

        # 商品名: まずalt属性から取得
        before_jan = html[max(0, jan_pos - 1000):jan_pos]
        name = ""
        
        # alt属性から商品名（最も信頼性が高い）
        alt_matches = re.findall(r'alt="([^"]{5,120})"', before_jan)
        if alt_matches:
            # 最後のalt（JANに最も近い）で、画像系以外
            for alt in reversed(alt_matches):
                if '海峡' not in alt and 'TOP' not in alt and 'top' not in alt:
                    name = alt
                    break
        
        # altが取れなければHTMLテキストから
        if not name:
            text_blocks = re.findall(r'>([^<]{5,120})<', before_jan)
            for block in reversed(text_blocks):
                block = block.strip()
                if not block or re.match(r'^[\s\d,円]+$', block):
                    continue
                if block in ('強', '化', '新品', '中古', '来店', '確定', '&nbsp;'):
                    continue
                if '来店' in block and len(block) < 15:
                    continue
                if block.startswith('JAN'):
                    continue
                if len(block) < 3:
                    continue
                name = block
                break

        if buyback_price > 0:
            results.append({
                "jan": jan,
                "name": name or f"JAN:{jan}",
                "buyback_price": buyback_price
            })

    return results


async def navigate_to_category(page, category):
    menu_clicks = category["menu_clicks"]
    await page.goto("https://www.mobile-ichiban.com/", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    for menu_text in menu_clicks:
        try:
            selector = f'text="{menu_text}"'
            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                await element.click()
                await page.wait_for_timeout(1500)
            else:
                print(f"  ⚠️ メニュー '{menu_text}' が見つかりません")
                return False
        except Exception as e:
            print(f"  ⚠️ メニュー '{menu_text}' クリック失敗: {e}")
            return False

    await page.wait_for_timeout(3000)
    return True


async def scrape_category(page, category, scraped):
    cat_name = category["name"]
    print(f"🔍 {cat_name}")

    navigated = await navigate_to_category(page, category)
    if not navigated:
        return

    page_num = 1
    total_found = 0

    while True:
        html = await page.content()
        if page_num == 1:
            print(f"  URL: {page.url}")

        products = extract_products_from_html(html)

        if not products:
            print(f"  ⚠️ ページ{page_num}: 商品なし")
            break

        found = 0
        for item in products:
            jan = item.get("jan", "")
            
            # 直接JANマッチ
            if jan in PRODUCT_MASTER and jan not in scraped:
                scraped[jan] = {
                    "name": PRODUCT_MASTER[jan].get("name_override", item["name"]),
                    "buyback_price": item["buyback_price"]
                }
                found += 1
                print(f"    ✅ {jan}: {scraped[jan]['name']} → ¥{item['buyback_price']:,}")
            
            # Steam Deck: 名前ベースマッチ（JANが異なる場合）
            elif cat_name == "Steam Deck":
                item_name = item.get("name", "")
                for pattern, master_jan in STEAM_DECK_NAME_MATCH.items():
                    if pattern in item_name and master_jan not in scraped:
                        scraped[master_jan] = {
                            "name": PRODUCT_MASTER[master_jan]["name_override"],
                            "buyback_price": item["buyback_price"]
                        }
                        found += 1
                        print(f"    ✅ (名前マッチ) {master_jan}: {scraped[master_jan]['name']} → ¥{item['buyback_price']:,}")

        total_found += found
        print(f"  ページ{page_num}: {len(products)}商品検出, {found}件新規マッチ")

        next_link = await page.query_selector('a:has-text("次へ")')
        if not next_link:
            break
        try:
            await next_link.click()
            await page.wait_for_timeout(3000)
        except:
            break
        page_num += 1
        if page_num > 10:
            break

    print(f"  → {cat_name}: 合計 {total_found}件取得")


async def scrape_all_prices():
    from playwright.async_api import async_playwright
    scraped = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for category in MENU_CATEGORIES:
            try:
                await scrape_category(page, category, scraped)
            except Exception as e:
                print(f"  ❌ {category['name']} エラー: {e}")

        await browser.close()

    # サイト非掲載商品は固定データを使用
    for jan, master in PRODUCT_MASTER.items():
        if master.get("not_on_site") and jan not in scraped:
            scraped[jan] = {
                "name": master["name_override"],
                "buyback_price": master["fixed_buyback"]
            }
            print(f"  📌 固定データ: {master['name_override']} → ¥{master['fixed_buyback']:,}")

    return scraped


def build_products(scraped):
    products = []
    updated = 0
    failed = 0

    for jan, master in PRODUCT_MASTER.items():
        official_price = master["official_price"]
        brand = master["brand"]
        group = master["group"]
        name_override = master.get("name_override", "")

        if jan in scraped:
            buyback_price = scraped[jan]["buyback_price"]
            name = name_override or scraped[jan]["name"]
            updated += 1
        else:
            buyback_price = 0
            name = name_override or f"[データ取得失敗] JAN:{jan}"
            failed += 1

        if buyback_price > 0:
            rate = round((buyback_price / official_price) * 100, 2)
            profit = buyback_price - official_price
        else:
            rate = 0
            profit = -official_price

        products.append({
            "jan": jan,
            "name": name,
            "brand": brand,
            "official_price": official_price,
            "buyback_price": buyback_price,
            "rate": rate,
            "profit": profit,
            "group": group,
        })

    print(f"\n📦 更新: {updated}件, 取得失敗: {failed}件")
    return products


def merge_with_existing(new_products):
    index_path = os.path.join(get_script_dir(), '..', 'index.html')
    if not os.path.exists(index_path):
        return new_products
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    match = re.search(r'const EMBEDDED_DATA = (\{.*?\});', html, re.DOTALL)
    if not match:
        return new_products
    try:
        existing = json.loads(match.group(1))
        existing_map = {p["jan"]: p for p in existing.get("all_products", [])}
    except:
        return new_products
    fallback_count = 0
    for p in new_products:
        if p["buyback_price"] == 0 and p["jan"] in existing_map:
            old = existing_map[p["jan"]]
            p["name"] = old["name"]
            p["buyback_price"] = old["buyback_price"]
            p["rate"] = old["rate"]
            p["profit"] = old["profit"]
            fallback_count += 1
    if fallback_count > 0:
        print(f"  ♻️ 既存データで {fallback_count}件補完")
    return new_products


def save_prices_json(products, updated_at):
    data = {"updated_at": updated_at, "all_products": products}
    json_path = os.path.join(get_script_dir(), '..', 'data', 'prices.json')
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 prices.json 保存完了 ({len(products)}商品)")


def update_embedded_data(products, updated_at):
    index_path = os.path.join(get_script_dir(), '..', 'index.html')
    if not os.path.exists(index_path):
        print("⚠️ index.htmlが見つかりません")
        return
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    new_data = {"updated_at": updated_at, "all_products": products}
    lines = json.dumps(new_data, ensure_ascii=False, indent=4).split('\n')
    indented = '\n'.join(
        ('                ' + line if i > 0 else line)
        for i, line in enumerate(lines)
    )
    pattern = r'const EMBEDDED_DATA = \{.*?\};'
    replacement = f'const EMBEDDED_DATA = {indented};'
    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)
    if count > 0:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print("✅ index.html EMBEDDED_DATA 更新完了")
    else:
        print("❌ EMBEDDED_DATA の置換に失敗")


async def main():
    print("=" * 50)
    print("🎮 ゲーム機買取率トラッカー - 価格更新 v5")
    print(f"   {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}")
    print("=" * 50)
    print("\n📡 モバイル一番からデータ取得中...\n")
    scraped = await scrape_all_prices()
    print(f"\n✅ {len(scraped)}/{len(PRODUCT_MASTER)} 商品のデータ取得")

    if len(scraped) == 0:
        print("❌ データが取れませんでした。既存データを維持します。")
        sys.exit(1)

    products = build_products(scraped)
    products = merge_with_existing(products)

    updated_at = datetime.now(JST).strftime('%Y-%m-%dT%H:%M:%S')
    save_prices_json(products, updated_at)
    update_embedded_data(products, updated_at)

    profit_items = [p for p in products if p["rate"] >= 100]
    print(f"\n{'=' * 50}")
    print(f"📊 更新サマリー:")
    print(f"   商品数: {len(products)}")
    print(f"   スクレイピング成功: {len(scraped)}件")
    print(f"   利益商品: {len(profit_items)}件")
    valid = [p for p in products if p["rate"] > 0]
    if valid:
        avg_rate = sum(p["rate"] for p in valid) / len(valid)
        print(f"   平均買取率: {avg_rate:.1f}%")
    print(f"   更新時刻: {updated_at}")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
