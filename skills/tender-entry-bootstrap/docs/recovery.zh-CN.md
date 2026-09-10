# 恢复手册

本手册覆盖首用引导可能遇到的异常状态。**总原则：保留现场，绝不删掉重来；绝不盲重发；不伪造通过。**

## 状态码 → 处置

### `state_path_unresolved`（状态路径不明）

私人工作区定位失败、权限不明、路径组件异常（符号链接、被文件占用），或 state_tool 退出码 6。

**处置**：停止一切安装类动作。用 `ManageWorkDirs(action="list", scope="current")` 重新确认登记目录；切 primary 不迁移 state；默认目录已移除 ⇒ 不能选任意项目目录补一份。目录本身异常时向用户报告并等待人工修复。

### `capability_blocked`（能力前检失败）

Read 缺 `pdf_mode=render` 渲染读取能力 / ManageTeam 缺 ref/expectedCommit / Delegate 缺 teamId/handoff，或 PDF smoke 渲染依赖报错。

**处置**：把具体阻塞码写入 state 的 `blockedCodes`；如实告知用户等待客户端更新后复测一次；**不安装外部 OCR、不降级用文字层冒充视觉核验、不重复触发已知依赖失败**。

### `installing` 且无回执（在途不明）

state 里有 `attemptId` 与 `installing`，但 fork 回执丢失或本次会话中断。

**处置**：`recovery_required`。可用 `ManageTeam(action="list")` 只读排查是否已出现与来源仓库匹配的团队；**任何情况下不得再次发起 fork_team**，直到人工确认归属。

### `recovery_required`（来源未知 / 不明既有安装 / 崩溃锁）

发现未记录的团队安装、无法确认来源 commit、或 state 工具报告语义损坏/崩溃锁（退出码 2 或 4）。

**处置**：保留现场。同名 ≠ 同一来源：不按名字收养团队。`members.lock.teamId` 与本地不一致可能只是源仓库冗余 ID（平台读取会归一化），不单凭此拒绝；但审批记录里的 teamId 必须是本地真实团队 ID。损坏或未知在途的 state/锁：不删除、不覆盖、不重建（init 是排他的，会自动拒绝），人工决定后可由用户备份并重建。

### `upgrade_required`（清单升级）

技能清单版本高于已安装团队对应的清单版本。

**处置**：仅标记，**保留旧安装继续可用**；不自动 pull / fork / 覆盖用户修改。升级必须由用户在发布新版后明确发起，重新走受控安装与规则核准。

### `waiting_rules_review`（待规则核准）

团队已安装但规则未经真人核准。**工具放行 ≠ 规则核准。**

**处置**：指引用户从侧栏进入总审会话，经总审头像 TL 入口进入目标团队那一组的团队设置（多团队时不用旧 MoreMenu 的第一团队），核对 name + 真实 teamId、审阅规则并确认。入口只读核对现有 team-approvals 记录与 rules.md（本地真实 teamId、正文 LF/去行尾归一化 SHA-256、名册排序去重）；文件 scope 受限读不到 ⇒ 保持 blocked，不改权限、不扫描其他用户、不用本机 HTTP 绕过。缺失/不匹配 ⇒ 维持等待。绝不写删审批文件、不调审批 HTTP、不模拟确认、不因口头确认变 ready。首次导入需真人确认来源（user_confirmed/user_ui_write）。

### `handoff_blocked`（移交受阻）

总审忙、拒绝或接受结果未知。

**处置**：保留私人请求清单，向用户说明；不改目标配置、不另派第二份。先用 `InspectRuns` 确认失败的子 run_id 并核实属于本次会话的委派，然后 `Delegate(action="resume", run_id="<已确认的失败子 run_id>", contextMode="continue")` 续跑该条。恢复前还须用 `InspectRuns` 核对失败 run 的最新且唯一后继；若后继仍在运行，等待它完成；若后继关系不清，停止并报告不确定性，不再次恢复或重新派发。仅在需要纠正时才加 `message`；不重新发起 async 委派。绝不把旧回报当成本次完成。

## 状态工具退出码处置

| 退出码 | 处置 |
| --- | --- |
| 2 状态无效 | recovery_required：保留现场，不覆盖、不 init 重建；人工审阅后决定备份与重建 |
| 3 用法错误 | 修正命令后重试即可 |
| 4 锁忙 | **活持有者**：等其结束再试，不杀进程不删锁；**疑似崩溃持有者**：recovery_required，人工确认后清理 |
| 5 revision 冲突（CAS） | 重新 `read` 取最新磁盘状态，合并意图后以新 expected-revision 提交；不重试覆盖 |
| 6 路径不可解析 | 见 `state_path_unresolved` |

## 边界提醒

- 本技能不发布任何东西；`release-manifest.json` 的 `status` 从 `draft` 变 `released` 只能发生在真实发布之后，且必须回填真实 HTTPS URL、真实 40 位 ref/expectedCommit、真实成员名册与资产哈希——缺一即回到 `draft` 语义。
- 离线结构校验不能证明远端仓库存在或内容已审；真实性由发布回执与后续安装核验保证。
