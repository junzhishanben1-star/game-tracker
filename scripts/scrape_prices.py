#!/usr/bin/env python3
"""
ゲーム機買取率トラッカー - Playwright スクレイピングスクリプト
モバイル一番 (mobile-ichiban.com) から最新買取価格を取得し、
prices.json と index.html の EMBEDDED_DATA を更新する。

GitHub Actions で手動実行（workflow_dispatch）用。
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# ============================================
# 商品マスターデータ（JAN → メタ情報）
# スクレイピングで取れない情報（定価、ブランド、グループ）を保持
# ============================================
PRODUCT_MASTER = {
    # --- Nintendo Switch 2 ---
    "4902370552683": {"brand": "Nintendo", "official_price": 69980, "group": "switch2_main"},
    "4902370553024": {"brand": "Nintendo", "official_price": 49980, "group": "switch2_main"},
    "4902370553031": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main"},
    "4902370553505": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main"},
    # --- Nintendo Switch (有機EL) ---
    "4902370548501": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled"},
    "4902370548495": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled"},
    # --- Nintendo Switch 標準 ---
    "4902370550733": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard"},
    "4902370551198": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard"},
    # --- Steam Deck ---
    "0814585022308": {"brand": "Valve", "official_price": 99800, "group": "steam_deck"},
    # --- PlayStation ---
    "4948872417075": {"brand": "Sony", "official_price": 119980, "group": "ps5_pro"},
    "4948872415934": {"brand": "Sony", "official_price": 79980, "group": "ps5_slim"},
    # --- Nintendo Switch 2 周辺機器 ---
    "4902370552843": {"brand": "Nintendo", "official_price": 9980, "group": "switch2_procon"},
    "4902370552744": {"brand": "Nintendo", "official_price": 9980, "group": "joycon2_pair"},
    "4902370552911": {"brand": "Nintendo", "official_price": 12980, "group": "switch2_dock"},
    # --- Meta Quest ---
    "0815820025238": {"brand": "Meta", "official_price": 48400, "group": "meta_quest3s"},
    # --- Joy-Con 2 単体 ---
    "4902370552706": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_left"},
    "4902370552720": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_right"},
    # --- microSD ---
    "4523052030185": {"brand": "SanDisk", "official_price": 7480, "group": "microsd_256"},
    "8806095700670": {"brand": "Samsung", "official_price": 7480, "group": "microsd_256"},
    # --- Nintendo Switch 周辺機器 ---
    "4902370543278": {"brand": "Nintendo", "official_price": 8778, "group": "ringfit"},
    "4902370550504": {"brand": "Nintendo", "official_price": 7980, "group": "switch_procon"},
    "4902370551136": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair"},
    "4902370551112": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair"},
    "4902370552027": {"brand": "Nintendo", "official_price": 8778, "group": "joycon_pair"},
    "4902370536010": {"brand": "Nintendo", "official_price": 7678, "group": "switch_procon_std"},
    "4902370544091": {"brand": "Nintendo", "official_price": 2728, "group": "joycon_grip"},
    "4902370535730": {"brand": "Nintendo", "official_price": 858, "group": "joycon_strap_red"},
    "4902370535747": {"brand": "Nintendo", "official_price": 858, "group": "joycon_strap_blue"},
    "4902370544114": {"brand": "Nintendo", "official_price": 2178, "group": "switch_case"},
    "4902370544060": {"brand": "Nintendo", "official_price": 3278, "group": "switch_ac"},
    # --- FUJIFILM ---
    "4547410377224": {"brand": "FUJIFILM", "official_price": 1100, "group": "cheki_film_10"},
    "4547410377231": {"brand": "FUJIFILM", "official_price": 2100, "group": "cheki_film_20"},
    "4547410369137": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu"},
    "4547410550955": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu_2025"},
    "4547410348613": {"brand": "FUJIFILM", "official_price": 1320, "group": "cheki_sq_10"},
    "4547410370003": {"brand": "FUJIFILM", "official_price": 2480, "group": "cheki_sq_20"},
    "4547410489132": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12"},
    "4547410489149": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12"},
    # --- IQOS ---
    "7622100834717": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_green"},
    "7622100834687": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_terracotta"},
    "7622100834724": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_violet"},
    "7622100834663": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_blue"},
    "7622100834649": {"brand": "IQOS", "official_price": 3980, "group": "iqos_one_black"},
    "7622100547938": {"brand": "IQOS", "official_price": 6980, "group": "iqos_one_seletti"},
    "7622100547525": {"brand": "IQOS", "official_price": 4980, "group": "iqos_one_minera"},
    "7622100547020": {"brand": "IQOS", "official_price": 5980, "group": "iqos_one_anniversary"},
    "7622100548096": {"brand": "IQOS", "official_price": 6980, "group": "iqos_kit_galaxy"},
    "7622100834601": {"brand": "IQOS", "official_price": 6980, "group": "iqos_kit_green"},
    "7622100547488": {"brand": "IQOS", "official_price": 9980, "group": "iqos_kit_minera"},
    "7622100547044": {"brand": "IQOS", "official_price": 9980, "group": "iqos_kit_anniversary"},
    "7622100547976": {"brand": "IQOS", "official_price": 14980, "group": "iqos_kit_seletti"},
    "7622100834465": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_blue"},
    "7622100834380": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_black"},
    "7622100834502": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_aspen"},
    "7622100834540": {"brand": "IQOS", "official_price": 12980, "group": "iqos_prime_garnet"},
    "7622100547464": {"brand": "IQOS", "official_price": 14980, "group": "iqos_prime_minera"},
    "7622100546993": {"brand": "IQOS", "official_price": 17980, "group": "iqos_prime_anniversary"},
    "7622100547952": {"brand": "IQOS", "official_price": 24980, "group": "iqos_prime_seletti"},
}

# スクレイピング対象ページ
SCRAPE_URLS = [
    # ゲーム > Nintendo Switch 2 (全ページ)
    "https://www.mobile-ichiban.com/Prod/2/01/01",
    # ゲーム > Nintendo Switch
    "https://www.mobile-ichiban.com/Prod/2/01/03",
    # ゲーム > PlayStation (全ページ)
    "https://www.mobile-ichiban.com/Prod/2/01/02",
    # ゲーム > Meta Quest
    "https://www.mobile-ichiban.com/Prod/2/01/06",
    # ゲーム > Steam Deck
    "https://www.mobile-ichiban.com/Prod/2/01/07",
    # カメラ > FUJIFILM instax
    "https://www.mobile-ichiban.com/Prod/2/02/14",
    # IQOS > IQOS ILUMA ONE
    "https://www.mobile-ichiban.com/Prod/2/10/01",
    # IQOS > IQOS ILUMA PRIME
    "https://www.mobile-ichiban.com/Prod/2/10/02",
    # IQOS > IQOS ILUMA KIT
    "https://www.mobile-ichiban.com/Prod/2/10/03",
]


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


async def scrape_all_prices():
    """Playwrightで全ページからJAN+買取価格を取得"""
    from playwright.async_api import async_playwright

    scraped = {}  # jan -> {"name": ..., "buyback_price": ...}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for url in SCRAPE_URLS:
            print(f"🔍 {url}")
            page_num = 1

            while True:
                current_url = url if page_num == 1 else re.sub(
                    r'/Prod/', f'/G01_ProdutShow/Index/{page_num}?kid=', url.replace('/Prod/', '/G01_ProdutShow/Index/1?kid=')
                )
                # ページネーション用URL構築
                if page_num > 1:
                    # URLパスからパラメータを構築: /Prod/2/01/02 -> kid=2&bid=01&mid=02
                    parts = url.replace("https://www.mobile-ichiban.com/Prod/", "").split("/")
                    params = []
                    keys = ["kid", "bid", "mid"]
                    for i, part in enumerate(parts):
                        if i < len(keys):
                            params.append(f"{keys[i]}={part}")
                    current_url = f"https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page_num}?{'&'.join(params)}"

                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)  # JS描画待ち
                except Exception as e:
                    print(f"  ⚠️ ページ読み込み失敗: {e}")
                    break

                # 商品カードを取得
                items = await page.query_selector_all(".col-md-12.col-sm-12.col-xs-12")
                if not items:
                    # 別のセレクタを試す
                    items = await page.query_selector_all("[class*='prod']")

                if not items and page_num == 1:
                    # ページ全体のテキストからJANと価格を抽出するフォールバック
                    content = await page.content()
                    jan_matches = re.findall(r'JAN[：:]?\s*(\d{8,13})', content)
                    price_matches = re.findall(r'(\d{1,3}(?:,\d{3})+)円', content)
                    print(f"  フォールバック: JAN {len(jan_matches)}件, 価格 {len(price_matches)}件")

                # ページ全体のHTMLからパースする方式
                content = await page.content()

                # JAN番号を含むブロックを探す
                jan_pattern = re.findall(
                    r'JAN[：:]?\s*(\d{8,13})',
                    content
                )

                if not jan_pattern:
                    if page_num > 1:
                        break  # 次ページなし
                    print(f"  ⚠️ JAN番号が見つかりません")
                    break

                # 各商品のJANと価格を取得（JavaScript実行で確実に取得）
                products_data = await page.evaluate("""
                    () => {
                        const results = [];
                        // 全テキストノードからJANと価格を探す
                        const allText = document.body.innerText;
                        
                        // 商品ブロックを探す（各商品は画像+名前+JAN+価格で構成）
                        const productBlocks = document.querySelectorAll('.row.prod_item, .prod-item, [class*="product"]');
                        
                        if (productBlocks.length > 0) {
                            productBlocks.forEach(block => {
                                const text = block.innerText;
                                const janMatch = text.match(/JAN[：:]?\s*(\d{8,13})/);
                                const priceMatch = text.match(/([\d,]+)円/g);
                                if (janMatch && priceMatch) {
                                    // 最後の価格を買取価格とする
                                    const lastPrice = priceMatch[priceMatch.length - 1];
                                    const price = parseInt(lastPrice.replace(/[,円]/g, ''));
                                    const name = text.split('\\n').find(l => l.trim().length > 5 && !l.includes('JAN') && !l.includes('円')) || '';
                                    results.push({
                                        jan: janMatch[1],
                                        name: name.trim(),
                                        buyback_price: price
                                    });
                                }
                            });
                        }
                        
                        // フォールバック: ページ全体からパース
                        if (results.length === 0) {
                            const lines = allText.split('\\n').map(l => l.trim()).filter(l => l);
                            let currentName = '';
                            let currentJan = '';
                            
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i];
                                const janMatch = line.match(/JAN[：:]?\s*(\d{8,13})/);
                                if (janMatch) {
                                    currentJan = janMatch[1];
                                    // 名前は前の行
                                    for (let j = i - 1; j >= Math.max(0, i - 5); j--) {
                                        if (lines[j].length > 5 && !lines[j].includes('JAN') && !lines[j].match(/^[\d,]+円$/)) {
                                            currentName = lines[j];
                                            break;
                                        }
                                    }
                                }
                                // 価格行（数字+円で終わる行）
                                const priceMatch = line.match(/^([\d,]+)円$/);
                                if (priceMatch && currentJan) {
                                    results.push({
                                        jan: currentJan,
                                        name: currentName,
                                        buyback_price: parseInt(priceMatch[1].replace(/,/g, ''))
                                    });
                                    currentJan = '';
                                    currentName = '';
                                }
                            }
                        }
                        
                        return results;
                    }
                """)

                found = 0
                for item in products_data:
                    jan = item.get("jan", "")
                    if jan in PRODUCT_MASTER:
                        scraped[jan] = {
                            "name": item.get("name", ""),
                            "buyback_price": item.get("buyback_price", 0)
                        }
                        found += 1

                print(f"  ページ{page_num}: {len(products_data)}商品検出, {found}件マッチ")

                # 次ページがあるか確認
                next_link = await page.query_selector('a:has-text("次へ")')
                if not next_link:
                    break
                page_num += 1
                if page_num > 10:  # 安全上限
                    break

        await browser.close()

    return scraped


def build_products(scraped):
    """スクレイピング結果 + マスターデータ → 商品リスト"""
    products = []
    updated = 0
    unchanged = 0

    for jan, master in PRODUCT_MASTER.items():
        official_price = master["official_price"]
        brand = master["brand"]
        group = master["group"]

        if jan in scraped:
            buyback_price = scraped[jan]["buyback_price"]
            name = scraped[jan]["name"]
            updated += 1
        else:
            # スクレイピングで取れなかった場合、既存データから
            buyback_price = 0
            name = f"[データ取得失敗] JAN:{jan}"
            unchanged += 1

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

    print(f"📦 更新: {updated}件, 取得失敗: {unchanged}件")
    return products


def merge_with_existing(new_products):
    """取得失敗分は既存データで補完"""
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

    merged = []
    for p in new_products:
        if p["buyback_price"] == 0 and p["jan"] in existing_map:
            # 既存データで補完
            old = existing_map[p["jan"]]
            p["name"] = old["name"]
            p["buyback_price"] = old["buyback_price"]
            p["rate"] = old["rate"]
            p["profit"] = old["profit"]
            print(f"  ♻️ 既存データ使用: {p['name']}")
        merged.append(p)

    return merged


def save_prices_json(products, updated_at):
    """prices.jsonを保存"""
    data = {
        "updated_at": updated_at,
        "all_products": products
    }
    json_path = os.path.join(get_script_dir(), '..', 'data', 'prices.json')
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 prices.json 保存完了 ({len(products)}商品)")


def update_embedded_data(products, updated_at):
    """index.htmlのEMBEDDED_DATAを更新"""
    index_path = os.path.join(get_script_dir(), '..', 'index.html')
    if not os.path.exists(index_path):
        print("⚠️ index.htmlが見つかりません")
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # EMBEDDED_DATAブロックを置換
    new_data = {
        "updated_at": updated_at,
        "all_products": products
    }
    new_json = json.dumps(new_data, ensure_ascii=False, indent=16)
    # インデントを調整（HTMLの中なので8スペース基準）
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
    print("🎮 ゲーム機買取率トラッカー - 価格更新")
    print(f"   {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}")
    print("=" * 50)

    # 1. スクレイピング
    print("\n📡 モバイル一番からデータ取得中...")
    scraped = await scrape_all_prices()
    print(f"\n✅ {len(scraped)}/{len(PRODUCT_MASTER)} 商品のデータ取得")

    if len(scraped) == 0:
        print("❌ データが取れませんでした。既存データを維持します。")
        sys.exit(1)

    # 2. 商品データ構築
    products = build_products(scraped)

    # 3. 取得失敗分を既存データで補完
    products = merge_with_existing(products)

    # 4. 保存
    updated_at = datetime.now(JST).strftime('%Y-%m-%dT%H:%M:%S')
    save_prices_json(products, updated_at)
    update_embedded_data(products, updated_at)

    # 5. サマリー
    profit_items = [p for p in products if p["rate"] >= 100]
    print(f"\n{'=' * 50}")
    print(f"📊 更新サマリー:")
    print(f"   商品数: {len(products)}")
    print(f"   利益商品: {len(profit_items)}件")
    if products:
        avg_rate = sum(p["rate"] for p in products) / len(products)
        print(f"   平均買取率: {avg_rate:.1f}%")
    print(f"   更新時刻: {updated_at}")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
