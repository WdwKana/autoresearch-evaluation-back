# 2026-08-27 框架 01 × tdc_admet_tox 进展与阻塞（工作暂停时的状态快照）

本轮按"先把 01 推广到其他 topic"的计划启动 TDC,进展到 smoke 的最后一项检查时暂停（团队决定改走"重拉最新仓库 + 复现"的规范路径）。此处记录已完成资产与未决阻塞,供恢复工作时接续。

## 已完成（可直接复用）

1. **数据集完整物化,校验全绿**
   - 官方档案 `admet_group.zip` 取自 Harvard Dataverse（datafile/4426004）,MD5/SHA256/大小与 `export_tdc_admet_tox_official_splits.py` 内钉的哈希**精确匹配**。
   - 切分导出需 **RDKit 恰好 2023.09.5**（脚本硬校验版本;`uv sync --extra tdc` 装到的是 2026.03.5 会被拒）。可用 `uv run --extra tdc --with "rdkit==2023.9.5" python ...` 满足。
   - 物化产出:公开集 `data/tdc_admet_tox/{train,validation,test}.csv + dataset_manifest.json`,隐藏标签分离至 `data/.hidden/tdc_admet_tox_labels/`。
   - smoke 的数据侧检查**全部通过**:public_file_set_exact / labeled_schema / test_schema_unlabeled / endpoint_sets_exact（AMES、hERG、DILI）/ cross_topic_paths_absent / credentials_absent_from_log。

2. **provider relay 链路打通**:relay 容器启动成功,`provider_relay_evidence.json` 显示 upstream 正确指向 bianxie,框架侧不可见公网。

3. **回收发布遗漏文件** `real_eval/codex_relay/relay.py`(1046 行,从常驻容器 `researchclaweval-codex-kimi-relay` docker cp 取得,已加 provenance 头)。**待向维护者索取正本 diff。**

## 未决阻塞：smoke 的 `agent_evidence` 检查

现象:容器内 `codex exec` 探针能连通 relay 并开始作答,但在第一次工具调用处静默中止,不产出 `tdc_admet_tox_smoke_evidence.json`,故该项为 false（其余九项皆 true）。

已排除的原因:
- 模型不支持函数调用 → 否。直连 bianxie 用 `gpt-5.6-luna` 测 chat + tools,正常返回 `tool_calls`。
- relay 不转发 tools → 否。`_translate_responses_tools` 覆盖 function/custom/namespace 三类。
- provider 配置无效 → 已修正为双格式 `my_provider.toml`（顶层字段供 wrapper sed 提取 + `[model_providers.*]` 供 Codex CLI）。

高置信度的真实原因（**版本错配**）:
- 本机装的是 **codex-cli 0.150.1**,它**已移除 `wire_api = "chat"` 支持**（启动即报 "no longer supported... set wire_api = responses"）。
- 而 relay 的设计前提正是"Codex 说 responses、上游说 chat"的翻译层（`relay_request path=/v1/responses upstream_wire_api=chat`）。
- 原作者当时用的 Codex 版本**仓库未钉**（`api/` 私有目录连同版本约定一起未发布）。新版 Codex 的 responses 协议与 relay 的翻译实现之间存在未知偏差,导致工具回合失败。

## 恢复工作时的建议顺序

1. **先问合作者**:你们跑 TDC/PsyDef 时用的 Codex CLI 版本号?（这是唯一能一步解决的信息）拿到后钉版本安装即可。
2. 若无法获知,再考虑抓包对比 codex 0.150 的 responses 载荷与 relay 期望格式——但这属于"没有规范的深挖",应先取得团队共识。

## 环境侧记录（本机特有）

- 宿主原本没有 node/npm;smoke 需要 `HOST_NODE_ROOT` 下的 codex 二进制,且该路径会被 bind-mount 进容器 → **必须装在宿主可见路径**（本机装于 `/data/daweiwang/claude-home/tools/node-root`,通过 `REAL_EVAL_HOST_NODE_ROOT` 指定;装在 `/usr/local` 会因挂载解析失败）。
- 通用 wrapper 需显式 `REAL_EVAL_RUN_ID`（同 02）。
