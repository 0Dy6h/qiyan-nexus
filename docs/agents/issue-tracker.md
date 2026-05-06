# Issue tracker: 本地 Markdown

问题和 PRD 以 Markdown 文件形式存放在 `.scratch/` 目录下。

## 约定

- 每个功能一个目录：`.scratch/<feature-slug>/`
- PRD 文件：`.scratch/<feature-slug>/PRD.md`
- 实现任务：`.scratch/<feature-slug>/issues/<NN>-<slug>.md`，从 `01` 起编号
- 问题状态记录在文件头部的 `状态:` 行（具体状态值参见 `docs/agents/triage-labels.md`）
- 评论和讨论历史追加到文件底部 `## 评论` 标题下

## 当技能说"发布到问题追踪器"时

在 `.scratch/<feature-slug>/` 下创建新文件（必要时创建目录）。

## 当技能说"获取相关工单"时

读取引用路径下的文件。用户通常会直接提供路径或问题编号。
