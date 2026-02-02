#!/usr/bin/env python3
"""
ゲーム機買取率トラッカー - Playwright スクレイピングスクリプト
モバイル一番 (mobile-ichiban.com) から最新買取価格を取得し、
prices.json と index.html の EMBEDDED_DATA を更新する。
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# ============================================
# 商品マスターデータ（JAN → メタ情報）
# ============================================
PRODUCT_MASTER = {
    "4902370552683": {"brand": "Nintendo", "official_price": 69980, "group": "switch2_main"},
    "4902370553024": {"brand": "Nintendo", "official_price": 49980, "group": "switch2_main"},
    "4902370553031": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main"},
    "4902370553505": {"brand": "Nintendo", "official_price": 53980, "group": "switch2_main"},
    "4902370548501": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled"},
    "4902370548495": {"brand": "Nintendo", "official_price": 37980, "group": "switch_oled"},
    "4902370550733": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard"},
    "4902370551198": {"brand": "Nintendo", "official_price": 32978, "group": "switch_standard"},
    "0814585022308": {"brand": "Valve", "official_price": 99800, "group": "steam_deck"},
    "4948872417075": {"brand": "Sony", "official_price": 119980, "group": "ps5_pro"},
    "4948872415934": {"brand": "Sony", "official_price": 79980, "group": "ps5_slim"},
    "4902370552843": {"brand": "Nintendo", "official_price": 9980, "group": "switch2_procon"},
    "4902370552744": {"brand": "Nintendo", "official_price": 9980, "group": "joycon2_pair"},
    "4902370552911": {"brand": "Nintendo", "official_price": 12980, "group": "switch2_dock"},
    "0815820025238": {"brand": "Meta", "official_price": 48400, "group": "meta_quest3s"},
    "4902370552706": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_left"},
    "4902370552720": {"brand": "Nintendo", "official_price": 4480, "group": "joycon2_right"},
    "4523052030185": {"brand": "SanDisk", "official_price": 7480, "group": "microsd_256"},
    "8806095700670": {"brand": "Samsung", "official_price": 7480, "group": "microsd_256"},
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
    "4547410377224": {"brand": "FUJIFILM", "official_price": 1100, "group": "cheki_film_10"},
    "4547410377231": {"brand": "FUJIFILM", "official_price": 2100, "group": "cheki_film_20"},
    "4547410369137": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu"},
    "4547410550955": {"brand": "FUJIFILM", "official_price": 2178, "group": "utsurundesu_2025"},
    "4547410348613": {"brand": "FUJIFILM", "official_price": 1320, "group": "cheki_sq_10"},
    "4547410370003": {"brand": "FUJIFILM", "official_price": 2480, "group": "cheki_sq_20"},
    "4547410489132": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12"},
    "4547410489149": {"brand": "FUJIFILM", "official_price": 15180, "group": "instax_mini12"},
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

# スクレイピング対象ページ（全ページ巡回する）
SCRAPE_URLS = [
    "https://www.mobile-ichiban.com/Prod/2/01/01",  # Nintendo Switch
    "https://www.mobile-ichiban.com/Prod/2/01/02",  # PlayStation
    "https://www.mobile-ichiban.com/Prod/2/01/03",  # Nintendo Switch 2
    "https://www.mobile-ichiban.com/Prod/2/01/06",  # Meta Quest
    "https://www.mobile-ichiban.com/Prod/2/01/07",  # Steam Deck
    "https://www.mobile-ichiban.com/Prod/2/02/14",  # FUJIFILM instax
    "https://www.mobile-ichiban.com/Prod/2/10/01",  # IQOS ILUMA ONE
    "https://www.mobile-ichiban.com/Prod/2/10/02",  # IQOS ILUMA PRIME
    "https://www.mobile-ichiban.com/Prod/2/10/03",  # IQOS ILUMA KIT
]


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


async def scrape_page_products(page):
    """現在のページからJAN+商品名+買取価格を抽出（改善版）"""
    # Playwrightで全商品情報を抽出
    products_data = await page.evaluate("""
        () => {
            const results = [];
            const html = document.body.innerHTML;
            
            // 方式1: JAN:XXXX と 価格円 のパターンでHTMLから直接抽出
            // モバイル一番のHTML構造: 商品名 → JAN:XXXX → 価格円 が順に並ぶ
            const janRegex = /JAN[：:]\\s*(\\d{7,13})/g;
            let match;
            const janPositions = [];
            
            while ((match = janRegex.exec(html)) !== null) {
                janPositions.push({
                    jan: match[1],
                    index: match.index
                });
            }
            
            // 各JANの後に出てくる最初の価格（XX,XXX円 パターン）を探す
            for (const jp of janPositions) {
                // JANの後の文字列から価格を探す
                const afterJan = html.substring(jp.index, jp.index + 2000);
                
                // 「確定」ボタンの後の価格、または単独の価格を探す
                // パターン: >XX,XXX円< または >XXX,XXX円<
                const priceMatches = afterJan.match(/(\\d{1,3}(?:,\\d{3})+)円/g);
                if (priceMatches && priceMatches.length > 0) {
                    // 最後の価格を買取価格とする（選択肢がある場合、確定後の価格が最後に来る）
                    const lastPrice = priceMatches[priceMatches.length - 1];
                    const price = parseInt(lastPrice.replace(/[,円]/g, ''));
                    
                    // JANの前のテキストから商品名を探す
                    const beforeJan = html.substring(Math.max(0, jp.index - 500), jp.index);
                    // img alt or テキストノードから商品名を取得
                    const nameMatch = beforeJan.match(/alt="[^"]*"[^>]*>[\\s\\S]*?([^<>\\n]{5,100})\\s*(?:<[^>]*>\\s*)*(?:&nbsp;|\\s)*$/);
                    
                    let name = '';
                    // innerTextベースで商品名を取得
                    const textContent = document.body.innerText;
                    const janInText = textContent.indexOf('JAN:' + jp.jan);
                    const janInText2 = textContent.indexOf('JAN：' + jp.jan);
                    const janIdx = janInText >= 0 ? janInText : janInText2;
                    
                    if (janIdx >= 0) {
                        // JANの前の数行から商品名を探す
                        const before = textContent.substring(Math.max(0, janIdx - 300), janIdx);
                        const lines = before.split('\\n').map(l => l.trim()).filter(l => l.length > 3);
                        // 商品名は通常、JANの数行前にある
                        for (let i = lines.length - 1; i >= 0; i--) {
                            const line = lines[i];
                            if (line.includes('強') || line.includes('化') || 
                                line.includes('新品') || line.includes('中古') ||
                                line.match(/^\\d/) || line.includes('来店') ||
                                line.includes('確定') || line.includes('商品買取') ||
                                line.length < 5 || line.match(/^\\d{1,3}(,\\d{3})*円$/)) {
                                continue;
                            }
                            name = line;
                            break;
                        }
                    }
                    
                    if (price > 0) {
                        results.push({
                            jan: jp.jan,
                            name: name || 'Unknown',
                            buyback_price: price
                        });
                    }
                }
            }
            
            return results;
        }
    """)
    return products_data


async def scrape_all_prices():
    """Playwrightで全ページからJAN+買取価格を取得"""
    from playwright.async_api import async_playwright

    scraped = {}

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
                # ページURL構築
                if page_num == 1:
                    current_url = url
                else:
                    parts = url.replace("https://www.mobile-ichiban.com/Prod/", "").split("/")
                    params = []
                    keys = ["kid", "bid", "mid"]
                    for i, part in enumerate(parts):
                        if i < len(keys):
                            params.append(f"{keys[i]}={part}")
                    current_url = f"https://www.mobile-ichiban.com/G01_ProdutShow/Index/{page_num}?{'&'.join(params)}"

                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)  # JS描画待ち（少し長めに）
                except Exception as e:
                    print(f"  ⚠️ ページ読み込み失敗: {e}")
                    break

                # 商品データ抽出
                products_data = await scrape_page_products(page)

                if not products_data:
                    if page_num > 1:
                        break
                    print(f"  ⚠️ 商品データなし")
                    break

                found = 0
                for item in products_data:
                    jan = item.get("jan", "")
                    if jan in PRODUCT_MASTER:
                        scraped[jan] = {
                            "name": item.get("name", ""),
                            "buyback_price": item.get("buyback_price", 0)
                        }
                        found += 1
                    # デバッグ: マッチしなかったJANも表示
                    elif jan:
                        pass  # 対象外商品はスキップ

                total = len(products_data)
                print(f"  ページ{page_num}: {total}商品検出, {found}件マッチ")
                
                # デバッグ: マッチしたJANを表示
                for item in products_data:
                    jan = item.get("jan", "")
                    if jan in PRODUCT_MASTER:
                        print(f"    ✅ {jan}: {item['name']} → ¥{item['buyback_price']:,}")

                # 次ページ確認
                next_link = await page.query_selector('a:has-text("次へ")')
                if not next_link:
                    break
                page_num += 1
                if page_num > 10:
                    break

        await browser.close()

    return scraped


def build_products(scraped):
    """スクレイピング結果 + マスターデータ → 商品リスト"""
    products = []
    updated = 0
    failed = 0

    for jan, master in PRODUCT_MASTER.items():
        official_price = master["official_price"]
        brand = master["brand"]
        group = master["group"]

        if jan in scraped:
            buyback_price = scraped[jan]["buyback_price"]
            name = scraped[jan]["name"]
            updated += 1
        else:
            buyback_price = 0
            name = f"[データ取得失敗] JAN:{jan}"
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

    print(f"📦 更新: {updated}件, 取得失敗: {failed}件")
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

    for p in new_products:
        if p["buyback_price"] == 0 and p["jan"] in existing_map:
            old = existing_map[p["jan"]]
            p["name"] = old["name"]
            p["buyback_price"] = old["buyback_price"]
            p["rate"] = old["rate"]
            p["profit"] = old["profit"]
            print(f"  ♻️ 既存データ使用: {p['name']}")

    return new_products


def save_prices_json(products, updated_at):
    """prices.jsonを保存"""
    data = {"updated_at": updated_at, "all_products": products}
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
    print("🎮 ゲーム機買取率トラッカー - 価格更新")
    print(f"   {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}")
    print("=" * 50)

    print("\n📡 モバイル一番からデータ取得中...")
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
    if products:
        valid = [p for p in products if p["rate"] > 0]
        if valid:
            avg_rate = sum(p["rate"] for p in valid) / len(valid)
            print(f"   平均買取率: {avg_rate:.1f}%")
    print(f"   更新時刻: {updated_at}")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
