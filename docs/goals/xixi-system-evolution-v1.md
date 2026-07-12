# Xixi Personal Dev System Evidence Evolution Goal

> **定位**：本文是本 Goal 的唯一权威入口。扫描范围、经验晋升规则、阶段门禁、证据、提交边界和完成状态均以本文为准。

## 1. 目标

以本机 Git `origin` 归属 GitHub 用户 `xixinikl` 的项目为范围，不读取远端仓库正文，扫描本地项目中已经发生并有证据的工程经验；以 `gongtu-project` 和 `canvas-storm` 为经验来源，升级 `xixi-dev-system` 的学习、自动化和 Goal 能力，并升级 `xixi-agent-profile` 的长期规则、模板与索引，最后分别验证、提交并推送两个系统仓库。

本 Goal 还必须吸收 Profile owner 多次强调的 CDS 式 Goal 写法：唯一权威入口、当前事实、范围与非范围、阶段依赖、小节点验收、证据栏、风险停止条件、PR 边界和 completion audit。

## 2. 当前事实

本机按 `origin` 过滤后共有5个归属工作副本，对应4个唯一GitHub仓库；`gongtu-project` 有两个并行本地工作副本，二者都属于证据范围：

| 仓库 | 本机路径 | 本 Goal 角色 |
|---|---|---|
| `gongtu-project` | `/Users/miduoduo/Documents/xixi_gongtu` | 经验来源 |
| `gongtu-project` | `/Users/miduoduo/Documents/xixi_gongtu-main-app` | 经验来源（同远端的并行工作副本） |
| `canvas-storm` | `/Users/miduoduo/Documents/思维风暴` | 经验来源 |
| `xixi-dev-system` | `/Users/miduoduo/Documents/xixi-dev-system` | 自动化与执行系统目标 |
| `xixi-agent-profile` | `/Users/miduoduo/Documents/xixi-agent-profile` | 长期规则与模板目标 |

- GitHub账号只用于本机范围过滤，不授权读取或复制远端仓库正文。
- 两个目标仓库均有现存未提交改动；这些改动视为 Profile owner 或前序 Agent 成果，必须在其基础上工作，不得覆盖。
- `xixi-dev-system` 已有 `learning`、`weekly-review`、`automation`、`goal`、`acceptance` 能力和正在开发的 Goal 状态内核。
- `xixi-agent-profile` 已有记忆更新协议、工作流索引、项目发现脚本和工业化工作流草案。

## 3. 范围

### 包含

- 只读扫描两个经验来源仓库的治理、复盘、交接、Goal、验收和自动化证据。
- 建立可审计的经验候选清单，记录来源、重复次数、影响、适用范围和反例。
- 把跨项目经验转成系统规则、模板、机器门禁或自动化，而不是只写叙述性总结。
- 把 CDS 式 Goal 变成可复用模板和系统检查项。
- 验证两个目标仓库现有改动与新增能力协同工作。
- 对两个目标仓库分别形成有意图的提交并推送 GitHub。

### 不包含

- 不扫描其他GitHub用户、组织仓库或无匹配 `origin` 的本机目录。
- 不把业务题目内容、产品视觉细节或单一事故直接晋升为全局规则。
- 不修改 `gongtu-project` 或 `canvas-storm` 的业务实现。
- 不覆盖目标仓库中现有未提交改动，不使用破坏性Git命令。
- 不以“写了文档”代替自动化、测试和真实调用证据。

## 4. 经验晋升合同

每条候选经验必须包含：

```text
id
source_projects
evidence_paths
observed_problem
repeated_pattern
proposed_rule
target_scope: project | profile | system
enforcement: guidance | template | check | automation
counterexample_or_limit
verification
```

晋升规则：

1. 单项目事实默认留在项目层。
2. 跨两个项目重复，或被用户明确多次纠正且影响高，可进入 Profile 候选。
3. 能稳定机器判断的规则优先进入系统 check/automation，不只写成提示词。
4. 高风险规则必须保留人工确认或停止条件，不能自动修改业务事实。
5. 每条晋升都能追溯到本地证据路径，不能凭聊天印象创造“经验”。

## 5. CDS Goal 合同

系统生成或审核的正式 Goal 至少必须具备：

- 唯一权威入口；
- 目标与“不是做什么”；
- 当前事实、事实源与未知项；
- 范围、非范围和产品/安全硬规则；
- 依赖有序的阶段和每阶段可独立验收小节点；
- 每项 acceptance 对应直接证据位置；
- PR/提交边界；
- 普通反馈、范围新增、阻塞和高风险错误的分类规则；
- 失败、阻塞、停止和恢复条件；
- completion audit；
- 可复制的开 Goal 目标文本。

短任务可以使用精简 Goal，但不得省略事实、验收、证据和完成审计四个核心部分。

## 6. 阶段计划与证据栏

| 状态 | 阶段 | 交付 | 验收 | 证据 |
|---|---|---|---|---|
| [x] | E1 本机归属与证据审计 | 仓库清单、证据索引、候选经验 | 5个工作副本/4个唯一远端；经验可追溯；项目细节未误晋升 | `docs/evolution/evidence-audit-v1.json`；真实owner发现命令 |
| [x] | E2 晋升设计 | 项目/Profile/系统三级决策表 | 每条候选有适用边界、执行方式和反例 | `docs/evolution/learning-candidates-v1.json`共7条候选 |
| [x] | E3 系统增强 | learning/automation/goal增强及测试 | 能发现归属项目、生成候选、检查CDS Goal；不自动修改业务仓库 | 13项unittest；owner发现、portfolio与goal lint实跑通过 |
| [x] | E4 Profile增强 | 长期规则、CDS模板、索引与维护协议 | 新Agent能找到并正确使用；与现有文档无冲突 | `CDS_GOAL_WORKFLOW.md`、`EVIDENCE_LEARNING_WORKFLOW.md`及四个入口链接检查 |
| [x] | E5 全链路验证 | 单元测试、临时目录演练、三个真实工作副本只读演练 | 输出稳定、无越界扫描、无未验证完成项 | 临时CODEX_HOME安装；证据数34+6+10；来源Git状态前后一致 |
| [x] | E6 发布与完成审计 | 两仓库提交、推送、最终审计 | 提交范围清晰、远端可见、所有显式要求有证据 | xixi-dev-system `4d14bab` / PR #12；xixi-agent-profile `762b3a9` / PR #3 |

## 7. PR与提交边界

- `xixi-dev-system`：系统实现、自动化提示、Schema、测试和系统文档为一个系统演进提交/PR范围。
- `xixi-agent-profile`：规则、模板、索引和长期记忆协议为一个Profile演进提交/PR范围。
- 不把两个Git仓库伪装成一个提交。
- 若现有分支包含同一系统演进的前序改动，应审计后共同提交；若包含无关改动，必须排除或停止并记录。

## 8. 停止条件

遇到以下情况不得自动推送：

- 目标仓库现有改动无法判断归属或与本Goal冲突；
- 测试失败且不能在本Goal范围内安全修复；
- Git远端或分支与当前事实不一致；
- 经验晋升会泄露密钥、用户数据、受版权保护内容或项目私有事实；
- 需要改写远端历史或覆盖他人提交。

## 9. Completion Audit

只有以下全部成立才能标记 complete：

- [x] 扫描范围由本机 `origin` 证据锁定为5个工作副本/4个唯一远端，未读取远端正文。
- [x] `gongtu-project` 两个工作副本与 `canvas-storm` 均有证据索引。
- [x] 每条晋升经验有来源、边界、反例和执行方式。
- [x] CDS Goal 写法已进入系统检查/模板和 Profile 长期规则。
- [x] 新能力有自动化测试和临时目录演练。
- [x] 两个目标仓库的现有改动已审计且未被覆盖。
- [x] `xixi-dev-system` 与 `xixi-agent-profile` 分别提交并推送，并建立独立PR。
- [x] 最终报告列出真实完成项、未完成项、验证命令和提交哈希。

发布证据：

- `xixi-dev-system`：提交`4d14bab`，分支`cx/goal-state-kernel-v1`，PR `https://github.com/xixinikl/xixi-dev-system/pull/12`。
- `xixi-agent-profile`：提交`762b3a9`，分支`cx/industrial-dev-os`，PR `https://github.com/xixinikl/xixi-agent-profile/pull/3`。
- 两个PR均以各自`main`为目标，不跨仓库混合提交。

## 10. 开 Goal 使用的目标文本

```text
请按照 docs/goals/xixi-system-evolution-v1.md 执行 Xixi Personal Dev System Evidence Evolution Goal。
以本文为唯一权威入口，只扫描本机 origin 归属 xixinikl 的项目；以 gongtu-project 和 canvas-storm 为经验来源，升级 xixi-dev-system 与 xixi-agent-profile。必须吸收 CDS 式 Goal 写法，按 E1→E6 推进，每阶段以直接证据验收；不得覆盖现有未提交改动，不得用文档代替自动化和测试。完成前执行 completion audit，并分别提交、推送两个目标仓库。
```
