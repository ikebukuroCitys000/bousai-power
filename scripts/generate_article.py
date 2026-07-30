"""Generate weekly blog posts from the topic queue using the Anthropic API.

Usage:
    ANTHROPIC_API_KEY=... python3 scripts/generate_article.py

Env vars:
    ANTHROPIC_API_KEY  required
    ARTICLE_MODEL      default: claude-haiku-4-5-20251001
    POSTS_PER_RUN      default: 2
"""
import datetime
import os
import sys
from pathlib import Path

import yaml
import anthropic

ROOT = Path(__file__).resolve().parent.parent
TOPICS_PATH = ROOT / "data" / "topics.yml"
POSTS_DIR = ROOT / "_posts"

MODEL = os.environ.get("ARTICLE_MODEL", "claude-haiku-4-5-20251001")
POSTS_PER_RUN = int(os.environ.get("POSTS_PER_RUN", "2"))
LOW_STOCK_WARNING_THRESHOLD = 4


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def generate_body(client, topic):
    prompt = f"""あなたは防災・ポータブル電源ジャンル専門のブログライターです。
以下のテーマで、読者の役に立つ日本語のブログ記事本文をMarkdown形式で書いてください。

タイトル: {topic['title']}
切り口: {topic.get('angle', '')}
キーワード: {', '.join(topic.get('keywords', []))}

条件:
- 見出し(##)を使って構成し、2000〜3000文字程度で書く
- 誇大表現や断定しすぎる安全性・防災効果の断言は避け、一般的な目安として書く
- 具体的な数値やチェックリストをできるだけ交える
- 特定の商品名を連呼せず、自然な文章にする（商品の詳細な紹介は別セクションで行うため本文では不要）
- タイトルの見出し(# {topic['title']})やMarkdownのフロントマターは出力しない。本文のみを出力する
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)

    topics = load_yaml(TOPICS_PATH)

    pending = [t for t in topics if t.get("status") == "pending"]
    if not pending:
        print("公開待ちのトピックがありません。data/topics.yml に追加してください。")
        return

    today = datetime.date.today()
    created_files = []

    for topic in pending[:POSTS_PER_RUN]:
        print(f"生成中: {topic['title']}")
        body = generate_body(client, topic)

        front_matter = {
            "title": topic["title"],
            "categories": [topic.get("category", "ポータブル電源・防災")],
            "products": topic.get("products", []),
        }
        front_matter_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False)
        content = f"---\n{front_matter_yaml}---\n\n{body}\n"

        filename = f"{today.isoformat()}-{topic['slug']}.md"
        path = POSTS_DIR / filename
        path.write_text(content, encoding="utf-8")
        created_files.append(path.name)

        topic["status"] = "published"
        topic["published_date"] = today.isoformat()

    save_yaml(TOPICS_PATH, topics)

    print("作成したファイル:")
    for name in created_files:
        print(f" - _posts/{name}")

    remaining_pending = len([t for t in topics if t.get("status") == "pending"])
    if remaining_pending < LOW_STOCK_WARNING_THRESHOLD:
        print(
            f"::warning::公開待ちトピックが残り{remaining_pending}件です。"
            " data/topics.yml にネタを追加してください。"
        )


if __name__ == "__main__":
    main()
