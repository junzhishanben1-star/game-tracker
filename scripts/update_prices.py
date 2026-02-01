#!/usr/bin/env python3
"""
ゲーム機買取率トラッカー - 価格データ同期スクリプト
GitHub Actions用 - 3時間ごとに実行

index.htmlのEMBEDDED_DATAをマスターデータとし、
prices.jsonを同期する方式。
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def extract_embedded_data():
    """index.htmlからEMBEDDED_DATAを抽出"""
    index_path = os.path.join(get_script_dir(), '..', 'index.html')
    if not os.path.exists(index_path):
        print(f"❌ index.html が見つかりません: {index_path}")
        return None
    
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    match = re.search(r'const EMBEDDED_DATA = (\{.*?\});', html, re.DOTALL)
    if not match:
        print("❌ EMBEDDED_DATA が見つかりません")
        return None
    
    try:
        data = json.loads(match.group(1))
        return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        return None

def save_prices_json(data):
    """prices.jsonを保存"""
    json_path = os.path.join(get_script_dir(), '..', 'data', 'prices.json')
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return json_path

def main():
    print("🔄 データ同期開始")
    print(f"   {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}")
    
    embedded = extract_embedded_data()
    if not embedded:
        print("❌ 失敗。終了。")
        return
    
    products = embedded.get('all_products', [])
    print(f"📦 {len(products)} 商品取得")
    
    if not products:
        print("⚠️ 商品なし。終了。")
        return
    
    output = {
        "updated_at": datetime.now(JST).strftime('%Y-%m-%dT%H:%M:%S'),
        "all_products": products
    }
    
    path = save_prices_json(output)
    print(f"💾 保存: {path} ({len(products)}商品)")

if __name__ == '__main__':
    main()
