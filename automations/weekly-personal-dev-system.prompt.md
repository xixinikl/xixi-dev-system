使用 xixi-dev-system 执行“每周个人开发系统回顾”。

目标：用户只接触 xixi-dev-system 一个入口；各产品保持独立视觉；系统规则、偏好、验收和经验逐周变得更健壮，并能跨电脑恢复。

执行：
1. 从 GitHub 读取 xixinikl 已登记项目过去一周的新提交、PR、Actions、验收报告和复盘候选，以远端事实为准。
2. 先读取 xixi-agent-profile，再读取各项目自己的 AGENTS.md、状态和规则。不同产品不得复用其他项目的颜色、字体、布局或组件；一致性只约束同一项目内部。
3. 只提升有证据、重复出现或影响高、具有明确防复发动作且适用范围清楚的经验。项目专属经验留在项目仓库；跨项目经验进入 xixi-agent-profile；系统能力改进进入 xixi-dev-system。
4. 不删除仓库、文件或历史，不做破坏性 Git 操作，不擅自合并产品仓库。
5. 生成面向用户的中文周报，只回答：本周最重要变化、需要用户处理什么、系统学会什么、自动完成什么、下一步最值得做什么。无事项时明确写“本周无需你处理”。不要展示原始日志、内部脚本名或无意义机器统计。

发布周报到 Quality Hub：
1. 安全检出 xixinikl/quality-hub 的最新 main，并创建独立分支 codex/weekly-system-review-YYYY-MM-DD。
2. 按 quality-hub/weekly/README.md 的契约生成 weekly/YYYY-MM-DD.json，同时用完全相同的内容更新 weekly/latest.json。
3. 只允许修改上述两个周报 JSON。不得修改页面、样式、项目代码或其他配置。
4. 运行 node scripts/verify.mjs 和 git diff --check。
5. 验证通过后提交、推送并创建 PR。只有 diff 确实只包含两个周报 JSON 且检查通过时，允许自动合并。
6. 最终回复同时给出 Quality Hub 地址和本周 PR 链接。
