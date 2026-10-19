# syntax=docker/dockerfile:1
# AI 游戏平台 · agent 镜像（构建上下文：apps/agent）
#
# 由 `cd apps/agent && uv run langgraph dockerfile ../deploy/docker/agent.Dockerfile` 生成后固化，
# 唯一改动是把基础镜像从浮动的 `:3.14` 锚定到 `:0.15.4-py3.14`
# （与本地 `langgraph dev` 实际运行的 langgraph_api 0.15.4 同版，保证开发/生产同构）。
#
# ⚠️ apps/agent/langgraph.json 变更后需要重新生成本文件并对齐版本。
FROM langchain/langgraph-api:0.15.4-py3.14

# -- Adding local package . --
ADD . /deps/agent
# -- End of local package . --

# -- Installing all local dependencies --
# 注意：用基础镜像自带的 /api/constraints.txt 约束安装；若与本工程锁定的依赖冲突，构建会显式失败
RUN for dep in /deps/*; do             echo "Installing $dep";             if [ -d "$dep" ]; then                 echo "Installing $dep";                 (cd "$dep" && PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir -c /api/constraints.txt -e .);             fi;         done

# -- End of local dependencies install --
ENV LANGGRAPH_AUTH='{"path": "/deps/agent/agent/auth.py:auth"}'
ENV LANGSERVE_GRAPHS='{"game": "/deps/agent/agent/agent.py:build_game_agent"}'

# -- Ensure user deps didn't inadvertently overwrite langgraph-api
RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license && touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py
RUN PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir --no-deps -e /api
# -- End of ensuring user deps didn't inadvertently overwrite langgraph-api --
# -- Removing build deps from the final image ~<:===~~~ --
RUN pip uninstall -y pip setuptools wheel
RUN rm -rf /usr/local/lib/python*/site-packages/pip* /usr/local/lib/python*/site-packages/setuptools* /usr/local/lib/python*/site-packages/wheel* && find /usr/local/bin -name "pip*" -delete || true
RUN rm -rf /usr/lib/python*/site-packages/pip* /usr/lib/python*/site-packages/setuptools* /usr/lib/python*/site-packages/wheel* && find /usr/bin -name "pip*" -delete || true
RUN uv pip uninstall --system pip setuptools wheel && rm /usr/bin/uv /usr/bin/uvx

WORKDIR /deps/agent
