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
data/products.yml の商品情報を使って「関連商品」セクションを自動挿入
  ↓
_posts/ に Markdown ファイルを作成し、GitHub にコミット・プッシュ
  ↓
GitHub Pages が自動的に再ビルドして公開
```

サイトは Jekyll（GitHub Pages 標準機能）でビルドされます。ローカルでのビルドは不要です。

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

### 3. `_config.yml` の `url` を更新

公開URL（`https://<ユーザー名>.github.io/<リポジトリ名>`）を `url:` に設定してください。

### 4. Claude APIキーをGitHub Secretsに登録

Settings → Secrets and variables → Actions → New repository secret で、
`ANTHROPIC_API_KEY` という名前でAPIキーを登録してください。

### 5. 動作確認

Actions タブから `Weekly article generation` ワークフローを手動実行（workflow_dispatch）して、
記事が生成・コミットされることを確認してください。

## Amazon・楽天アフィリエイトの反映

`data/products.yml` の `amazon_url` / `rakuten_url` は、審査が通るまでの
**非アフィリエイトの検索リンク**です。審査通過後、以下の手順で本番リンクに差し替えてください。

- **Amazon アソシエイト**: 管理画面でリンクを生成し、`amazon_url` を発行されたトラッキング付きURLに置き換える
- **楽天アフィリエイト**: 「リンク自動作成」機能で発行されたリンクに置き換える

審査は一定量のコンテンツがあるサイトの方が通りやすいため、記事が数本公開された状態で申し込むことを推奨します。
Amazonアソシエイトは登録後180日以内に一定件数の売上がないとアカウントがクローズされる規定があるため、
申込みのタイミングは計画的に。

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
  products: [products.ymlのkeyを列挙]
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
