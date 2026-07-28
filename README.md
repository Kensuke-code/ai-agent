# ai-agent
Custom AI Agent

Claude Agent SDK (Python) を使って、コンテナ内で `agent.py` を動かすプロジェクト。

## セットアップ

依存関係は `uv` (`pyproject.toml` + `uv.lock`) で管理している。

```bash
docker compose build
docker compose up -d
docker compose exec agent-app bash
```

コンテナは `sleep infinity` で起動したままになるので、入った後に好きなタイミングで実行する。

```bash
uv run python agent.py
```

## 認証(API課金ではなくPro/Maxプランを使う)

`ANTHROPIC_API_KEY` はAnthropic ConsoleのAPI従量課金で、Pro/Maxプランの利用枠とは別会計。Pro/Max分を使いたい場合は設定しない。

1. ホスト側で1度だけOAuthトークンを発行: `claude setup-token`
2. `.env` に `ANTHROPIC_API_KEY` は書かず、発行されたトークンを設定: `CLAUDE_CODE_OAUTH_TOKEN=<setup-tokenで発行された値>`

`ANTHROPIC_API_KEY` が設定されていると常に優先されるので、Pro/Maxを使うときは完全に削除する。

- `CLAUDE_CODE_OAUTH_TOKEN` は有効期限1年、自動更新されない(切れたら `claude setup-token` を再実行)
- 推論専用のトークンで、Remote Control等の機能は使えない

(以前 `Credit balance is too low` エラーが出たのは `ANTHROPIC_API_KEY` 経由の課金クレジットが尽きていたためで、上記の切り替えで解消した。)

## セッション機能(会話の継続)

`agent.py` は実行完了時に `session_id` を `session_id.txt` に保存し、次回実行時にそのIDで会話を再開する。続けたい場合はファイルを残し、新規に始めたい場合は削除してから実行する。

`session_id.txt` は `.gitignore` 済み。再開に失敗した場合(セッションが存在しない/壊れているなど)は自動削除され、次回は新規セッションから始まる。

## ストリーミング出力とツール呼び出しの表示

### メッセージ種別の使い分け

| 種別 | 内容 | 届くタイミング |
|---|---|---|
| `AssistantMessage` | 1ターン分の完成した応答(テキスト・ツール呼び出しを含む) | 常に届く |
| `StreamEvent` | 生成途中の断片(生のClaude APIストリーミングイベントをラップ) | `include_partial_messages=True` の時のみ |

`StreamEvent` は次のような入れ子構造になっている。

```
StreamEvent                     ← 1段目:「これはストリーミングの断片ですよ」という外側の箱
  └ event                       ← 2段目:「どんな種類の出来事か」(6種類)
       ├ message_start          … 1ターンの開始
       ├ content_block_start    … ブロック開始(content_block.type: "text" | "tool_use")
       ├ content_block_delta    … ブロック内の差分
       │    └ delta.type        ← 3段目:「テキストかツール入力か」("text_delta" | "input_json_delta")
       ├ content_block_stop     … ブロック終了
       └ message_delta / message_stop  … ターン終了
```

ブロックごとに `start → delta(複数回) → stop` を繰り返し、1ターン終わると `AssistantMessage` が届く。ツール実行を挟んで次のターンがまた `StreamEvent` から始まり、クエリ全体の終了時には `ResultMessage` が届く。

`message_delta` はターン終了時に1回だけ届き、最終的な `stop_reason`(応答が終わった理由)と累積の `usage`(トークン数)を含む。`message_stop` はストリームの終了を知らせるだけのイベント。

### 実装方針

ツールを呼び出すとき、Claudeはその入力引数(JSON)も `input_json_delta` として断片的に送ってくる。これは人間が読むテキストではないため、そのまま画面に出すと壊れかけのJSON片が表示されてしまう。そこで `agent.py` は `delta.type == "text_delta"` のときだけ画面に出すことで、この事故を防いでいる。

さらに `content_block_start` で `tool_use` を検知した時点から `content_block_stop` までを `in_tool` フラグで区間として扱い、その間は `text_delta` を表示せず `[Using Tool: 名前]... Done` とだけ表示する。これにより会話テキストとツール呼び出しの表示が混ざらない。

`message_delta`/`message_stop` の情報(`stop_reason`・usage)は現状未使用 — `ResultMessage` から取得すれば足りるため。`thinking_delta`(拡張思考)も現状未対応で、表示する要件が出た場合はブロック種別による分岐が必要になる。

## 依存関係の管理(pyproject.toml / uv.lock)

- `pyproject.toml`: 直接使うパッケージを書く人間編集用のファイル。依存を追加・削除・バージョン制約変更するときだけ触る
- `uv.lock`: 間接依存も含めた全パッケージのバージョンを固定する自動生成ファイル。手で編集しない

依存を足す/消すときはコンテナ内で実行し、生成された2ファイルをセットでコミットする:

```bash
docker compose exec agent-app uv add <package>
docker compose exec agent-app uv remove <package>
```

`Dockerfile` は `uv sync --frozen` で `uv.lock` の内容をそのまま入れるので、`pyproject.toml` だけ書き換えて `uv.lock` の更新を忘れるとビルドが失敗する(意図的なガード)。また変更後は `docker compose build` でイメージを作り直さないと反映されない。

## 参考

- Claude Agent SDK (Python) リファレンス: https://code.claude.com/docs/ja/agent-sdk/python#query
- Claude Agent SDK ガイド: https://shiftb.dev/articles/claude-agent-sdk-guide#basic-agent
- Research Skillの実装例: https://zenn.dev/tokium_dev/articles/building-a-research-skill
