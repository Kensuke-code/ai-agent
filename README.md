# ai-agent
Custom AI Agent

Claude Agent SDK (Python) を使って、コンテナ内で `main.py` を動かすプロジェクト。

## セットアップ

依存関係は `uv` (`pyproject.toml` + `uv.lock`) で管理している。

```bash
docker compose build
docker compose up -d
docker compose exec agent-app bash
```

コンテナは `sleep infinity` で起動したままになるので、入った後に好きなタイミングで実行する。

```bash
uv run python src/main.py
```

## 認証(API課金ではなくPro/Maxプランを使う)

`ANTHROPIC_API_KEY` はAnthropic ConsoleのAPI従量課金で、Pro/Maxプランの利用枠とは別会計。Pro/Max分を使いたい場合は設定しない。

1. ホスト側で1度だけOAuthトークンを発行: `claude setup-token`
2. `.env` に `ANTHROPIC_API_KEY` は書かず、発行されたトークンを設定: `CLAUDE_CODE_OAUTH_TOKEN=<setup-tokenで発行された値>`

`ANTHROPIC_API_KEY` が設定されていると常に優先されるので、Pro/Maxを使うときは完全に削除する。

- `CLAUDE_CODE_OAUTH_TOKEN` は有効期限1年、自動更新されない(切れたら `claude setup-token` を再実行)
- 推論専用のトークンで、Remote Control等の機能は使えない

(以前 `Credit balance is too low` エラーが出たのは `ANTHROPIC_API_KEY` 経由の課金クレジットが尽きていたためで、上記の切り替えで解消した。)

## 会話の継続(ClaudeSDKClient)

`main.py` は `ClaudeSDKClient` で接続を張ったまま、以下の2段階で会話を継続する。

- **プロセス内(同一実行内)**: 1ターンの応答が終わるとターミナルで `You: ` の入力を待ち、入力した内容を同じ接続のまま次のターンとして送る。Claudeがテキストで質問を返してきた場合もここで回答すれば会話が続く。空入力または `exit` / `quit` / `終了` を入力すると終了する。
- **プロセスを跨いだ再開**: 実行終了時に `session_id` を `session_id.txt` に保存し、次回起動時にそのIDで会話を再開する。続けたい場合はファイルを残し、新規に始めたい場合は削除してから実行する。

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

`message_delta` はターン終了が近づくと1回以上届き、最終的な `stop_reason`(応答が終わった理由)と累積の `usage`(トークン数)を含む。`message_stop` はストリームの終了を知らせるだけのイベント。

### 実装方針

ツールを呼び出すとき、Claudeはその入力引数(JSON)も `input_json_delta` として断片的に送ってくる。これは人間が読むテキストではないため、そのまま画面に出すと壊れかけのJSON片が表示されてしまう。そこで `main.py` は `delta.type == "text_delta"` のときだけ画面に出すことで、この事故を防いでいる(そもそも`tool_use`ブロック中に`text_delta`が来ることはないため、実質的にはこの型チェックだけで十分)。

ただしこのままだとツール呼び出し中は何も表示されず無言になってしまう。そこで `content_block_start` で `tool_use` を検知した時点から `content_block_stop` までを `in_tool` フラグで区間として扱い、その間だけ `[Using Tool: 名前]... Done` というステータス表示に切り替えている。これにより会話テキストとツール呼び出しの表示が混ざらない。

`message_delta`/`message_stop` の情報(`stop_reason`・usage)は現状未使用 — `ResultMessage` から取得すれば足りるため。`thinking_delta`(拡張思考)も現状未対応で、表示する要件が出た場合はブロック種別による分岐が必要になる。

## パーミッション制御(can_use_tool)

`ClaudeAgentOptions(can_use_tool=handle_tool_request)` で、ツール呼び出しごとに許可/拒否を判定している。

### Write / Edit — 書き込み先を `/app/` 配下に限定

- `file_path` を `os.path.realpath` で解決し、シンボリックリンクや `..` を実体パスに正規化してから判定する
- `/etc/`, `/root/`, `.ssh/` を含むパスへの書き込みは**タスク/セッションごと中断**する(`interrupt=True`)。狙って機密領域に書き込もうとする明らかに異常な挙動とみなすため
- それ以外で `/app/` 配下でないパスは、その書き込みだけを拒否して継続する(`interrupt=False`)

### Bash — `rm` / `sudo` を拒否

`disallowed_tools=["Bash(rm *)", "Bash(sudo *)"]` でCLIレベルのパターンマッチにより拒否する。コンテナに `git` 自体が入っていない(`Dockerfile` 参照)ため、`git push` 等の追加制限は行っていない。

### AskUserQuestion — ターミナルで直接質問に答える

Claudeが `AskUserQuestion` ツールを呼ぶと、`handle_ask_user_question` が質問と選択肢をターミナルに表示し、`input()` で人間の回答を待つ。回答は `question["question"]` をキーとした `answers` 辞書にまとめ、`PermissionResultAllow(updated_input={**input_data, "answers": answers})` として返すことで、同じターン内でClaudeに回答が渡る(新しいプロンプトを送り直す必要はない)。

### 注意: `allowed_tools` は `can_use_tool` をシャドーイングする

`allowed_tools` にツール名をそのまま(括弧なしで)書くと、そのツールは `can_use_tool` を経由せず自動承認される。`handle_tool_request` 側で個別に判定したいツール(`Write`, `Edit`, `AskUserQuestion`)は `allowed_tools` に入れず、`can_use_tool` 側の分岐だけで許可/拒否を決める。`Read` / `Grep` / `Glob` / `WebSearch` のように無条件で許可してよいツールだけを `allowed_tools` に入れている。

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
- Claude Agent SDK でつくる！対話型AIエージェント開発 https://zenn.dev/ml_bear/books/f2d52a3bc0b33c/viewer/1b209e
