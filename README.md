# ai-agent
Custom AI Agent

Claude Agent SDK (Python) を使って、コンテナ内で `agent.py` を動かすプロジェクト。

## セットアップ

依存関係は `pip` ではなく `uv` (`pyproject.toml` + `uv.lock`) で管理している。

```bash
docker compose build
docker compose up -d
```

コンテナは `sleep infinity` で起動したままになるので、中に入って好きなタイミングで実行する。

まずコンテナに入る:

```bash
docker compose exec agent-app bash
```

コンテナ内で実行:

```bash
uv run python agent.py
```

## 認証(API課金ではなくPro/Maxプランを使う)

`ANTHROPIC_API_KEY` はAnthropic ConsoleのAPI従量課金、Pro/Maxプランの利用枠とは別会計。Pro/Max分を使いたい場合は設定しない。

1. ホスト側で1度だけ実行してOAuthトークンを発行
   ```bash
   claude setup-token
   ```
2. `.env` に `ANTHROPIC_API_KEY` は書かず、発行されたトークンを設定
   ```
   CLAUDE_CODE_OAUTH_TOKEN=<setup-tokenで発行された値>
   ```

`ANTHROPIC_API_KEY` が設定されていると常に優先されるので、Pro/Maxを使うときは完全に削除する。

**注意点:**
- `CLAUDE_CODE_OAUTH_TOKEN` は**有効期限1年、自動更新されない**(切れたら `claude setup-token` を再実行)
- 推論専用のトークンで、Remote Control等の機能は使えない

以前 `Credit balance is too low` エラーが出たのは `ANTHROPIC_API_KEY` 経由の課金クレジットが尽きていたためで、上記の切り替えで解消した。

## セッション機能(会話の継続)

`agent.py`は実行完了時に`session_id`を`session_id.txt`に保存し、次回実行時にそのIDで会話を再開(`resume`)する。会話を続けたいときは`session_id.txt`を残したまま、新しく会話を始めたいときは`session_id.txt`を削除してから実行する。

`session_id.txt`は実行のたびに変わる一時状態のため`.gitignore`済み。セッションの再開に失敗した場合(セッションが存在しない/壊れているなど)は`session_id.txt`を自動で削除し、次回実行時に新規セッションから始まるようにしている。

## ストリーミング出力とツール呼び出しの表示

`ClaudeAgentOptions(include_partial_messages=True)`を指定すると、最終的な`AssistantMessage`/`ResultMessage`より前に`StreamEvent`が逐次流れてくる。`StreamEvent`はAnthropic APIの生のストリームイベントをラップしたもので、以下のように入れ子構造になっている。

```
StreamEvent                     ← 1段目:「これはストリーミングの断片ですよ」という外側の箱
  └ event                       ← 2段目:「どんな種類の出来事か」(6種類ある)
       ├ message_start          … 1ターンの開始
       ├ content_block_start    … コンテンツブロック開始(content_block.type: "text" | "tool_use")
       ├ content_block_delta    … ブロック内の差分
       │    └ delta.type        ← 3段目:「テキストの断片なのか、ツール入力の断片なのか」
       │         ├ "text_delta"        … テキストの断片
       │         └ "input_json_delta"  … ツール入力(JSON)の断片
       ├ content_block_stop     … コンテンツブロック終了
       ├ message_delta          … ターン全体の差分(stop_reasonなど)
       └ message_stop           … 1ターンの終了
```

text/tool_useのブロックごとに`content_block_start → content_block_delta(複数回) → content_block_stop`を繰り返し、1ターン分の`StreamEvent`が終わると`AssistantMessage`(そのターンの完全なメッセージ)が流れてくる。ツール実行を挟んで次のターンが始まる場合はまた`StreamEvent`から繰り返し、クエリ全体が終わると最後に`ResultMessage`が流れてくる。

`agent.py`では`content_block_start`の`content_block.type`が`"tool_use"`かどうかで`in_tool`フラグを立て、

- `in_tool`中は`content_block_delta`の`text_delta`を表示せず、代わりに`[Using Tool: 名前]... Done`とだけ表示する
- `in_tool`でない`text_delta`はそのまま逐次表示する(`AssistantMessage`側での再表示はしていないので二重出力にならない)

ことで、会話テキストとツール呼び出しの表示が混ざらないようにしている。新しいターンは直前のターンで`tool_use`が使われた場合にのみ発生するため、テキストのみのターンが連続することはない。

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
