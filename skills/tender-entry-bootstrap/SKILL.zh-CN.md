# 标书检查首用引导

## L0

本技能只做"入口引导"：核验 → 受控安装 → 等待规则核准 → 移交总审。入口自己不做标书专业审查，不保证合规或中标。

## L1（操作流程）

### 0. 前置事实

- 本技能所有路径均为**相对技能目录**的相对引用（`schemas/`、`scripts/`、`assets/`、`docs/`）。唯一绝对路径例外：私人状态文件（见 §1），它必须固定在入口自己的默认私人工作区内。
- **工作区内 I/O**：技能执行期间产生的任何临时文件、状态候选文件、命令输出捕获和测试产物，**必须**写入当前 Agent 已登记的私人工作区（通过 `ManageWorkDirs(action="list", scope="current")` 获取）。禁止写入系统 `/tmp`、技能发布目录、用户标书文件夹或工作区外的任何路径。在工作区内使用独占文件名或子目录以避免冲突。
- **脚本调用**：所有对技能脚本（`validate_manifest.py`、`state_tool.py`、`generate_smoke_pdf.py`）的调用**必须**使用从技能目录解析的真实绝对路径——禁止使用依赖 cwd 的相对路径。
- **命令审计**：每次命令执行必须捕获并记录完整的 stdout、stderr 和真实退出码，包括失败情况。退出码 0 绝不能在命令未实际运行或输出未被捕获时被假定或替代。遗漏或丢失的退出码记录为 `exit_code_not_captured`，而非 0。

### 1. 定位私人状态

- 用 `ManageWorkDirs(action="list", scope="current")` 取已登记的私人工作区，用户 ID 必须来自平台注入身份，**不得猜测、不得扫描其他用户目录**。
- 状态文件固定为 `<私人工作区>/.desirecore/tender-entry-bootstrap/state.json`。**不跟随**任意当前 cwd，**不放**技能发布目录或用户标书目录。
- 定位失败或权限不明 → 记 `state_path_unresolved`，停止安装类动作。
- 状态读写一律用 `scripts/state_tool.py`（argparse 子命令：`init <工作区> --manifest <清单路径>` / `read <工作区>` / `write <工作区> <新状态文件> --expected-revision N`）。跨进程排他锁覆盖"读现 state → 全结构校验 → revision 比较 → 候选校验与自洽检查 → 同目录原子落盘"全过程；退出码 0 成功、2 状态无效（语法或语义，保留现场）、3 用法错误、4 锁忙（他人持锁，结构化冲突）、5 revision 冲突、6 路径不可解析。符号链接与路径逃逸被拒绝；排他初始化；崩溃锁或未知在途记 `recovery_required`，不盲删锁、不盲重试、不重复 fork。
- **state 禁止存储**：凭据、用户材料正文、任何"审批已批准/规则已核准"授权字段。核准每次使用都重新只读核验，不缓存。

### 2. 发行绑定与本机前检（不可跳过）

- 固定 Entry 仓提交与真实市场安装来源承载发布者声明。通过已授权的平台安装记录取得真实身份；不得由 manifest 自证、同名 Agent 或调用者自报 hash 推定可信。来源不明阻止安装和使用。manifest 校验器只查结构及跨字段，不认证 CI、签名或发布者 QA；发布者发行审计在装配时独立核验，新人不重跑。
- 用实际安装的 `scripts/validate_manifest.py` 校验安装的 manifest；JSON 输出必须为 `status=passed`，原始 manifest 和 Schema hash 相符且真实退出码 0。draft 保持平台身份和最低版本 null、零安装。released 不代表生产就绪；预览或生产资格在外部绑定不变的发行提交。
- 从真实平台事实取得当前客户端版本，核对已发行且非 null 的最低版本。只支持 Mac arm64，未知或其他主机明确 unsupported 并在本机停止；不把开发源码版本当正式发行。
- 安装前通过真实 ToolCatalog 确认 Read 页图、ManageTeam 不可变 `ref`/`expectedCommit`、Delegate 团队 handoff 和 ExportMedia。参数严格跟随当前工具 Schema，不照抄历史例子。能力缺失阻止受影响使用，不虚构参数或降级为纯文本冒充图像验证。
- 在入口自有私有 workspace 做真实 PDF/图片冒烟：用既有生成脚本的正式输出参数生成公开合成 PDF，先抽文本，再实际 Read 第 1 页图确认仅图片携带的标记；对返回的已授权媒体指针实际 ExportMedia 到自有私有输出，再 Read 导出图片。保留精确 request、完整 response/stdout/stderr/真实 exit（适用时）、当前 turn/run 与输出身份。工具目录存在或 JSON 自称 passed 不是已执行探测。不需要外部 OCR、全局安装或开发者安全审计。
- 完成受控团队安装后，调用 `scripts/check_local_install.py`：Entry 根和预期 Entry 提交来自真实安装回执，当前客户端版本来自真实平台观察，各成员根来自已授权 ManageTeam/ManageAgent 返回。脚本只读检查本机 Mac、Entry 已提交 Skill 的变更、成员提交、不可变 UUID/版本及全部 criticalAssets hash；不会返回 ready，`local_files_passed_tool_probes_required` 仅为文件身份子集。所有 `notVerified` 项仍未获此脚本证明，不向报告输出原始私有配置。
- 每个成员必须自己调用 `ManageWorkDirs(action="list", scope="current")` 发现已登记的私有 workspace，入口自己的 list 不能代替成员。团队共享 cwd 不是私有运行时位置；禁止遍历其他 Agent 用户目录或从猜测的相对路径找 venv。Agent 自管环境不一定列在平台 Hatch/Volta 清单。成员在当前初始化明确授权输出位置交付非秘密回执，包含解释器身份/版本、环境前缀、lock hash、所需正式 helper 的真实冒烟及当前 producer/run/task 身份。入口只读明确授权交付的回执；不可访问、缺失、过期则阻断该功能，不回退读取旧私有 run。公开 manifest 不包含运行时路径、私有回执或用户身份。
- 专业使用前，各相关成员核验自己的锁定运行时，并对授权的非敏感前检输入执行所需已安装正式 helper。Evidence 核锁定 validator 和适用的 Lead TaskSpec checker；Visual 核锁定图片 helper 与适用的 ROI coverage helper；Requirements、Commercial 使用各自必要的正式流程。采用当前安装 Skill/锁/Schema、精确版本和完整真实回执。禁止借别人环境、未锁替代包或自造替代脚本。入口收集回执不改成员输出；依赖或 helper 证据缺失、未知、失败则阻止受影响功能。
- 每次 handoff 前复核安装、团队、资产 hash 与真实人工规则确认；复用原 CAS/state phase/blockedCodes。ready 只记录当前本机可用，不代表业务正确、QA 认证或生产验收，不存授权通过标记。manifest 或源变更走升级处理，不静默刷新 hash 或再次 fork。

### 3. 清单核验

- `python3 scripts/validate_manifest.py release-manifest.json` 必须先过。
- `status="draft"`（当前真实状态）⇒ **零 fork、零网络安装**：只允许做能力诊断并把阻塞写入 state；禁止任何 fork_team/远程安装动作。
- `status="released"` 且 §2 的安装前来源/客户端/工具检查通过 ⇒ 进入 §4。安装后文件/运行时/helper/规则检查在该次安装后进行，必须先于 §6 handoff 通过，不作为创建团队的前置。清单升级（packageVersion/内容变化）只标 `upgrade_required`，保留旧安装，**不自动** pull/fork/覆盖用户修改。

### 4. 受控安装（仅 released）

1. 先检查 state：若已有本次清单对应的 `teamId`，走**核验复用**：`ManageTeam(get)` 核实名册/版本/真实目录，只读核对源 commit 历史与关键资产哈希，`ManageAgent(get)` 逐个核验成员。**禁止按团队 name 收养同名团队**——只认 state 记录的真实 teamId 与 fork 回执。
2. 无记录才新安装：先把 `attemptId` 与时间写入 state（phase=`installing`），再**只调用一次** `ManageTeam(action="fork_team", url=<清单>, ref=<40位SHA>, expectedCommit=<同一40位SHA>, installMembers=true)`，立即把返回的 teamId/resolvedCommit 落盘。
3. 工具返回 success 但存在失败成员或警告 ⇒ `partial`，如实记录，不宣称完整就绪。
4. 回执丢失、来源未知、或发现不明既有安装 ⇒ `recovery_required`，保留现场，**不盲重发**；不得发明 `install_members`/`approve` 之类不存在的工具。

### 5. 等待规则核准

- fork 成功后置 `waiting_rules_review`。**全部工具调用放行不等于规则核准**。
- 指引用户：从侧栏进入总审会话，通过总审头像 TL 入口进入**目标团队那一组**的团队设置（多团队时不要使用旧 MoreMenu 的"第一个团队"），在设置中核对团队 name + 真实 teamId，审阅规则并确认；后续平台会提供明确打开并返回团队 ID 的设置入口。然后回到入口继续。
- 入口只允许在已授权范围内**只读**平台现有 team-approvals 记录与 `rules.md`，核对 teamId、正文归一化（LF/去行尾空白）SHA-256、名册（排序去重）。注意：`members.lock.teamId` 可能是源仓库的冗余 ID，平台读取时会归一化为本地 ID，**不能单凭此差异拒绝**；但审批记录中的 teamId 必须是本地真实团队 ID。缺失/不匹配/读取受限（文件 scope 受限读不到核准记录）⇒ 维持 `waiting_rules_review` 并保持 blocked，**绝不凭口头确认变 ready**；不改权限、不扫描其他用户目录、不用本机 HTTP 绕过。
- 绝不写删审批文件、不调审批 HTTP、不模拟用户确认。每次使用重新核验，不永久缓存"已核准"。首次导入规则需真人确认来源（user_confirmed/user_ui_write），不能把 team_imported 仅采纳名册当作正文已审。

### 6. 移交总审

- `ready` 后只建立**私人请求清单**：原始要求、已授权文件绝对路径/媒体指针、哈希、缺失材料、原件只读约束。清单只存坐标，不存材料正文。
- 默认移交：`Delegate(target=<清单中的总审 slug>, handoff=true, teamId=<已核验 ID>, task=<以用户第一人称忠实复述原始请求>, context=<材料坐标与约束>)`，由平台切到总审会话；入口之后不再重复审查。
- 目标忙/拒绝/接受结果未知 ⇒ `handoff_blocked`：保留请求，说明原因；不改目标配置，不另派第二份。
- 用本次 `requestId`/`correlationId`/`childRunId` 区分任务；旧回报、或 Delegate 工具单纯返回 success，都不算本次完成。

## L2（边界与反例）

- **入口职责上限**：只做安装条件核验、受控安装编排、核准等待、请求移交。任何标书专业审查结论（资格、报价计算、图像证据判定）只能由团队成员产出。
- **不承诺**：不保证合规、不保证中标、不承诺审查覆盖率。
- **禁止**：创建新 Agent；修改总审/专业成员配置；发布团队或技能（发行状态仅由单独授权且审查的发布流程修改）；调用不存在的工具；用假 URL/全零 SHA/HEAD 冒充固定版本；按名称收养团队；二次盲发 fork；删除或绕过审批。
- 更多使用与恢复细节见 `docs/usage.zh-CN.md` 与 `docs/recovery.zh-CN.md`。

## 公开合同绑定（manifest v2，consumer候选v3）

每个已发布成员增加 `delegationInputBinding`，与同一成员不可变 `repoCommit` 绑定。Lead 要求 `{"kind":"absent"}`；四专业各要求 `{"kind":"exact","value":<完整公开delegation_input_contract>}`。publisher仅从该固定commit的公开seed派生，不发布完整私有agent.json摘要、模型/审批偏好或运行时路径。checker按JSON深等价比较固定seed合同、manifest值和安装后合同：对象键顺序无关、数组顺序保留、布尔与数字不同。Lead/Entry必须真正缺省，null不算缺省。用户合法模型/审批偏好变化不会使合同比较失败。

保留原fd锚定/预算有界/只读Git快照、Mac宿主限制与本地源码核验。合同相等不表示运行或认证过官方固定子集验证器，更不证明业务执行。publisher官方接受与当前真实客户端能力前检仍需独立证据，不能编造不存在的只读工具入口。draft的platformRelease/minimumClientVersion/team仍为null、members空，零安装；本候选不宣称已有公开版本或pin。不符应保留并阻断受影响使用，不能为通过而恢复用户整份配置或覆盖历史。
