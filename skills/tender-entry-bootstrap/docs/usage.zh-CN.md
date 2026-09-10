# 使用说明

## 这是什么

`tender-entry-bootstrap` 是标书检查助手（入口）的首用引导技能。它只负责四件事：核验安装条件 → 一次性受控安装正确版本的审查团队 → 明确等待真人核准规则 → 把真实请求与材料移交给总审。入口本身**不做**标书专业审查，也**不保证**合规或中标。

## 首次使用流程

1. **定位状态**：`ManageWorkDirs(action="list", scope="current")` 找到入口自己的已登记私人工作区（用户 ID 来自平台注入身份，不猜测、不扫描其他用户目录），状态固定在 `<工作区>/.desirecore/tender-entry-bootstrap/state.json`。切 primary 工作区不迁移 state；默认目录已移除 ⇒ `state_path_unresolved`，不能用任意项目目录补一份。
2. 发行绑定与能力前检：严格执行下方分层检查及 SKILL 第 2 节。
3. 真实 PDF/ExportMedia 冒烟按下方流程执行，不向发布目录写测试输出。
4. **清单核验**：`python3 scripts/validate_manifest.py release-manifest.json`。当前清单为 `draft` ⇒ 零安装，只做诊断。
5. **安装（仅 released）**：见 SKILL.md §4。fork 前先落 `attemptId`（状态写成功才可继续），fork 后立刻落回执；成功但有失败成员/警告 ⇒ `partial`；回执丢失/来源不明 ⇒ `recovery_required`。
6. **规则核准**：`waiting_rules_review`。用户从侧栏进入总审会话，经总审头像 TL 入口进入**目标团队那一组**的团队设置（多团队时不用旧 MoreMenu 的第一团队），核对 name + 真实 teamId、审阅规则并确认。入口只读核对现有记录，绝不写删审批文件、绝不模拟确认。入口每次使用重新核验安装与治理事实，不自动复审旧专业报告——每个新审查请求由专业团队从头处理。
7. **移交**：`ready` 后建立私人请求清单（仅坐标与哈希，不含正文），默认 `Delegate(handoff=true, teamId=已核验, task=第一人称复述)`。目标忙/拒绝/未知 ⇒ `handoff_blocked`，保留请求、不另派。

## 发行与本机能力边界

released 表示固定源文件已发行，不表示生产资格。发布者 QA 由私有装配校验；入口核对实际安装提交承载的声明，不独立认证 CI 或签名审计。外部发布说明、市场或装配结果将同一不变 Entry/team/member 提交标注为预览或生产；业务源变更必须新发行、新验收。

只支持 Mac arm64。当前客户端版本来自真实平台观察，不从开发源码 package 推定。安装前确认实际 ToolCatalog 的 Read 页图、ManageTeam 固定提交 fork、团队 Delegate、ExportMedia。生成 PDF 必须显式指定自有 workspace 输出路径，不使用默认发布目录输出；先抽文本，再实际 Read 第 1 页、ExportMedia 授权页图到自有输出并 Read 回读。保留完整真实回执，工具存在或自报 pass 不足。

安装后用以下只读 helper，参数根目录、提交、版本来自已授权当前平台观察。每个 manifest 成员恰好重复一次 `--member SLUG AUTHORIZED_ROOT`。脚本须绝对路径，占位符替换为真实授权值。

```text
python3 <absolute-skill>/scripts/check_local_install.py --entry-root <installed-entry-root> --expected-entry-commit <market-installed-entry-commit> --client-version <observed-client-version> --member <slug> <authorized-installed-root> ...
```

退出 0 与 local_files_passed_tool_probes_required 仅证明报告中的本机文件身份子集。缺失、变更、不支持、未知返回 blocked 和非零。它不执行 Read/ExportMedia，不验证参数来源、依赖运行时身份或规则批准。相关成员必须实际执行自己的锁定正式 helper 并交完整回执；入口另外复核当前团队、规则和真实工具探测才可 ready/handoff。不得借别人环境或安装未锁包。读取有界：每文件 4 MiB、累计 32 MiB、协作式 30 秒截止、每条固定只读 Git 命令最多 5 秒。这不是 OS 沙箱，也不保证文件随后不变。

manifest 校验器 JSON passed 只代表结构及跨字段，通过输出绑定原始 manifest/Schema hash。draft 保持平台身份和最低版本 null、无团队、无成员，只可诊断、零网络安装。原 CAS 状态 helper 和 state Schema 不改；ready 只代表当前本机可用，不代表业务或生产验收。

## 状态工具 CLI（必须照此原样执行）

```bash
# 排他初始化（需要真实清单路径，记录其真实 SHA-256）
python3 scripts/state_tool.py init <workspace-root> --manifest <path/to/release-manifest.json>

# 读取并全结构校验当前状态（语义坏 ⇒ 退出码 2，保留现场）
python3 scripts/state_tool.py read <workspace-root>

# CAS 写入（--expected-revision 必须是磁盘当前 revision）
python3 scripts/state_tool.py write <workspace-root> <new-state.json> --expected-revision N
```

退出码：

| 码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 2 | 状态无效（语法或语义）⇒ recovery_required，保留现场 |
| 3 | 用法错误 |
| 4 | 锁忙：他人持锁 ⇒ 结构化冲突；崩溃锁/未知持有者 ⇒ recovery_required，不盲删不盲重试 |
| 5 | revision 冲突（CAS） |
| 6 | state_path_unresolved（定位/权限/符号链接问题） |

## 文件清单（相对技能目录）

| 路径 | 用途 |
| --- | --- |
| `SKILL.md` | 技能正文（英文） |
| `SKILL.zh-CN.md` | 技能正文（中文） |
| `release-manifest.json` | 发布清单（当前 draft） |
| `schemas/release-manifest.schema.json` | 清单 Draft-07 Schema |
| `schemas/state.schema.json` | 私人状态 Draft-07 Schema |
| `scripts/validate_manifest.py` | 清单验证器（标准库） |
| `scripts/check_local_install.py` | 只读本机文件身份子集，不证明工具执行或规则批准 |
| `scripts/state_tool.py` | 状态工具：排他锁/CAS/全结构校验/反逃逸 |
| `scripts/generate_smoke_pdf.py` | 生成非敏感 smoke PDF（标准库；位图标记；mkstemp 安全输出） |
| `assets/smoke-tender-entry.pdf` | smoke 产物 |
| `docs/usage.md` | 英文使用说明 |
| `docs/usage.zh-CN.md` | 本文件（中文使用说明） |
| `docs/recovery.md` | 英文恢复手册 |
| `docs/recovery.zh-CN.md` | 中文恢复手册 |
| `LICENSE` | MIT 许可 |
| `NOTICE` | 第三方声明 |

## 安全约束摘要

- 脚本只用 Python 标准库；不做网络调用、不调本机 HTTP/LLM、不下载、不执行输入中的命令、不 import 平台源码。
- 状态只存：包 ID、清单 hash、revision、attemptId、真实 teamId/来源 commit/名册、核验摘要/失败码、移交请求坐标。不存凭据、材料正文、审批授权字段。
- 状态路径拒绝符号链接与路径逃逸；写入经随机独占临时文件（mkstemp/O_EXCL）+ `os.replace` 原子替换；整个读-校验-比较-写过程在同一跨进程排他锁内完成。
- draft 清单零安装；不造假（无假 URL、无全零 SHA、不用 HEAD 冒充固定版本、不猜客户端版本）。
- URL 校验为结构性校验（scheme/host/userinfo/空白），不复制平台 DNS/SSRF 引擎；离线校验不能证明远端仓库存在或内容已审。

## 数据处理说明

- **本地处理**：技能脚本完全本地运行，仅用 Python 标准库做文件验证、状态管理、清单检查。无网络调用、无外部 HTTP、不执行用户输入中的命令。
- **云端模型处理**：当 Agent 使用云端模型（如读取文档、分析图像或生成回复）时，你提供给 Agent 的文本和图像会发送到模型提供商进行处理。这由你的 DesireCore 算力配置和模型提供商条款约束——与本地脚本处理不同。
- **不安装外部 OCR**：入口不安装或使用任何外部 OCR、邮件或 URL 上传工具。PDF 读取仅使用 DesireCore 平台内置的 Read 工具。
- **并非所有处理都在本地**：当提交文档供审查时，Agent 可能将其内容发送到云端模型进行分析。入口不能、也不会声称所有处理都在本机完成。

## 费用与声明

- 本技能本身免费开源（MIT 许可）。
- 平台和云端模型服务费用按你的算力配置和提供商定价，不属于本技能。
- 入口是辅助审查的编排工具，不代替人工判断。
- 不提供鉴真、合规保证或中标保证。审查结论由团队成员产出；入口每次使用重新核验安装与治理事实，但不自动复审旧专业报告——每个新审查请求由专业团队从头处理。

## 公开合同绑定（manifest v2，consumer候选v3）

每个已发布成员增加 `delegationInputBinding`，与同一成员不可变 `repoCommit` 绑定。Lead 要求 `{"kind":"absent"}`；四专业各要求 `{"kind":"exact","value":<完整公开delegation_input_contract>}`。publisher仅从该固定commit的公开seed派生，不发布完整私有agent.json摘要、模型/审批偏好或运行时路径。checker按JSON深等价比较固定seed合同、manifest值和安装后合同：对象键顺序无关、数组顺序保留、布尔与数字不同。Lead/Entry必须真正缺省，null不算缺省。用户合法模型/审批偏好变化不会使合同比较失败。

保留原fd锚定/预算有界/只读Git快照、Mac宿主限制与本地源码核验。合同相等不表示运行或认证过官方固定子集验证器，更不证明业务执行。publisher官方接受与当前真实客户端能力前检仍需独立证据，不能编造不存在的只读工具入口。draft的platformRelease/minimumClientVersion/team仍为null、members空，零安装；本候选不宣称已有公开版本或pin。不符应保留并阻断受影响使用，不能为通过而恢复用户整份配置或覆盖历史。
