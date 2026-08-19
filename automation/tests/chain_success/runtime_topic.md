# Runtime Topic Contract

## Topic

- Topic label: `BabyLM`
- Dataset root: `/home/guanghao/researchclaweval/BabyLM-2026-Strict-Small`

## Goal

当前自动化运行的真实 e2e 任务必须围绕这个 topic 展开。

## Smoke Gate

在提交 `systemd --user` 级别 e2e 之前，smoke 阶段必须先确认：

1. 当前项目真正消费的任务输入位置已经找对
2. 该输入不再指向旧 topic
3. 当前项目已经知道数据集路径或本 contract 文件路径
4. 如需改动，只做最小必要改动
5. 提交出去的 e2e 将实际跑这个 topic

## Acceptance

只有当以上条件满足时，才允许从 smoke 进入 e2e dispatch。
