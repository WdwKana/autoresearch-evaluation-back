# ResearchClawEval Collaboration Guide / 协作指南

> **English** | [中文](#researchclaweval-协作指南)

---

## English

### Overview

ResearchClawEval is an evaluation control plane for research-agent frameworks. This repository contains the evaluation infrastructure (contracts, validators, scripts, registry, and adapter patches). The actual framework source code is **not included** in this repository — it is cloned from upstream public repositories during setup.

### Prerequisites

- **Linux** (evaluation runs require Linux)
- **Python 3.10 – 3.12**
- **[uv](https://docs.astral.sh/uv/)** (recommended package manager)
- **Git**
- **Docker** (required for actual framework runs, not needed for dry-run/validation)
- **~4 GB free disk space** (for cloning the three frameworks)

### Quick Start

#### 1. Clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/researchclaweval-public.git
cd researchclaweval-public
```

#### 2. Run the setup script

The setup script will clone the three frameworks (AI-Researcher, AI-Scientist-v2, AutoResearchClaw), checkout the pinned commits, apply patches, and install dependencies:

```bash
bash setup.sh
```

To set up only specific frameworks:

```bash
bash setup.sh --frameworks 01,04    # Only AI-Researcher and AutoResearchClaw
```

To clone frameworks to a different directory:

```bash
bash setup.sh --dir /path/to/frameworks
```

#### 3. Configure API keys

You need an LLM provider that supports OpenAI-compatible API. Set these environment variables:

```bash
export OPENAI_API_KEY=your_api_key_here
export OPENAI_BASE_URL=https://api.your-provider.com/v1
export OPENAI_MODEL=your-model-name
```

Optionally, set framework source paths explicitly (otherwise the setup script's clone locations are used):

```bash
export RESEARCHCLAWEVAL_AI_RESEARCHER_ROOT=/path/to/AI-Researcher
export RESEARCHCLAWEVAL_AI_SCIENTIST_V2_ROOT=/path/to/AI-Scientist-v2
export RESEARCHCLAWEVAL_AUTORESEARCHCLAW_ROOT=/path/to/AutoResearchClaw
```

#### 4. Verify the setup

```bash
# Validate the registry
uv run rceval validate registry

# List all registered frameworks and topics
uv run rceval registry list

# Show the evaluation matrix for a topic
uv run rceval registry matrix --topic arc_wbe_2026 --mode smoke

# Run a dry-run smoke test (no Docker, no framework launch needed)
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-test
```

### Running an Evaluation

#### Smoke test

A smoke test generates native inputs and validates the data pipeline without launching the actual framework:

```bash
# Set output directory
export REAL_EVAL_RUN_ROOT=/tmp/rceval-smoke

# Run AI-Researcher ARC-WBE-2026 smoke test
bash real_eval/scripts/01_ai_researcher_arc_wbe_2026_smoke.sh
```

#### Full run (requires Docker)

Full runs execute the framework inside a Docker container. You need to build the required Docker images first:

```bash
# For AI-Researcher: build the outer container
docker build -t ai-researcher:runtime-ready -f /path/to/AI-Researcher/docker/Dockerfile /path/to/AI-Researcher
```

Then run:

```bash
export REAL_EVAL_RUN_ROOT=/tmp/rceval-fullrun
bash real_eval/scripts/01_ai_researcher_arc_wbe_2026_fullrun.sh
```

> **Note**: Full runs require datasets, which are not distributed through this repository. See the [Datasets](#datasets) section below.

### Framework Details

| ID | Framework | Upstream | Size | Patches |
|---|---|---|---|---|
| 01 | AI-Researcher | [HKUDS/AI-Researcher](https://github.com/HKUDS/AI-Researcher.git) | ~1.7 GB | 1 patch (evaluation adapter) |
| 02 | AI-Scientist-v2 | [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2.git) | ~12 MB | None |
| 04 | AutoResearchClaw | [aiming-lab/AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw.git) | ~256 MB | 1 patch (HTTP error logging) |

### Directory Structure

```
researchclaweval-public/
├── researchclaweval/          # Python package (CLI, registry, leaderboard)
├── framework_evaluator/       # Evaluation orchestrator and state machine
├── real_eval/                 # Real evaluation scripts and registry
│   ├── registry/              # Framework, topic, and run registries
│   └── scripts/               # Run scripts for each framework × topic
├── adapters/                  # Framework adapter manifests and patches
│   ├── 01-ai-researcher/
│   ├── 02-ai-scientist-v2/
│   └── 04-autoresearchclaw/
├── automation/                # Shared automation scripts and contracts
├── schemas/                   # JSON Schema definitions
├── docs/                      # Documentation
├── tasks/                     # Framework task descriptions
├── tests/                     # Test suite
├── setup.sh                   # One-click setup script
├── SETUP.md                   # This file
└── pyproject.toml             # Project configuration
```

### Datasets

Datasets are **not** included in this repository. They must be obtained separately:

| Topic | Dataset | Status | How to Obtain |
|---|---|---|---|
| GAVE2-Task2 | GAVE2 preliminary | Public | See [GAVE2 official site](https://gave2.webis.de/) |
| ARC-WBE-2026 | ARC White-Box Estimation | Public | See [ARC official site](https://arc.net/) |
| PsyDefDetect | PsyDefDetect | Beta | Contact maintainers |
| BabyLM-10M | BabyLM-2026-Strict-Small | Public | See [BabyLM site](https://babylm.github.io/) |
| TDC-ADMET-Tox | TDC ADMET | Public | See [TDC website](https://tdcommons.ai/) |

Set dataset paths via environment variables:

```bash
export ARC_WBE_2026_DATASET_ROOT=/path/to/ARC_WBE_2026
export GAVE2_DATASET_ROOT=/path/to/GAVE2_preliminary
```

### API Configuration

For full runs, you can provide a TOML config file for the LLM provider:

```toml
# Example: provider.toml
experimental_bearer_token = "your-api-key"
base_url = "https://api.your-provider.com"
model = "gpt-5.4"
```

Then reference it in the run script:

```bash
export PROVIDER_CONFIG=/path/to/provider.toml
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding a new framework adapter
- Adding a new evaluation topic
- Submitting evaluation results

### Getting Help

- Open an issue on GitHub
- See [SECURITY.md](SECURITY.md) for reporting security issues

---

## ResearchClawEval 协作指南

### 概述

ResearchClawEval 是一个科研 Agent 框架的评测控制层。本仓库包含评测基础设施（合约、验证器、脚本、注册表和适配器补丁）。框架的**实际源代码不包含在此仓库中**，需要在设置时从上游公共仓库克隆。

### 前置要求

- **Linux** 系统（评测运行需要 Linux）
- **Python 3.10 – 3.12**
- **[uv](https://docs.astral.sh/uv/)**（推荐包管理器）
- **Git**
- **Docker**（运行实际框架时需要，dry-run 验证不需要）
- **约 4 GB 可用磁盘空间**（用于克隆三个框架）

### 快速开始

#### 1. 克隆本仓库

```bash
git clone https://github.com/你的用户名/researchclaweval-public.git
cd researchclaweval-public
```

#### 2. 运行设置脚本

设置脚本会自动克隆三个框架（AI-Researcher、AI-Scientist-v2、AutoResearchClaw），切换到固定 commit，应用补丁，并安装依赖：

```bash
bash setup.sh
```

只设置特定框架：

```bash
bash setup.sh --frameworks 01,04    # 只设置 AI-Researcher 和 AutoResearchClaw
```

克隆到自定义目录：

```bash
bash setup.sh --dir /path/to/frameworks
```

#### 3. 配置 API Key

你需要一个支持 OpenAI 兼容接口的 LLM 提供商。设置以下环境变量：

```bash
export OPENAI_API_KEY=你的API密钥
export OPENAI_BASE_URL=https://你的提供商地址/v1
export OPENAI_MODEL=模型名称
```

可选：显式指定框架源码路径（否则使用设置脚本的克隆位置）：

```bash
export RESEARCHCLAWEVAL_AI_RESEARCHER_ROOT=/path/to/AI-Researcher
export RESEARCHCLAWEVAL_AI_SCIENTIST_V2_ROOT=/path/to/AI-Scientist-v2
export RESEARCHCLAWEVAL_AUTORESEARCHCLAW_ROOT=/path/to/AutoResearchClaw
```

#### 4. 验证设置

```bash
# 验证注册表
uv run rceval validate registry

# 列出所有注册的框架和主题
uv run rceval registry list

# 查看某个主题的评估矩阵
uv run rceval registry matrix --topic arc_wbe_2026 --mode smoke

# 运行 dry-run 冒烟测试（不需要 Docker，不需要启动框架）
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-test
```

### 运行评测

#### 冒烟测试

冒烟测试会生成原生输入并验证数据管道，不启动实际框架：

```bash
# 设置输出目录
export REAL_EVAL_RUN_ROOT=/tmp/rceval-smoke

# 运行 AI-Researcher ARC-WBE-2026 冒烟测试
bash real_eval/scripts/01_ai_researcher_arc_wbe_2026_smoke.sh
```

#### 完整运行（需要 Docker）

完整运行会在 Docker 容器内执行框架。需要先构建所需的 Docker 镜像：

```bash
# AI-Researcher：构建外部容器
docker build -t ai-researcher:runtime-ready -f /path/to/AI-Researcher/docker/Dockerfile /path/to/AI-Researcher
```

然后运行：

```bash
export REAL_EVAL_RUN_ROOT=/tmp/rceval-fullrun
bash real_eval/scripts/01_ai_researcher_arc_wbe_2026_fullrun.sh
```

> **注意**：完整运行需要数据集，这些数据集不通过本仓库分发。请参见下方的[数据集](#数据集)部分。

### 框架详情

| ID | 框架 | 上游仓库 | 大小 | 补丁 |
|---|---|---|---|---|
| 01 | AI-Researcher | [HKUDS/AI-Researcher](https://github.com/HKUDS/AI-Researcher.git) | ~1.7 GB | 1 个（评估适配器） |
| 02 | AI-Scientist-v2 | [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2.git) | ~12 MB | 无 |
| 04 | AutoResearchClaw | [aiming-lab/AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw.git) | ~256 MB | 1 个（HTTP 错误日志） |

### 目录结构

```
researchclaweval-public/
├── researchclaweval/          # Python 包（CLI、注册表、排行榜）
├── framework_evaluator/       # 评估编排器和状态机
├── real_eval/                 # 实际评估脚本和注册表
│   ├── registry/              # 框架、主题和运行注册表
│   └── scripts/               # 每个框架×主题的运行脚本
├── adapters/                  # 框架适配器清单和补丁
│   ├── 01-ai-researcher/
│   ├── 02-ai-scientist-v2/
│   └── 04-autoresearchclaw/
├── automation/                # 共享自动化脚本和合约
├── schemas/                   # JSON Schema 定义
├── docs/                      # 文档
├── tasks/                     # 框架任务描述
├── tests/                     # 测试套件
├── setup.sh                   # 一键设置脚本
├── SETUP.md                   # 本文件
└── pyproject.toml             # 项目配置
```

### 数据集

数据集**不包含在本仓库中**，需要单独获取：

| 主题 | 数据集 | 状态 | 获取方式 |
|---|---|---|---|
| GAVE2-Task2 | GAVE2 preliminary | 公开 | 参见 [GAVE2 官网](https://gave2.webis.de/) |
| ARC-WBE-2026 | ARC White-Box Estimation | 公开 | 参见 [ARC 官网](https://arc.net/) |
| PsyDefDetect | PsyDefDetect | Beta | 联系维护者 |
| BabyLM-10M | BabyLM-2026-Strict-Small | 公开 | 参见 [BabyLM 官网](https://babylm.github.io/) |
| TDC-ADMET-Tox | TDC ADMET | 公开 | 参见 [TDC 网站](https://tdcommons.ai/) |

通过环境变量设置数据集路径：

```bash
export ARC_WBE_2026_DATASET_ROOT=/path/to/ARC_WBE_2026
export GAVE2_DATASET_ROOT=/path/to/GAVE2_preliminary
```

### API 配置

完整运行时，可以通过 TOML 配置文件提供 LLM 提供商信息：

```toml
# 示例：provider.toml
experimental_bearer_token = "你的API密钥"
base_url = "https://api.your-provider.com"
model = "gpt-5.4"
```

然后在运行脚本中引用：

```bash
export PROVIDER_CONFIG=/path/to/provider.toml
```

### 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何：
- 添加新的框架适配器
- 添加新的评测主题
- 提交评测结果

### 获取帮助

- 在 GitHub 上提交 Issue
- 安全问题请参见 [SECURITY.md](SECURITY.md)