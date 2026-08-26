# 2026-08-25 环境搭建与首轮运行排障记录

机器：原评测机（8×RTX PRO 5000 72GB Blackwell）。工作环境是一个共享宿主 docker daemon 的容器,仓库通过 bind mount 同时可见于 `/root/researchclaweval-public` 与 `/data/daweiwang/claude-home/researchclaweval-public`（同一 inode）。

## 1. 容器挂载路径解析（本环境最关键的坑）

- **现象**：fullrun 启动后框架容器秒崩,`cd /workspace/AI-Researcher/research_agent: No such file or directory`。
- **根因**：评测脚本经 `/var/run/docker.sock` 直通宿主 daemon,`docker -v` 的路径按**宿主文件系统**解析。`/root/researchclaweval-public/...` 仅存在于工作容器内,宿主上没有 → 挂载进去是空目录。
- **验证**：同一镜像 A/B 挂载实验——`/root` 形式挂载得到 0 个文件,`/data/daweiwang/...` 形式内容完整。
- **处置**：所有 `REAL_EVAL_RUN_ROOT`、数据集路径、脚本调用一律使用 `/data/daweiwang/claude-home/researchclaweval-public/...` 形式（`.env` 已注明）。**注意**：任何需要挂进容器的临时/沙盒目录同理（如 `/tmp/...` 也挂不进去）。
- **影响面**：所有框架、所有 topic;仅影响"在容器内发起评测"的环境,直接在宿主上跑不受影响。

## 2. 镜像 `ai-researcher:runtime-ready` 缺运行时依赖

原镜像备份 tag：`ai-researcher:runtime-ready-pre-libgl-20260825`。依次补齐并固化：

1. `libGL.so.1` / `libglib2.0`（cv2 导入即崩）；
2. Playwright chromium（browsergym 文献浏览环境需要,`/ms-playwright/chromium-1084`,经 npmmirror 下载）；
3. chromium 系统依赖（libnss3 等一串,实测 `p.chromium.launch()` 通过）；
4. 一次 `docker commit` 失误覆盖了 ENTRYPOINT,已恢复为 `/opt/nvidia/nvidia_entrypoint.sh` + CMD `bash`。

**给协作者**：若你们的 runtime-ready 镜像构建批次较早,可能同样缺 1/2/3,建议用 `python -c "import cv2"` 与 playwright launch 测试。

## 3. 模型名默认值陷阱

- 01 wrapper 默认 `REAL_EVAL_MODEL` 未设时调 **gpt-5.4**;02 默认 **kimi-k2.6**。key 无对应模型权限时表现为 403（"该令牌无权访问模型 gpt-5.4"）无限重试至超时。
- 处置：`.env` 设 `REAL_EVAL_MODEL=gpt-5.6-luna` 全局覆盖。

## 4. ARC 官方打分器（whest starterkit）

- fullrun 硬依赖 `whest`（AIcrowd starterkit）,默认路径 `/tmp/whest-starterkit/.venv`（易失!）。缺失时 run 直接 blocked（exit 25）,打分 fail-closed 无回退。
- 处置：安装于 `/root/whest-starterkit`（whestbench **0.16.0**,commit `35164f3535c2103742772dd11a68ce840464db0b`）,经 `.env` 的 `ARC_WBE_2026_WHEST_PYTHON` 指向。`whest doctor` 6/6 通过。
- **给协作者**：仓库未钉 whest 版本,请对齐上述 commit。

## 5. 网络与下载

- 本机出口代理（127.0.0.1:17897）单连接仅 ~35KB/s;绕开代理直连国内镜像：hf-mirror ~4.5MB/s,gh-proxy.com ~14MB/s（`env -u http_proxy -u https_proxy ...`）。
- ARC 数据集只需 **mini split**（fullrun 的 weights-only 生成器默认 mini）,且 `generate_arc_wbe_2026_weights_only_dataset.py` 要求数据集根下有原始 `data/mini-*.parquet`（三个文件,aria2 多连接从 hf-mirror 拉取）。
- Semantic Scholar 无 key 会被 429（见 02 阻塞记录）。

## 6. 运行方式教训

- 长 run 必须脱离终端会话（tmux 会话 `rceval` 或 `setsid nohup ... </dev/null`）,否则随发起会话终止而被杀——8-25 的首个真实 run 因此丢掉了打分阶段。
- 遗留后台重试循环（clone 失败自动 rm -rf 重试）曾在会话残留期间破坏已就绪的 AI-Researcher checkout;后台循环务必自然终结或显式清理。
- 其他小项：宿主需 `ripgrep`（脚本用 `rg`）;run 目录必须由脚本自建（预创建会被拒）。

## 首轮真实运行结果（run `fullrun_arc_01_20260825_102702`,保留）

环境全通后,gpt-5.6-luna 驱动 01 完成 65 分钟真实研究（idea + E1–E4 + 消融）,产物齐全但不合规（位置/trace 格式/estimator 接口）→ 引出 01×ARC bug 链分析,见 [2026-08-26-01-arc-bug-analysis.md](2026-08-26-01-arc-bug-analysis.md)。
