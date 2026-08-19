# ResearchClawEval

ResearchClawEval 是面向科研 Agent 框架的公开评测控制层。它维护任务契约、
固定上游框架版本、记录最小适配补丁、验证运行证据，并生成脱敏排行榜；数据集、
密钥、隐藏标签、完整上游源码和原始运行目录不进入本仓库。

## 成熟度

| Topic | 成熟度 | 公开模式 |
|---|---|---|
| GAVE2-Task2 | stable | input pack、smoke、full run |
| ARC-WBE-2026 | stable | input pack、smoke、full run |
| PsyDefDetect | beta | smoke、full run |
| BabyLM-10M | legacy | full run |
| TDC-ADMET-Tox | experimental | smoke pilot |

注册表包含 7 个框架和 64 条映射。映射存在并不代表结果已通过原生执行准入；
使用通用宿主 `codex exec` 的 fullrun 会明确标记为 `unsupported_non_native`。

## 本地使用

### 一键设置（协作模式）

```bash
# 克隆本仓库
git clone https://github.com/你的用户名/researchclaweval-public.git
cd researchclaweval-public

# 运行设置脚本——自动克隆 3 个框架、应用补丁、安装依赖
bash setup.sh

# 配置 LLM API Key
export OPENAI_API_KEY=你的API密钥
export OPENAI_BASE_URL=https://你的提供商地址/v1
export OPENAI_MODEL=模型名称

# 验证设置
uv run rceval validate registry
uv run rceval registry list
uv run rceval registry matrix --topic gave2_task2 --mode fullrun
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-plan
uv run rceval leaderboard render
```

详细协作指南请参见 [SETUP.md](SETUP.md)。

### 基础验证（无需框架）

```bash
uv sync --extra dev
uv run rceval validate registry
uv run rceval registry list
uv run rceval registry matrix --topic gave2_task2 --mode fullrun
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-plan
```

以上命令不会启动真实框架，也不需要数据集。真实评测需要 Linux、Docker、外部
框架 checkout、数据集路径以及用户自行提供的 provider 环境变量。

贡献 Topic、框架适配器或评测结果前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

