# RAGSieve

Detecting knowledge-poisoned documents in Retrieval-Augmented Generation (RAG) without a trusted reference corpus.

- **RSQ** — online filter: scores the Top-5 retrieved documents against ranks 6–20 for the current query.
- **RSG** — offline scanner: scores every corpus document against its own semantic–lexical neighborhood.

## Web 演示界面

一个零依赖的单页前端，展示 RSQ 与 RSG 在演示数据上的检测结果（红 = 投毒，绿 = 干净）。

### 一键部署并启动

```bash
bash web/start.sh
```

然后浏览器打开 <http://127.0.0.1:8000>。

- 改端口：`PORT=9000 bash web/start.sh`
- GPU 机器：`DEVICE=cuda:0 bash web/start.sh`（默认 CPU）

首次运行会自动 `uv sync` 安装依赖；若 `outputs/demo` 缺失，会先执行 `bash run_demo.sh`
生成演示数据（首次需下载模型，约几分钟）。

### 手动分步

```bash
uv sync --all-extras          # 1. 安装依赖
bash run_demo.sh              # 2. 生成演示数据到 outputs/demo
uv run python web/server.py   # 3. 启动 Web 界面
```

界面包含两个标签页：**RSQ · 在线检测**（点选 4 个示例查询，查看 Top-5 打分/标记、
过滤前后对比、四项证据）与 **RSG · 离线扫描**（520 篇文档得分分布与标记清单）。
数据全部来自预先计算的 `outputs/demo`，前端不加载模型、秒开。
