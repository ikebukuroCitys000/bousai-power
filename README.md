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

## Instagram（カルーセル・リール）のコンテンツ自動生成

`.github/workflows/instagram-content.yml` が毎日07:00 JSTに動き、`sns_drafts/` にInstagram下書きがまだ無いブログ記事を見つけて、Claude APIで**カルーセル投稿**と**リール投稿**の台本を自動生成します。さらに`OPENAI_API_KEY`を登録していれば、各スライドの**挿絵イラストも画像生成AI（gpt-image-1）で自動生成**され、Canvaの一括作成に直接差し込める状態まで自動化されます。**動画の制作、投稿そのものは手動**です。

### 生成される内容

- **カルーセル**: 必ず7枚固定（1枚目フック／2〜6枚目本文／7枚目CTA）＋各スライドの挿絵（画像生成AI）＋キャプション＋ハッシュタグ10〜15個。挿絵を生成する場合、**各スライドの見出しは太字・高コントラストのバナー付きで画像に直接焼き込み済み**（Pillowで合成。ポップで可愛いトーンに合わせて濃紺の角丸バナー＋白抜き文字）なので、Canva側で見出し用テキストを別途重ねる必要はありません
- **リール**: 15〜30秒想定のシーン割り（映像指示＋画面テキスト＋秒数）＋フック文＋キャプション＋ハッシュタグ

出力先は3つあります。

- `sns_drafts/<記事のスラッグ>-instagram.md` — 人が読む用の台本（カルーセル・リール両方、挿絵ファイルへのパス付き）
- `sns_drafts/images/<スラッグ>-slide<N>.png` — スライドごとに自動生成された挿絵（`OPENAI_API_KEY`未設定時は生成されない）
- `sns_drafts/canva_carousel.csv` — **Canvaの「一括作成(Bulk Create)」にそのまま読み込める横持ちCSV**（カルーセルのみ。1記事＝1行、実行のたびに追記・更新される。`slide{N}_image`列には生成した画像のURLが入る）

リールはCanva側にCSVからの動画自動生成の仕組みがないため、`.md`の台本を見ながらCapCut等で手動編集してください。

### 画像生成AIのセットアップ（挿絵の自動生成、任意）

1. [platform.openai.com](https://platform.openai.com/) でAPIキーを発行する（要アカウント登録・支払い方法の登録はご自身で行ってください）
2. リポジトリにSecretとして登録

```bash
gh secret set OPENAI_API_KEY --repo ikebukuroCitys000/bousai-power
```

（GitHub Web UIの Settings → Secrets and variables → Actions からでも登録可能です）

3. 未設定のままでもワークフローはエラーになりません。台本の`image_prompt`（挿絵の指示文）だけが出力され、Canvaのマジック生成に手動でコピペする従来フローに自動的にフォールバックします。

**コストの目安**（2026年時点のgpt-image-1料金、変動する可能性があるため[公式の料金ページ](https://platform.openai.com/docs/pricing)で要確認）: `IMAGE_QUALITY=low` の初期設定で1枚あたり約$0.01〜0.02。1記事7枚×週1〜数記事のペースなら月あたり数百円程度。画質を上げたい場合は環境変数 `IMAGE_QUALITY=medium` または `high` をワークフロー側に追加してください。

### Canva側の一度きりのセットアップ（カルーセル用）

1. Canvaで7ページのカルーセル用テンプレートを1つ作成する（Instagramの投稿サイズ 1080×1350等）
2. 各ページのテキスト枠を選択し、「データを接続」で以下のフィールド名をタグ付けする（`title`、`caption`、`hashtags` はお好みで配置）

   `OPENAI_API_KEY`を設定して挿絵を自動生成している場合、**見出し（`slide{N}_headline`）は既に画像の中に焼き込まれている**ので、Canva側は画像フィールドだけでOKです（本文は引き続きテキストフィールドとして重ねてください）。

   | ページ | 画像用フィールド | 本文用フィールド | 見出し用フィールド |
   |---|---|---|---|
   | 1枚目 | `slide1_image` | `slide1_body` | `slide1_headline`（画像生成ありなら不要） |
   | 2枚目 | `slide2_image` | `slide2_body` | `slide2_headline`（画像生成ありなら不要） |
   | … | … | … | … |
   | 7枚目 | `slide7_image` | `slide7_body` | `slide7_headline`（画像生成ありなら不要） |

   `OPENAI_API_KEY`未設定で挿絵が自動生成されていない記事の場合のみ、`slide{N}_headline`もテキストフィールドとしてタグ付けしてください（従来通りCanva側で見出しを重ねる形になります）。

   画像用フレームには、テキスト枠と同じ「データを接続」から画像プレースホルダーを選び、`slide{N}_image` を紐づけてください。CSVのその列には画像ファイルの公開URL（`https://raw.githubusercontent.com/...`）が入っているので、Canvaが自動的にURL先の画像を取得してフレームに差し込みます（手元でのアップロード操作は不要です）。`OPENAI_API_KEY`未設定で画像が生成されていない行はこの列が空になるので、その場合だけ手動で写真を入れてください。

3. テンプレート上部メニューの「一括作成」→「CSVをアップロード」から `sns_drafts/canva_carousel.csv` を選択
4. フィールドの対応が自動または手動で紐づいたら「生成」。**行(記事)ごとに7ページのカルーセルが挿絵込みで自動でまとめて出来上がります**
5. 生成後、実際の投稿前に一言二言、手直しをして仕上げてください

一度テンプレートを作ってしまえば、以降は新しい記事が増えるたびにCSVへ行が追記されるので、そのCSVを都度アップロードし直すだけで新規カルーセルが作れます。

### 手動実行・特定記事の再生成

```bash
# 未生成の記事だけまとめて処理（挿絵も生成する場合はOPENAI_API_KEYも渡す）
ANTHROPIC_API_KEY=sk-ant-... OPENAI_API_KEY=sk-... python3 scripts/generate_instagram_content.py

# 特定の記事だけ強制的に再生成したい場合（スラッグ = _postsのファイル名から.mdを除いたもの）
ANTHROPIC_API_KEY=sk-ant-... OPENAI_API_KEY=sk-... python3 scripts/generate_instagram_content.py 2026-07-30-capacity-calculation
```

GitHub Actionsから手動実行する場合は、Actionsタブの `Instagram content` ワークフローから `Run workflow` を押してください。

## タイムセール監視（自動）とSNS投稿（手動）

`.github/workflows/deal-watch.yml` が6時間ごとに動き、`_data/products.yml` に登録された商品の楽天価格を監視します。値下がりを検知すると、ブログ記事とSNS用の下書きテキストを自動生成しますが、**SNSへの投稿自体は手動**です（Xの有料API化・Instagramの審査コストを避けるため、あえて自動投稿はしていません）。

### 仕組み

```
6時間ごと（GitHub Actions cron）
  ↓
scripts/check_deals.py が楽天商品検索APIで現在価格を取得
  ↓
data/deal_watch_state.yml の前回価格と比較（10%以上の値下がりを検知）
  ↓
値下がりを検知した場合のみ：
  scripts/generate_deal_content.py が Claude API で
  ①速報ブログ記事 ②X用キャプション ③Instagram用キャプション を同時生成
  ↓
①は _posts/ に自動コミット→ブログに自動公開
②③は sns_drafts/ に下書きとして保存
  ↓
検知した商品ごとにGitHub Issueを自動作成（コピペ用の下書き付き）
  ↓
Issueの通知を見て、ご自身の手でXやInstagramに投稿
```

### セットアップ

1. [webservice.rakuten.co.jp/app/create](https://webservice.rakuten.co.jp/app/create) でアプリを新規作成
2. 発行された **アプリID(applicationId)** と **アクセスキー(accessKey)** を控える
3. リポジトリに以下の2つをSecretsとして登録

```bash
gh secret set RAKUTEN_APPLICATION_ID --repo ikebukuroCitys000/bousai-power
gh secret set RAKUTEN_ACCESS_KEY --repo ikebukuroCitys000/bousai-power
```

（GitHub Web UIの Settings → Secrets and variables → Actions からでも登録可能です）

### 運用時の注意

- **初回実行時は「基準価格」を記録するだけで、値下がり検知はされません。** 2回目以降の実行から比較が始まります。
- 値下がり判定の閾値は環境変数 `DEAL_DROP_THRESHOLD`（デフォルト0.1 = 10%）で調整できます。
- 楽天の同一商品を継続して追跡できるよう、初回に検索でヒットした商品（itemCode）を `data/deal_watch_state.yml` に固定します。検索結果の順位変動で別の商品にすり替わることはありません。
- Amazon側は、PA-APIが2026年5月に廃止され後継の「Creators API」に移行しましたが、**過去30日以内の売上実績がないとアクセスできない**仕様のため、現時点では未実装です（レポート内 §07 参照）。Amazonアソシエイトで売上が立ち始めた段階で追加を検討してください。
- SNS投稿を自動化したくなった場合は、X APIの有料プラン契約・Instagram Graph APIのMeta審査（画像生成の仕組みも別途必要）が必要になります。

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
