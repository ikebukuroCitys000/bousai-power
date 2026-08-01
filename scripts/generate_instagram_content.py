"""Generate Instagram carousel + Reels content drafts from blog posts.

For each post under _posts/ that doesn't yet have a matching Instagram
draft, asks Claude to turn the article into:
  - a carousel slide breakdown (headline + short body per slide) + caption + hashtags
  - a Reels shooting script (hook + scene-by-scene) + caption + hashtags

This only produces the *content* to build from — actual slide design
(e.g. in Canva) and video editing/filming (e.g. in CapCut) stay manual,
and so does posting itself.

Usage:
    ANTHROPIC_API_KEY=... python3 scripts/generate_instagram_content.py
    ANTHROPIC_API_KEY=... python3 scripts/generate_instagram_content.py <slug> [<slug> ...]

With no arguments, processes every post in _posts/ that doesn't already
have a sns_drafts/<slug>-instagram.md file. Pass one or more slugs
(the post filename without the .md extension) to force regeneration for
specific posts.
"""
import json
import os
import re
import sys
from pathlib import Path

import anthropic
import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "_posts"
DRAFTS_DIR = ROOT / "sns_drafts"

MODEL = os.environ.get("ARTICLE_MODEL", "claude-haiku-4-5-20251001")

INSTAGRAM_SCHEMA = {
    "type": "object",
    "properties": {
        "carousel": {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["headline", "body"],
                        "additionalProperties": False,
                    },
                },
                "caption": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["slides", "caption", "hashtags"],
            "additionalProperties": False,
        },
        "reel": {
            "type": "object",
            "properties": {
                "hook": {"type": "string"},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "visual": {"type": "string"},
                            "on_screen_text": {"type": "string"},
                            "duration_sec": {"type": "integer"},
                        },
                        "required": ["visual", "on_screen_text", "duration_sec"],
                        "additionalProperties": False,
                    },
                },
                "caption": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["hook", "scenes", "caption", "hashtags"],
            "additionalProperties": False,
        },
    },
    "required": ["carousel", "reel"],
    "additionalProperties": False,
}

# ジャンル定番＋ニッチ特化のハッシュタグの目安（Claudeへの参考例として渡す）
HASHTAG_REFERENCE = [
    "#防災", "#防災グッズ", "#防災対策", "#防災備蓄", "#備蓄",
    "#ポータブル電源", "#Jackery", "#EcoFlow", "#Anker",
    "#フェーズフリー", "#ローリングストック", "#防災リュック",
    "#車中泊", "#キャンプ初心者", "#暮らしの知恵", "#一人暮らし防災",
]


def parse_post(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n\n?(.*)$", text, re.DOTALL)
    if not m:
        return None
    front_matter = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return front_matter, body


def generate_instagram_content(client, title, body):
    prompt = f"""あなたは防災・ポータブル電源ジャンルのInstagram運用担当です。
以下のブログ記事をもとに、Instagramの「カルーセル投稿」と「リール(Reels)投稿」の台本を作成してください。

# カルーセル投稿の条件
- スライドは6〜8枚
- 1枚目は「保存したくなる」フック（数字・断言・意外性のいずれかを使う）
- 2枚目以降は記事の要点を1スライド1メッセージで区切る（見出し10〜16文字程度、本文は1〜2文で簡潔に）
- 最後のスライドは「保存」「フォロー」「プロフィールのリンクへ」等の行動喚起
- キャプションは記事の要約＋一言の共感/問いかけ、200文字程度
- ハッシュタグは10〜15個。大きいタグ（フォロワー数が多い一般的なタグ）とニッチなタグを混ぜる。参考例: {', '.join(HASHTAG_REFERENCE)}（これに限らず記事内容に合うものを自由に含めてよい）

# リール投稿の条件
- 尺は15〜30秒を想定し、シーンは4〜7個
- hookは最初の1〜2秒で使う一言（画面に出す文字、または最初のセリフ）。「え、知らなかった」と思わせる切り口にする
- 各シーンはvisual（画面に映すもの・動作の指示）、on_screen_text（画面内テキスト）、duration_sec（秒数の目安）を含める
- 誇張しすぎず、記事の内容に基づいた実用的な情報にする
- キャプション・ハッシュタグはカルーセルと同じ条件

# 元記事
タイトル: {title}

本文:
{body}
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        output_config={"format": {"type": "json_schema", "schema": INSTAGRAM_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def render_draft(slug, title, content):
    lines = [f"# {title}", "", "## カルーセル投稿", ""]
    for i, slide in enumerate(content["carousel"]["slides"], start=1):
        lines.append(f"**スライド{i}: {slide['headline']}**")
        lines.append(slide["body"])
        lines.append("")
    lines.append("**キャプション**")
    lines.append(content["carousel"]["caption"])
    lines.append("")
    lines.append("**ハッシュタグ**")
    lines.append(" ".join(content["carousel"]["hashtags"]))
    lines.append("")
    lines.append("## リール投稿")
    lines.append("")
    lines.append(f"**フック(最初の1〜2秒)**: {content['reel']['hook']}")
    lines.append("")
    for i, scene in enumerate(content["reel"]["scenes"], start=1):
        lines.append(f"**シーン{i}（約{scene['duration_sec']}秒）**")
        lines.append(f"- 映像: {scene['visual']}")
        lines.append(f"- 画面テキスト: {scene['on_screen_text']}")
        lines.append("")
    lines.append("**キャプション**")
    lines.append(content["reel"]["caption"])
    lines.append("")
    lines.append("**ハッシュタグ**")
    lines.append(" ".join(content["reel"]["hashtags"]))
    lines.append("")
    return "\n".join(lines)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")

    requested_slugs = sys.argv[1:]
    DRAFTS_DIR.mkdir(exist_ok=True)

    if requested_slugs:
        targets = [POSTS_DIR / f"{slug}.md" for slug in requested_slugs]
        targets = [p for p in targets if p.exists()]
    else:
        targets = []
        for path in sorted(POSTS_DIR.glob("*.md")):
            slug = path.stem
            draft_path = DRAFTS_DIR / f"{slug}-instagram.md"
            if not draft_path.exists():
                targets.append(path)

    if not targets:
        print("生成対象の記事がありません（すべて生成済み、または_posts/が空です）。")
        return

    client = anthropic.Anthropic(api_key=api_key)
    created = []

    for path in targets:
        parsed = parse_post(path)
        if not parsed:
            print(f"警告: {path.name} のフロントマターを読み取れませんでした")
            continue
        front_matter, body = parsed
        title = front_matter.get("title", path.stem)
        slug = path.stem

        print(f"生成中: {title}")
        content = generate_instagram_content(client, title, body)
        draft_text = render_draft(slug, title, content)

        draft_path = DRAFTS_DIR / f"{slug}-instagram.md"
        draft_path.write_text(draft_text, encoding="utf-8")
        created.append(draft_path.name)

    print("作成したInstagram下書き:")
    for name in created:
        print(f" - sns_drafts/{name}")


if __name__ == "__main__":
    main()
