"""Check Rakuten prices for tracked products and detect flash-sale style drops.

Uses the Rakuten Ichiba Item Search API (2026-07-01 revision, openapi.rakuten.co.jp
host). On the first run for a product it searches by keyword and pins the
resulting itemCode so later runs compare the same listing rather than
whatever currently tops the keyword search.

Usage:
    RAKUTEN_APPLICATION_ID=... RAKUTEN_ACCESS_KEY=... python3 scripts/check_deals.py

Env vars:
    RAKUTEN_APPLICATION_ID  required
    RAKUTEN_ACCESS_KEY      required
    DEAL_DROP_THRESHOLD     default: 0.1 (10% drop from the last checked price)
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_PATH = ROOT / "_data" / "products.yml"
CONFIG_PATH = ROOT / "_config.yml"
STATE_PATH = ROOT / "data" / "deal_watch_state.yml"
DEALS_PATH = ROOT / "data" / "detected_deals.json"

API_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
DROP_THRESHOLD = float(os.environ.get("DEAL_DROP_THRESHOLD", "0.1"))
REQUEST_INTERVAL_SEC = 1.2


def load_yaml(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def get_rakuten_affiliate_id():
    config = load_yaml(CONFIG_PATH)
    return config.get("rakuten_affiliate_id")


def build_affiliate_url(item_url, affiliate_id):
    if not affiliate_id or not item_url:
        return item_url
    return f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={quote(item_url, safe='')}"


def fetch_item(application_id, access_key, keyword=None, item_code=None):
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "formatVersion": 2,
        "hits": 1,
    }
    if item_code:
        params["itemCode"] = item_code
    elif keyword:
        params["keyword"] = keyword
    else:
        raise ValueError("keyword or item_code is required")

    resp = requests.get(API_ENDPOINT, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return None
    return items[0]


def write_output(name, value):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def main():
    application_id = os.environ.get("RAKUTEN_APPLICATION_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not application_id or not access_key:
        sys.exit("RAKUTEN_APPLICATION_ID / RAKUTEN_ACCESS_KEY is not set")

    affiliate_id = get_rakuten_affiliate_id()
    products = load_yaml(PRODUCTS_PATH)
    state = load_yaml(STATE_PATH)

    deals = []

    for i, product in enumerate(products):
        if i > 0:
            time.sleep(REQUEST_INTERVAL_SEC)

        key = product["key"]
        keyword = product.get("keyword")
        if not keyword:
            continue

        entry = state.get(key, {})
        item_code = entry.get("rakuten_item_code")

        try:
            item = fetch_item(
                application_id,
                access_key,
                keyword=None if item_code else keyword,
                item_code=item_code,
            )
        except requests.RequestException as e:
            print(f"警告: {key} の価格取得に失敗しました: {e}")
            continue

        if not item:
            print(f"警告: {key} に一致する商品が見つかりませんでした")
            continue

        current_price = item.get("itemPrice")
        current_item_code = item.get("itemCode")
        item_url = item.get("itemUrl")

        if current_price is None:
            continue

        previous_price = entry.get("last_price")

        if previous_price and current_price <= previous_price * (1 - DROP_THRESHOLD):
            discount_pct = round((1 - current_price / previous_price) * 100, 1)
            deals.append({
                "key": key,
                "name": product["name"],
                "previous_price": previous_price,
                "current_price": current_price,
                "discount_pct": discount_pct,
                "url": build_affiliate_url(item_url, affiliate_id),
            })

        state[key] = {
            "rakuten_item_code": current_item_code or item_code,
            "last_price": current_price,
        }

    save_yaml(STATE_PATH, state)
    DEALS_PATH.write_text(json.dumps(deals, ensure_ascii=False, indent=2), encoding="utf-8")

    if deals:
        print(f"{len(deals)}件の値下がりを検知しました:")
        for d in deals:
            print(f" - {d['name']}: {d['previous_price']}円 → {d['current_price']}円（{d['discount_pct']}%引）")
        write_output("deals_found", "true")
    else:
        print("値下がりは検知されませんでした。")
        write_output("deals_found", "false")


if __name__ == "__main__":
    main()
