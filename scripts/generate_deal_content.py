"""Generate a flash-deal blog post and copy-paste SNS drafts for detected deals.

Reads data/detected_deals.json (written by check_deals.py). For each deal,
writes a short blog post to _posts/ (published automatically via the normal
Pages build) and a draft file to sns_drafts/ with ready-to-paste X and
Instagram captions. Posting to SNS itself stays a manual step.

Usage:
    ANTHROPIC_API_KEY=... python3 scripts/generate_deal_content.py
"""
import datetime
import json
import os
import sys
from pathlib import Path

import anthropic
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEALS_PATH = ROOT / "data" / "detected_deals.json"
DRAFTS_SUMMARY_PATH = ROOT / "data" / "latest_deal_drafts.json"
POSTS_DIR = ROOT / "_posts"
DRAFTS_DIR = ROOT / "sns_drafts"

MODEL = os.environ.get("ARTICLE_MODEL", "claude-haiku-4-5-20251001")

DEAL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "body": {"type": "string"},
        "x_caption": {"type": "string"},
        "instagram_caption": {"type": "string"},
    },
    "required": ["title", "body", "x_caption", "instagram_caption"],
    "additionalProperties": False,
}


def slugify(key, date):
    return f"{date.isoformat()}-deal-{key.replace('_', '-')}"


def generate_deal_content(client, deal):
    prompt = f"""あなたは防災・ポータブル電源ジャンルのブログ編集者です。
以下の値下がり情報をもとに、次の4つを作成してください。

- title: 記事タイトル（30〜40文字程度、値下がり幅が伝わる見出し）
- body: ブログ本文（Markdown、400〜600文字程度。誇大表現は避け、通常の価格帯や使いどころにも軽く触れる）
- x_caption: X（旧Twitter）投稿用の短文（120文字以内、絵文字は使わない）
- instagram_caption: Instagram投稿用のキャプション（200文字程度、ハッシュタグを3〜5個含める）

商品名: {deal['name']}
通常価格: {deal['previous_price']}円
現在価格: {deal['current_price']}円
割引率: 約{deal['discount_pct']}%
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        output_config={"format": {"type": "json_schema", "schema": DEAL_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")

    if not DEALS_PATH.exists():
        print("data/detected_deals.json が見つかりません。先に check_deals.py を実行してください。")
        return

    deals = json.loads(DEALS_PATH.read_text(encoding="utf-8"))
    if not deals:
        print("検知された値下がりがないため、生成をスキップします。")
        DRAFTS_SUMMARY_PATH.write_text("[]", encoding="utf-8")
        return

    client = anthropic.Anthropic(api_key=api_key)
    POSTS_DIR.mkdir(exist_ok=True)
    DRAFTS_DIR.mkdir(exist_ok=True)

    today = datetime.date.today()
    created = []

    for deal in deals:
        print(f"生成中: {deal['name']} の特価速報")
        content = generate_deal_content(client, deal)
        slug = slugify(deal["key"], today)

        front_matter = {
            "title": content["title"],
            "categories": ["タイムセール速報"],
            "products": [deal["key"]],
        }
        fm_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False)
        post_body = f"---\n{fm_yaml}---\n\n{content['body']}\n"
        (POSTS_DIR / f"{slug}.md").write_text(post_body, encoding="utf-8")

        draft_text = (
            f"# {deal['name']} 特価速報 ({today.isoformat()})\n\n"
            f"通常 {deal['previous_price']}円 → 現在 {deal['current_price']}円（約{deal['discount_pct']}%引）\n"
            f"商品リンク: {deal['url']}\n\n"
            f"## X用\n{content['x_caption']}\n\n"
            f"## Instagram用\n{content['instagram_caption']}\n"
        )
        (DRAFTS_DIR / f"{slug}.md").write_text(draft_text, encoding="utf-8")

        created.append({"slug": slug, "title": content["title"], "name": deal["name"]})

    DRAFTS_SUMMARY_PATH.write_text(json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8")

    print("作成した速報記事・SNS下書き:")
    for c in created:
        print(f" - _posts/{c['slug']}.md / sns_drafts/{c['slug']}.md")


if __name__ == "__main__":
    main()
