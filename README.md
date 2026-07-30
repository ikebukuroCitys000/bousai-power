# 防災ポータブル電源ラボ

ポータブル電源・防災グッズの選び方や比較情報を発信するアフィリエイトブログです。
毎週、Claude APIが記事の下書きを生成し、GitHub Pagesで公開します。

## 仕組み

```
毎週月曜 06:00 JST（GitHub Actions cron）
  ↓
scripts/generate_article.py が data/topics.yml から次の記事ネタを取得
  ↓
Claude API（Haiku 4.5）が記事本文を生成
  ↓
記事のフロントマターに関連商品のkeyを記録（例: products: [jackery_1000]）
  ↓
_posts/ に Markdown ファイルを作成し、GitHub にコミット・プッシュ
  ↓
GitHub Pages が自動的に再ビルドして公開
```

サイトは Jekyll（GitHub Pages 標準機能）でビルドされます。ローカルでのビルドは不要です。

**「関連商品」セクションは記事ファイルに直接書き込まれるのではなく、`_data/products.yml` を毎回のビルド時に参照して表示されます。** そのため `_data/products.yml` の1箇所を編集するだけで、過去に公開済みの記事も含めて全記事のリンクが一括で更新されます（審査通過後にリンクを差し替える際、記事を1本ずつ直す必要はありません）。

## 月あたりのコスト目安

Claude Haiku 4.5（入力 $1 / 100万トークン、出力 $5 / 100万トークン）で、
1回あたり入力500トークン・出力4000トークン、週2記事のペースで生成した場合：

- 週あたり: 入力1,000トークン + 出力8,000トークン ≈ $0.04
- 月あたり: 約 $0.17（1ドル145円換算で約25円）

GitHub・GitHub Pagesは無料です。実質的なランニングコストはClaude APIの従量課金のみで、
月100円以下に収まる計算です。

## セットアップ手順

### 1. GitHubリポジトリを作成してプッシュ

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create <リポジトリ名> --public --source=. --push
```

### 2. GitHub Pagesを有効化

リポジトリの Settings → Pages で、Source を「Deploy from a branch」、
Branch を `main` / `/ (root)` に設定してください。

### 3. `_config.yml` の `url` / `baseurl`

公開URL: https://ikebukuroCitys000.github.io/bousai-power/ （設定済み）

### 4. Claude APIキーをGitHub Secretsに登録

Settings → Secrets and variables → Actions → New repository secret で、
`ANTHROPIC_API_KEY` という名前でAPIキーを登録してください。

### 5. 動作確認

Actions タブから `Weekly article generation` ワークフローを手動実行（workflow_dispatch）して、
記事が生成・コミットされることを確認してください。

## Amazon・楽天アフィリエイトの設定（審査通過後の反映方法）

`_data/products.yml` の `amazon_url` / `rakuten_url` は商品ページ・検索結果への通常URLです。
トラッキングID自体は個別のURLではなく `_config.yml` に一元管理しており、ビルド時に全商品リンクへ自動付与されます。

```yaml
# Amazonアソシエイト・トラッキングID（全Amazonリンクの末尾に &tag=... として自動付与）
amazon_associate_tag: "bababauru-22"

# 楽天アフィリエイトID（「どこでもリンク」形式 https://hb.afl.rakuten.co.jp/hgc/{ID}/?pc=... で全楽天リンクをラップ）
rakuten_affiliate_id: "562f878b.0286961a.562f878c.30d1c03c"
```

IDを変更・更新したい場合は、この2行を書き換えてコミット・プッシュするだけで、既存記事・新規記事の両方に反映されます。
（楽天IDは affiliate.rakuten.co.jp で何らかのリンクを1つ生成し、`https://hb.afl.rakuten.co.jp/hgc/`の直後から次の`/`までの文字列を控えれば確認できます。実際にリダイレクトを辿って `scid=af_pc_etc` 等の追跡パラメータが付与されることを確認済みです。）

審査は一定量のコンテンツがあるサイトの方が通りやすいため、記事が数本公開された状態で申し込むことを推奨します。
Amazonアソシエイトは登録後180日以内に一定件数の売上がないとアカウントがクローズされる規定があるため、
申込みのタイミングは計画的に。

## 商品リンクの追加方法（新しい商品を紹介したいとき）

1. `_data/products.yml` に新しいエントリを追加する

```yaml
- key: 一意の識別子（英数字とアンダースコアのみ）
  name: 商品名
  note: 一言紹介文（任意）
  amazon_url: "https://..."
  rakuten_url: "https://..."
```

2. `data/topics.yml` の該当トピックの `products:` にその `key` を追加する（新規生成される記事に反映）
3. 既存の記事に追加したい場合は、その記事ファイルのフロントマターにある `products:` に `key` を追加する

```yaml
---
title: "..."
categories: [...]
products: [jackery_1000, ecoflow_river2, 追加したkey]
---
```

## 画像の入れ方

現在の生成スクリプトはテキストのみを生成し、画像は自動生成しません。画像を追加したい場合は以下の方法があります。

- **商品画像**: Amazon・楽天それぞれのアフィリエイト管理画面には、審査通過後に「バナー画像＋アフィリエイトリンク」を自動生成してくれる機能があります（Amazonの場合はSiteStripe、楽天の場合はリンク自動作成ツール）。この画像はそのまま利用が許諾されているため、Amazon商品ページの画像を直接保存して使うより安全です。
- **記事の挿絵・オリジナル画像**: `assets/images/` フォルダを作成し、画像ファイルを置いた上で、記事のMarkdown本文に以下のように記述します。

```markdown
![説明文]({{ '/assets/images/ファイル名.jpg' | relative_url }})
```

`{{ '...' | relative_url }}` を付けることで、`baseurl`（`/bousai-power`）が自動的に付与され、正しいパスになります。単純な `![説明文](/assets/images/xxx.jpg)` だと、パスがズレて表示されないのでご注意ください。

## 法令・規約上必須の対応（すでに反映済み）

- **アフィリエイト表記**: 全記事の先頭に「本記事はアフィリエイト広告を含みます」バナーを自動挿入（`_includes/disclosure-banner.html`）。日本のステルスマーケティング規制（景品表示法）対応。
- **広告・アフィリエイト表記ページ**: `/disclosure/`
- **プライバシーポリシー**: `/privacy-policy/`

Amazon・楽天それぞれの規約で要求される正確な文言は変更されることがあるため、
審査通過時に各プログラムの最新ガイドラインを確認し、必要であれば文言を調整してください。

## 記事ネタを追加する

`data/topics.yml` に以下の形式でエントリを追加してください。

```yaml
- slug: url-slug-here
  title: 記事タイトル
  angle: どんな切り口で書くか
  keywords: [キーワード1, キーワード2]
  category: カテゴリ名
  products: [_data/products.ymlのkeyを列挙]
  status: pending
```

`status: pending` のものから順に公開され、公開後は自動的に `status: published` に更新されます。
残りが4件を下回るとGitHub Actionsのログに警告が出るので、その前に追加してください。

## ローカルでのスクリプトテスト

```bash
python3 -m venv venv
./venv/bin/python3 -m pip install -r requirements.txt
ANTHROPIC_API_KEY=sk-ant-... ./venv/bin/python3 scripts/generate_article.py
```
