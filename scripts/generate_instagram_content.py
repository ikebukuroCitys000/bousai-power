"""Generate Instagram carousel + Reels content drafts from blog posts.

For each post under _posts/ that doesn't yet have a matching Instagram
draft, asks Claude to turn the article into:
  - a carousel slide breakdown (headline + short body per slide) + caption + hashtags
  - a Reels shooting script (hook + scene-by-scene) + caption + hashtags

If OPENAI_API_KEY is set, each carousel slide's image_prompt is also sent
to an image-generation model (gpt-image-1) to actually produce the
illustration, saved under sns_drafts/images/ and committed to the repo.
Since this repo is public, the committed PNGs are reachable at a
raw.githubusercontent.com URL — that URL is written into the
slide{N}_image column of canva_carousel.csv, and Canva's "Bulk create"
can pull an image directly from a URL in an image-type field. So once
the Canva template has image placeholders tagged, no manual image
upload/paste step is needed. If OPENAI_API_KEY is not set, image
generation is skipped and only the text image_prompt is produced (for
manual use in Canva's Magic Media).

Video editing/filming (e.g. in CapCut) and posting itself stay manual.

Carousel slide count is fixed at 7 (hook, 5x body, CTA) so the output
also lands in sns_drafts/canva_carousel.csv in wide format — one row
per post, with a slide1_headline/slide1_body/slide1_image ... slide7_*
column set per slide. Build a matching 7-frame Canva template with
those field names tagged (image fields as "image" type), then use
Canva's "Bulk create" to generate all slides for all posts in one pass.
Reels have no Canva equivalent (no CSV-driven video timeline), so those
stay in the per-post .md file only.

Usage:
    ANTHROPIC_API_KEY=... python3 scripts/generate_instagram_content.py
    ANTHROPIC_API_KEY=... OPENAI_API_KEY=... python3 scripts/generate_instagram_content.py
    ANTHROPIC_API_KEY=... python3 scripts/generate_instagram_content.py <slug> [<slug> ...]

With no arguments, processes every post in _posts/ that doesn't already
have a sns_drafts/<slug>-instagram.md file. Pass one or more slugs
(the post filename without the .md extension) to force regeneration for
specific posts.
"""
import base64
import csv
import json
import os
import re
import sys
from pathlib import Path

import anthropic
import yaml

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "_posts"
DRAFTS_DIR = ROOT / "sns_drafts"
CANVA_CSV_PATH = DRAFTS_DIR / "canva_carousel.csv"
IMAGES_DIR = DRAFTS_DIR / "images"

MODEL = os.environ.get("ARTICLE_MODEL", "claude-haiku-4-5-20251001")

SLIDE_COUNT = 7  # 1:フック 2-6:本文 7:CTA。Canvaの固定7枚テンプレートに合わせる

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-1")
IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "1024x1536")  # 縦長。IGカルーセル比率に近い
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "low")  # コスト優先。要望あればmedium/highに

# コミット済み画像を参照する公開URLのベース（このリポジトリはpublicなのでraw経由で取得可能）
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/ikebukuroCitys000/bousai-power/main"

INSTAGRAM_SCHEMA = {
    "type": "object",
    "properties": {
        "carousel": {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    # 構造化出力のJSON SchemaはminItems/maxItemsに0/1以外を指定できない
                    # （2に設定しただけで400になる）。枚数はプロンプト指示＋実行時の
                    # 補正（pad_or_trim_slides）で7枚に揃える。
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "body": {"type": "string"},
                            "image_prompt": {"type": "string"},
                        },
                        "required": ["headline", "body", "image_prompt"],
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
- スライドは必ずちょうど7枚（Canvaの固定テンプレートに流し込むため、多くても少なくてもいけない）
- 1枚目は「保存したくなる」フック（数字・断言・意外性のいずれかを使う）
- 2〜6枚目は記事の要点を1スライド1メッセージで区切る（見出し10〜16文字程度、本文は1〜2文で簡潔に）
- 7枚目は「保存」「フォロー」「プロフィールのリンクへ」等の行動喚起
- 各スライドの image_prompt には、その内容を視覚的に補うイラスト・写真の指示を1文で書く（例:「停電した部屋でスマホの充電が切れて困っている人のフラットイラスト」）。実在の人物・商標ロゴを指定しない。Canvaの画像生成（マジック生成）にそのまま使える具体性を持たせる
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
    content = json.loads(text)
    content["carousel"]["slides"] = pad_or_trim_slides(content["carousel"]["slides"])
    return content


def generate_slide_images(image_client, slug, slides):
    """image_promptから実際にイラストを生成し、slides各要素に image_file
    （ファイル名。失敗時は空文字）を追加する。image_clientがNoneなら何もしない。"""
    if image_client is None:
        for slide in slides:
            slide["image_file"] = ""
        return slides

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for i, slide in enumerate(slides, start=1):
        filename = f"{slug}-slide{i}.png"
        out_path = IMAGES_DIR / filename
        try:
            response = image_client.images.generate(
                model=IMAGE_MODEL,
                prompt=(
                    f"{slide['image_prompt']}。"
                    "フラットデザインのイラスト、Instagramカルーセル投稿の挿絵として使う、"
                    "文字は入れない、実在の人物や商標ロゴは描かない。"
                ),
                size=IMAGE_SIZE,
                quality=IMAGE_QUALITY,
                n=1,
            )
            image_bytes = base64.b64decode(response.data[0].b64_json)
            out_path.write_bytes(image_bytes)
            slide["image_file"] = filename
        except Exception as exc:  # noqa: BLE001 — 1枚失敗しても他のスライド生成は続ける
            print(f"警告: 画像生成に失敗しました（{filename}）: {exc}")
            slide["image_file"] = ""
    return slides


def pad_or_trim_slides(slides):
    """スキーマでは強制できないため、7枚ちょうどになるよう実行時に揃える。"""
    slides = list(slides[:SLIDE_COUNT])
    while len(slides) < SLIDE_COUNT:
        slides.append({
            "headline": "続きはブログで",
            "body": "詳しくはプロフィールのリンクからブログ記事をご覧ください。",
            "image_prompt": "プロフィールリンクを指差すシンプルなイラスト",
        })
    return slides


def render_draft(slug, title, content):
    lines = [f"# {title}", "", "## カルーセル投稿", ""]
    for i, slide in enumerate(content["carousel"]["slides"], start=1):
        lines.append(f"**スライド{i}: {slide['headline']}**")
        lines.append(slide["body"])
        lines.append(f"_挿絵の指示: {slide['image_prompt']}_")
        if slide.get("image_file"):
            lines.append(f"_挿絵ファイル（自動生成済み）: sns_drafts/images/{slide['image_file']}_")
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


def csv_fieldnames():
    fields = ["post_slug", "title"]
    for i in range(1, SLIDE_COUNT + 1):
        fields += [
            f"slide{i}_headline",
            f"slide{i}_body",
            f"slide{i}_image_prompt",
            f"slide{i}_image",
        ]
    fields += ["caption", "hashtags"]
    return fields


def csv_row_for(slug, title, content):
    row = {"post_slug": slug, "title": title}
    for i, slide in enumerate(content["carousel"]["slides"], start=1):
        row[f"slide{i}_headline"] = slide["headline"]
        row[f"slide{i}_body"] = slide["body"]
        row[f"slide{i}_image_prompt"] = slide["image_prompt"]
        image_file = slide.get("image_file")
        row[f"slide{i}_image"] = f"{GITHUB_RAW_BASE}/sns_drafts/images/{image_file}" if image_file else ""
    row["caption"] = content["carousel"]["caption"]
    row["hashtags"] = " ".join(content["carousel"]["hashtags"])
    return row


def update_canva_csv(rows_by_slug):
    """Canvaの「Bulk create」にそのまま読み込める横持ちCSVを、
    post_slugをキーに追記/上書きする（既存行は保持したまま更新）。"""
    fieldnames = csv_fieldnames()
    existing = {}
    if CANVA_CSV_PATH.exists():
        with open(CANVA_CSV_PATH, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing[row["post_slug"]] = row

    existing.update(rows_by_slug)

    with open(CANVA_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing.values():
            writer.writerow(row)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    image_client = None
    if openai_api_key and OpenAI is not None:
        image_client = OpenAI(api_key=openai_api_key)
    elif openai_api_key and OpenAI is None:
        print("警告: openaiパッケージが未インストールのため画像生成をスキップします（pip install -r requirements.txt）")
    else:
        print("OPENAI_API_KEY未設定のため、挿絵の自動生成はスキップします（image_promptのテキストのみ生成）")

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
    csv_rows = {}

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
        content["carousel"]["slides"] = generate_slide_images(image_client, slug, content["carousel"]["slides"])
        draft_text = render_draft(slug, title, content)

        draft_path = DRAFTS_DIR / f"{slug}-instagram.md"
        draft_path.write_text(draft_text, encoding="utf-8")
        created.append(draft_path.name)
        csv_rows[slug] = csv_row_for(slug, title, content)

    if csv_rows:
        update_canva_csv(csv_rows)

    print("作成したInstagram下書き:")
    for name in created:
        print(f" - sns_drafts/{name}")
    if csv_rows:
        print(f" - sns_drafts/canva_carousel.csv （{len(csv_rows)}件を追記/更新）")


if __name__ == "__main__":
    main()
