使用 xixi-dev-system 执行“每周个人开发系统回顾”。

目标：用户只接触 xixi-dev-system 一个入口；各产品保持独立视觉；系统规则、偏好、验收和经验逐周变得更健壮，并能跨电脑恢复。

执行：
1. 在本机环境可用时，先运行 owner-scoped 项目发现：只读取本机 Git `origin`，筛选 owner 为 `xixinikl` 的工作副本；同一远端的多个工作副本分别记录。账号过滤不等于读取远端仓库正文的授权。
2. 从 GitHub 读取已登记项目过去一周的新提交、PR和Actions元数据作为协作事实；项目复盘、Goal、验收和交接正文优先读取已选择的本地工作副本。远端代码不得为了周报而执行。
3. 先读取 xixi-agent-profile，再读取各项目自己的 AGENTS.md、状态和规则。不同产品不得复用其他项目的颜色、字体、布局或组件；一致性只约束同一项目内部。
4. 为明确选作经验来源的项目生成只读证据组合包，并对存在`错误复盘.md`、`RETROSPECTIVE.md`或`doc/retrospectives/`的项目运行`learning harvest`，将结果写入该项目本地`.xds/learning/registry.json`。摄取必须幂等：同一来源不重复，内容变化标记`needs_re_review`，缺字段标记`needs_completion`，零条目是合法结果。
5. 自动摄取只形成带原始来源、稳定指纹、缺失字段和状态的候选。晋升前必须运行人工`learning review`：至少两个不同origin支持，或原文存在用户明确纠正且审阅者明确标记高影响；否则只能留项目或拒绝。不得未经审阅直接修改Profile。
6. 只提升有证据、重复出现或影响高、具有明确防复发动作且适用范围清楚的经验。项目专属经验留在项目仓库；跨项目经验进入xixi-agent-profile；可稳定机器判断的能力进入xixi-dev-system。`learning publish`只能发布registry中`approved_for_profile`的候选，并按候选ID幂等防重复。
7. 本周新建或变更的正式长期 Goal 必须通过 CDS Goal 结构检查，并在周报中区分“结构通过”与“业务完成”。
8. 不删除仓库、文件或历史，不做破坏性 Git 操作，不擅自合并产品仓库。
9. 生成面向用户的中文周报，只回答：本周最重要变化、需要用户处理什么、系统学会什么、自动完成什么、下一步最值得做什么。无事项时明确写“本周无需你处理”。不要展示原始日志、内部脚本名或无意义机器统计。

发布周报到 Quality Hub：
1. 安全检出 xixinikl/quality-hub 的最新 main，并创建独立分支 codex/weekly-system-review-YYYY-MM-DD。
2. 按 quality-hub/weekly/README.md 的契约生成 weekly/YYYY-MM-DD.json，同时用完全相同的内容更新 weekly/latest.json。
3. 只允许修改上述两个周报 JSON。不得修改页面、样式、项目代码或其他配置。
4. 运行 node scripts/verify.mjs 和 git diff --check。
5. 验证通过后提交、推送并创建 PR。只有 diff 确实只包含两个周报 JSON 且检查通过时，允许自动合并。
6. 最终回复同时给出 Quality Hub 地址和本周 PR 链接。
