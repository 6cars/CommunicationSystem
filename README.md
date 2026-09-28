# カウンセリング・エージェント（失敗経験のポジティブ・リフレーミング支援）

ユーザとチャット形式で対話し、失敗経験を尋ねたうえで、その失敗経験と関係する肯定的な経験（関連経験）を想起させる Web アプリケーションです。

- フロントエンド: Next.js 14 / React / Tailwind CSS（`frontend/`）
- バックエンド: Python / Django + Django REST framework（`backend/`）
- LLM: OpenAI API（既定モデル `gpt-4o`。`LLM_PROVIDER=anthropic` で Claude API にも切り替え可）。**経験想起支援機能（「思いつかない」を押したときの具体例生成）でのみ使用**し、質問文はテンプレートから作ります
- データ保存: PostgreSQL（ローカルでの確認用に SQLite も選べます）

## 構成

| 仕様の構成要素 | 実装 |
|---|---|
| インタフェース | `frontend/app/page.tsx`, `frontend/components/*` |
| 対話制御部（ステートマシン） | `backend/counseling/dialogue/states.py`（状態と遷移表）, `backend/counseling/dialogue/controller.py` |
| 経験想起支援機能 | `backend/counseling/dialogue/recall_support.py` |
| 経験DB | `backend/counseling/models.py` の `Experience` |
| ログ | `Message`（全発話・フェーズ・要素・応答種別）, `RecallSupportLog`（プロンプト全文・LLM出力・何回目か）, 出力は `backend/counseling/export.py` |
| 質問文テンプレート | `backend/prompts/questions.json` |
| 具体例生成のプロンプトテンプレート | `backend/prompts/recall_support/<要素>.txt` |

状態と遷移の一覧は [docs/state_machine.md](docs/state_machine.md) にあります。

## セットアップと起動（Docker Compose）

1. リポジトリ直下に `.env` を作り、OpenAI の API キーを書きます（`.env` は Git 管理外です）。

   ```
   OPENAI_API_KEY=sk-proj-...
   ```

   シェルで `export OPENAI_API_KEY=...` してから起動しても構いません。

2. 起動します。

   ```bash
   docker compose up --build
   ```

   バックエンドは起動時に `python manage.py migrate` を実行します。

3. ブラウザで http://localhost:3000 を開きます。
   - 一般ユーザ: ログイン画面で新規登録してチャットを開始
   - 管理者: お名前 `admin` / パスワード `admin` でログインすると管理画面（ユーザ・セッション一覧、対話ログ、ログ出力）

## 環境変数

`.env.dev`（Compose が読み込む）に既定値があります。

| 変数 | 既定値 | 説明 |
|---|---|---|
| `OPENAI_API_KEY` | （なし） | OpenAI API キー。`.env` またはシェルの環境変数で渡す |
| `LLM_PROVIDER` | `openai` | `openai`: OpenAI API / `anthropic`: Claude API / `mock`: API を呼ばず固定の具体例を返す（動作確認用） |
| `LLM_MODEL` | `gpt-4o` | 具体例生成に使うモデル（未指定時は `openai` なら `gpt-4o`、`anthropic` なら `claude-opus-5`） |
| `LLM_MAX_TOKENS` | `4000` | 最大出力トークン数 |
| `LLM_TIMEOUT_SECONDS` | `60` | API 呼び出しのタイムアウト（秒） |
| `ANTHROPIC_API_KEY` | （なし） | `LLM_PROVIDER=anthropic` のときの Claude API キー |
| `LLM_EFFORT` | `low` | `anthropic` のときのみ。Claude の effort。空にすると指定しません |
| `LLM_USE_FALLBACKS` | `1` | `anthropic` のときのみ。応答が拒否された場合にサーバ側で別モデルに切り替えて再実行する |
| `PROMPTS_DIR` | `backend/prompts` | テンプレートの置き場所 |
| `DB_ENGINE` | `postgresql` | `sqlite` にすると `backend/db.sqlite3`（または `SQLITE_PATH`）を使う |
| `POSTGRES_*` | `.env.dev` 参照 | PostgreSQL の接続情報 |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | フロントエンドから見たバックエンドの URL |

具体例の生成に失敗したとき（API キー未設定、通信エラーなど）は、チャットに「具体例を用意できませんでした」と表示して同じ質問のまま応答を待ち、エラー内容を `RecallSupportLog.error` に記録します。

## Docker を使わずに起動する

```bash
# バックエンド
cd backend
pip install -r ../docker_files/backend/requirements.txt
export DB_ENGINE=sqlite OPENAI_API_KEY=sk-proj-...   # API を使わずに試すなら LLM_PROVIDER=mock
python manage.py migrate
python manage.py runserver 8000

# フロントエンド（別ターミナル）
cd frontend
npm install
npm run dev
```

## テスト（仕様 8章の動作確認）

仕様 8章の対話と分岐をテストにしています（LLM はモック）。

```bash
cd backend
DB_ENGINE=sqlite python manage.py test counseling
```

確認している内容:
- 基本の対話: 失敗経験5要素 → 関連経験の最初の質問で「思いつかない」→ 具体例 → 「遅れた理由を冗談っぽく話した」→ 事後状態・事後思想 → 評価「はい」→ 起点の提示で終了
- 省略不可の質問（失敗経験の行動・事後状態、再想起の事後状態、評価）で「特にない」が受け付けられないこと
- 「思いつかない」を繰り返すと、前回までの具体例がプロンプトに含まれ、毎回異なる具体例が出ること
- 種類1で「特にない」→ 種類2の質問に進むこと（失敗経験の事後思想がなければ再想起フェーズへ）
- 種類2も「特にない」→ 失敗経験再想起フェーズに進み、新たな事後状態で種類1の質問が作られること
- 評価で「いいえ」→ 種類1の別の行動を尋ねること
- ログの JSON / CSV 出力

## テンプレートの編集

テンプレートは呼び出しのたびにファイルから読み込むので、編集はサーバを再起動しなくても反映されます。

### 質問文（`backend/prompts/questions.json`）

キーは状態名（[docs/state_machine.md](docs/state_machine.md)）です。ほかに `greeting`（冒頭の挨拶、リスト）、`origin_type1` / `origin_type2`（起点の提示）、`closing`（終了のあいさつ）、`recall_support_error`（具体例の生成に失敗したとき）、`session_completed`（終了後に応答が来たとき）があります。

### 具体例生成のプロンプト（`backend/prompts/recall_support/`）

尋ねる要素ごとに1ファイルです（ファイル名＝状態名）。各テンプレートは仕様 5章の5部分（①役割と生成内容 ②要素の定義 ③これまでの回答 ④尋ねている要素と関係 ⑤出力形式）で構成しています。

2回目以降の具体例生成では、`{previous_examples_section}` の位置に `_previous_examples.txt` の内容（それまでに提示した具体例の一覧と「異なる例を作る」指示）が入ります。1回目は空になります。

LLM の出力は、最初の空でない行を1文の問いかけとしてチャットに表示します（生の出力は `RecallSupportLog.raw_output` に残ります）。

### テンプレート変数

質問文・プロンプトの両方で使えます。値が空の要素は「未回答」に置き換わります。

| 変数 | 内容 |
|---|---|
| `{failure_action}` | 失敗経験の行動 |
| `{failure_pre_state}` | 失敗経験の事前状態（複数あれば「／」区切り。再想起で追加されたものを含む） |
| `{failure_post_state}` | 失敗経験の事後状態（同上） |
| `{current_failure_post_state}` | 失敗経験の最新の事後状態（種類1の質問で使う。再想起後は新しい事後状態） |
| `{failure_pre_thought}` / `{failure_post_thought}` | 失敗経験の事前思想 / 事後思想 |
| `{related_action}` | 想起中の関連経験の行動（種類2では「事前状態と行動」の回答） |
| `{related_pre_state}` | 関連経験の事前状態（種類1では失敗経験の事後状態） |
| `{related_post_state}` / `{related_post_thought}` | 関連経験の事後状態 / 事後思想 |
| `{related_pre_thought}` | 関連経験の事前思想（種類2では失敗経験の事後思想） |
| `{related_pre_state_and_action}` | 種類2の「事前状態と行動」の回答 |
| `{origin_failure_post_state}` | 起点の提示（種類1）で使う、その関連経験の起点になった失敗経験の事後状態 |
| `{user_name}` | ユーザ名（`greeting` のみ） |
| `{previous_examples}` | それまでに提示した具体例の一覧（`_previous_examples.txt` のみ） |

## ログ（評価実験用）

管理画面のセッション詳細から、そのセッションのログを JSON / CSV でダウンロードできます。ヘッダの「全セッションのログ (JSON)」で全セッション分を出力します。API を直接呼ぶこともできます。

```
GET /api/admin/sessions/<session_id>/export/?format=json
GET /api/admin/sessions/<session_id>/export/?format=csv&table=utterances
GET /api/admin/export/?format=json                     # 全セッション
GET /api/admin/export/?format=csv&table=experiences&user_id=user_001
```

JSON にはセッションごとに次が入ります。

- `utterances`: 全発話（話者、本文、時刻、フェーズ、尋ねていた要素、ユーザの応答種別 `answer`/`dont_know`/`nothing`、エージェント発話の種類 `greeting`/`question`/`example`/`notice`/`origin`/`closing`）
- `recall_support_calls`: 経験想起支援機能の呼び出し（入力したプロンプト全文、LLM の生出力と表示した出力、何回目の具体例か、モデル、エラー）
- `failure_experience` / `related_experiences`: 最終的に得られた失敗経験・関連経験の全要素
- `evaluation_results`, `positive_related_experience_id`: 評価の結果

CSV は `table` で3種類（`utterances`: 発話、`recall_support`: 具体例生成、`experiences`: 経験DB）に分かれます。Excel で開けるよう BOM 付き UTF-8 です。

## 補足

- 管理者 API（`/api/admin/...`）には認証がかかっていません（既存の設計のまま）。外部に公開する場合は保護してください。
- 対話中にページを再読み込みすると新しいセッションが始まります。
