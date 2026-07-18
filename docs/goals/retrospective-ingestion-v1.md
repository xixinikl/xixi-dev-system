# Retrospective Ingestion Reliability Goal

> **唯一权威入口**：本文件定义错误复盘自动摄取、审阅、发布和自动任务恢复的事实、范围、门禁、证据与完成审计。

## 当前事实

- owner-scoped项目发现、证据portfolio和CDS Goal lint已经存在。
- 旧系统只能索引`错误复盘.md`标题和哈希，不能自动形成字段化候选。
- Profile已有`GROWTH_LOOP.md`与`LEARNINGS.md`，但发布前缺少机器可验证的review状态。
- `bootstrap-new-machine.sh`已有周任务恢复能力，需要与统一命令和稳定automation id收敛。

## 目标

让系统可靠摄取项目错误复盘，但不自动污染Profile；让任何Agent打开或clone dev仓库后都知道并能幂等恢复同一自动摄取任务。

## 范围

- 读取owner匹配的本机项目复盘文件。
- 支持当前中文字段和结构化模板。
- 原文证据、稳定指纹、缺失字段、内容变化、零状态和幂等registry。
- 跨origin或高影响用户纠正的人工晋升门禁。
- 只发布已审阅候选并幂等防重复。
- Dev仓库入口、Skill、README、自动化提示、安装与bootstrap恢复。

### 不包含

- 不使用LLM猜测缺失根因、规则或验证。
- 不因摄取成功自动批准晋升。
- 不自动提交业务项目或原始registry。
- 不删除重复自动任务；发现重复时停止并报告。

## 阶段计划与证据

| 状态 | 阶段 | 验收 | 证据 |
|---|---|---|---|
| [x] | R1 合同与Schema | 状态机、字段、门禁和Schema明确 | `system/learning-registry-v1.schema.json`、本Goal和Profile工作流 |
| [x] | R2 Harvest内核 | 旧格式、缺项、变化、幂等、零状态和敏感信息阻断正确 | 18项测试中的harvest与脱敏边界测试 |
| [x] | R3 Review/Publish | 跨项目/高影响门禁和发布幂等正确 | 单源拒绝、高影响纠正通过、重复发布测试 |
| [x] | R4 自动任务恢复 | clone入口、安装、bootstrap使用稳定id且拒绝重复 | `AGENTS.md`、安装器、bootstrap与ensure-learning测试 |
| [x] | R5 真实项目验收 | 三个来源工作副本只读摄取，无源项目改动 | 51候选：48待审、3缺项；第二次51 unchanged；Git状态前后一致 |
| [x] | R6 GitHub发布 | 两仓库提交推送，现有PR更新 | xixi-dev-system`cb0d689`进入PR#12；Profile`a9c1a89`进入PR#3且doctor成功 |

## 停止条件

- owner不匹配、registry结构损坏或多条同名自动任务存在。
- 自动化试图推断缺字段、直接写Profile或修改来源项目。
- 远端分支有未整合变化、测试失败或出现密钥/隐私内容。

## Completion Audit

- [x] 原始目标中的自动摄取、健壮门禁、自动任务恢复和GitHub发布均有直接证据。
- [x] 旧格式、缺字段、内容变化、重复运行、零状态均有测试。
- [x] 密钥、Token、Cookie、密码或私钥触发`blocked_sensitive`，registry字段与摘录均脱敏。
- [x] 单项目普通候选不能晋升；跨origin或高影响用户纠正可经人工审阅晋升。
- [x] 未审阅候选不能发布；重复发布不产生重复Profile条目。
- [x] Agent从dev仓库`AGENTS.md`和Skill可找到完整流程。
- [x] install/bootstrap恢复同一稳定自动任务，重复实例触发停止。
- [x] 三个来源工作副本前后Git状态一致。
- [x] 两个GitHub PR包含最新提交。

发布证据：

- xixi-dev-system：`cb0d689 feat: automate reviewed retrospective ingestion`，PR `https://github.com/xixinikl/xixi-dev-system/pull/12`。
- xixi-agent-profile：`a9c1a89 docs: define reviewed retrospective ingestion`，PR `https://github.com/xixinikl/xixi-agent-profile/pull/3`，Profile doctor GitHub Action成功。
- 当前机器全局Skill和命令已执行`install-local.sh --upgrade`；`weekly-personal-dev-system`自动任务已创建/更新且匹配实例数为1。

## 开 Goal 目标文本

```text
按照 docs/goals/retrospective-ingestion-v1.md 执行错误复盘自动摄取可靠性Goal。以本文为唯一权威入口，按R1→R6推进；自动摄取不等于自动晋升，缺证据不得补写，测试和真实只读演练通过后更新xixi-dev-system与xixi-agent-profile现有PR。
```
