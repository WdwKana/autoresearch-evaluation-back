# 补丁统一化重构蓝图

状态: 设计已定,待当前五线测试收尾后施工。触发条件: 本轮 kimi/DS/mcar8/tdc13/babylm17 无新增回归。

## 目标

框架级补丁"一框架一份",wrapper 只调用不复制。消除三次实证过的复制税:
BabyLM 重踩 ARC 已修的 PLATFORM 族坑、psydef wrapper 至今缺 GPTClient 模型修复、
同一补丁三处漂移无人察觉。

## 目标结构

```
real_eval/adapters/
  ai_researcher/
    patch_common.py          # 新建:全部 01 框架级补丁的唯一权威
  ai_scientist_v2/
    patch_ai_scientist_v2_common.py   # 已存在,并入同一规范
  <topic>/patch_*.py         # topic 专属(数据投影等)保留,先调 common 再做本topic部分
```

## patch_common.py 收编清单(01)

| 补丁 | 现居地 | 范围参数 |
|---|---|---|
| constant.py PLATFORM | ARC/BabyLM wrapper + TDC/mcar adapter ×4 份 | 无条件 |
| tools/__init__ 显式注册 | 同上 ×4 | 无条件 |
| main(args, references="") | ×4 | 无条件 |
| GitHub search 绕过 | ×4(各自硬编码 category) | --category |
| GPTClient 读 OPENAI_MODEL + chat() 去 None | 仅 BabyLM | 无条件(psydef 缺此修复=已知隐患) |
| tiktoken disallowed_special | 仅 BabyLM | 无条件 |
| agent 缓存别名解析 | 仅 BabyLM | 无条件 |
| docker_env 宿主路径重映射+hostname env+端口断言放宽 | 仅 ARC | 需 socket 直通的 topic |
| 内层通道 keepalive 重连 | 仅 ARC(2026-09-01 新增) | 同上 |
| docling 导入护栏 / tree→find | 仅 ARC | 无条件 |
| PaperMemory no-op / 其他能力削减 | 仅 ARC | **--enable-capability-cuts 显式开关**,默认保留原生能力,削减必须显式声明(公平性问题单独暴露) |

## 质量标准(施工验收线)

1. **金样等价测试**: 对同一份源码副本,分别用旧 wrapper 内嵌块与新 patch_common.py 打补丁,
   `diff -r` 两棵产物树必须为空。逐 wrapper 验证后才允许删除旧内嵌块。零 API 成本。
2. **幂等**: 连续应用两次,第二次为显式 no-op(现有 in-guard 风格保持)。
3. **锚点响亮失败**: 上游变更导致锚点消失时 raise SystemExit 指明补丁名,禁止静默 SKIP
   (除标注为可选的项)。
4. 每个补丁单元携带: 名称、目标文件、依据(run 证据引用)、范围条件。单文件、零第三方依赖。
5. wrapper 侧改动 = 删内嵌块 + 一行调用;git diff 只允许出现 01/02 作用域文件。

## 顺带清理项

- AI-Researcher 检出内我早期手工放置的 benchmark/final/mountaincar_continuous/ 与
  dataset_candidate/mountaincar_continuous/(生成器已能产出,冗余 fallback,删除并复跑金样)。
- 核对 AI-Researcher/docker/requirements.txt 的 M(非我们所改,疑似作者构建镜像时期遗留)。

## 明确不做

- 不动 03-07 任何文件;不动共享 validator;不新增补丁语义——纯搬家,行为逐字节等价。
