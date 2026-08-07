FROM python:3.12-slim

# uvをインストール(pipより高速なインストーラ)
RUN pip install --no-cache-dir uv

WORKDIR /app

# 依存関係の定義ファイルだけ先にコピーしてsync
# (コードだけ変更した場合にこのレイヤーのキャッシュを効かせるため)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# コードはcompose.ymlのバインドマウント頼みにしていて、イメージには焼き込まない

# コンテナを起動したままにしておき、docker compose exec で
# agent.pyを何度も実行するための待機コマンド。
CMD ["sleep", "infinity"]
