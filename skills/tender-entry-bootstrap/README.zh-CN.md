# 标书检查助手 — 首用引导技能

标书检查助手（tender-review-assistant）的首用引导技能。

**做什么：** 新用户从市场安装本 Agent 后，本技能核验安装条件、一次性受控安装审查团队（仅在团队已真实发布时）、明确等待真人核准规则，然后把真实请求交给总审。

**不做什么：** 不自行做标书专业审查，不保证合规、通过审查或中标。

## 核心概念

| 术语 | 含义 |
| --- | --- |
| **入口安装** | 从市场安装本 Agent。这只给你一个入口——不会自动安装审查团队。 |
| **团队安装** | 一个单独的、显式的步骤：用固定 commit 做一次受控 `fork_team` 调用。仅在清单为 `released` 且能力前检通过时才发生。 |
| **规则核准** | 团队安装后，必须有人类通过 DesireCore GUI 审阅并确认团队规则，才能开始审查。工具放行 ≠ 规则核准。 |
| **就绪（ready）** | 以上全部在本次会话中已核验。每次使用重新核验，不缓存。 |

## 安装

从 DesireCore 市场安装 `tender-review-assistant` Agent。首用引导技能随 Agent 一起安装。

## 发行与本机能力边界

released 表示固定源文件已发行，不表示生产资格。发布者 QA 由私有装配校验；入口核对实际安装提交承载的声明，不独立认证 CI 或签名审计。外部发布说明、市场或装配结果将同一不变 Entry/team/member 提交标注为预览或生产；业务源变更必须新发行、新验收。

只支持 Mac arm64。当前客户端版本来自真实平台观察，不从开发源码 package 推定。安装前确认实际 ToolCatalog 的 Read 页图、ManageTeam 固定提交 fork、团队 Delegate、ExportMedia。生成 PDF 必须显式指定自有 workspace 输出路径，不使用默认发布目录输出；先抽文本，再实际 Read 第 1 页、ExportMedia 授权页图到自有输出并 Read 回读。保留完整真实回执，工具存在或自报 pass 不足。

安装后用以下只读 helper，参数根目录、提交、版本来自已授权当前平台观察。每个 manifest 成员恰好重复一次 `--member SLUG AUTHORIZED_ROOT`。脚本须绝对路径，占位符替换为真实授权值。

```text
python3 <absolute-skill>/scripts/check_local_install.py --entry-root <installed-entry-root> --expected-entry-commit <market-installed-entry-commit> --client-version <observed-client-version> --member <slug> <authorized-installed-root> ...
```

退出 0 与 local_files_passed_tool_probes_required 仅证明报告中的本机文件身份子集。缺失、变更、不支持、未知返回 blocked 和非零。它不执行 Read/ExportMedia，不验证参数来源、依赖运行时身份或规则批准。相关成员必须实际执行自己的锁定正式 helper 并交完整回执；入口另外复核当前团队、规则和真实工具探测才可 ready/handoff。不得借别人环境或安装未锁包。读取有界：每文件 4 MiB、累计 32 MiB、协作式 30 秒截止、每条固定只读 Git 命令最多 5 秒。这不是 OS 沙箱，也不保证文件随后不变。

manifest 校验器 JSON passed 只代表结构及跨字段，通过输出绑定原始 manifest/Schema hash。draft 保持平台身份和最低版本 null、无团队、无成员，只可诊断、零网络安装。原 CAS 状态 helper 和 state Schema 不改；ready 只代表当前本机可用，不代表业务或生产验收。

## 规则核准路径

团队安装后，入口指引用户：

1. 从侧栏进入总审会话。
2. 通过总审头像（TL）入口进入**目标团队**的设置组（不用旧 MoreMenu 的第一团队）。
3. 在设置中核对团队名称和真实 teamId。
4. 审阅规则并确认。

入口只读现有平台记录。绝不写、删或模拟审批文件。

## 失败恢复

- **状态损坏**会在磁盘上保留——绝不删除或重新初始化。由用户决定如何恢复。
- **锁竞争**返回结构化错误（退出码 4）——锁文件绝不强制删除。
- **重复启动**不会重新安装团队。现有状态被重新核验；不一致时返回 `recovery_required`。
- **丢回执**进入 `recovery_required`——绝不盲目重新 fork。

## 数据处理说明

- **本地处理：** 技能的 Python 脚本完全本地运行，仅使用 Python 标准库。执行文件验证、状态管理和清单检查。不发起网络调用、不调用外部 HTTP 服务、不执行用户输入中的命令。
- **云端模型处理：** 当 DesireCore Agent 使用云端模型（如用于读取文档、分析图像或生成回复）时，你提供给 Agent 的文本和图像可能由所选模型提供商进行处理。用户必须拥有将这些材料交给该模型服务处理的权利，并给予相应授权。这不授权将材料发送至其他任何服务。处理由你的 DesireCore 算力配置和模型提供商条款约束——与本地脚本处理不同。
- **不安装外部 OCR：** 入口不安装或使用任何外部 OCR、邮件或 URL 上传工具。PDF 读取仅使用 DesireCore 平台内置的 Read 工具。
- **并非所有处理都在本地：** Python 脚本在本地运行，但文档审查可能涉及将内容发送到你配置的云端模型。入口从未承诺或暗示所有处理都在本机完成——这种说法不准确，我们明确否认。

## 范围

本技能仅提供**入口和编排层**。它：

- 核验条件并安装审查团队。
- 等待真人规则核准。
- 把请求移交给总审。

**状态与数据边界：**
- 入口的私人状态固定在 `<workspace>/.desirecore/tender-entry-bootstrap/state.json`（通过 `ManageWorkDirs` 定位到已登记的 Agent 私人工作区；切换 primary 不迁移 state）。工具的状态文件与用户的标书材料分属不同范围，由不同 scope 管理——不要求用户只能选择 state 目录，也不把 state 目录等同为不得包含材料的目录。

它**不**：

- 做任何专业审查结论（资格、报价、图像证据判断）。
- 保证合规、中标或审查覆盖率。
- 修改其他 Agent、团队或平台审批记录。

## 费用

- 本技能本身免费且开源（MIT 许可）。
- 使用 DesireCore 平台和云端模型服务可能根据你的算力配置和提供商定价产生费用。这些费用属于平台和模型服务，不属于本技能。

## 待完成项

以下事项需要真实发布的团队和平台更新后才能测试：

1. 真实 `fork_team` 安装与回执核验。
2. 同名团队隔离、升级保留、丢回执恢复。
3. GUI 规则核准全链路。
4. 真实 `Delegate(handoff=true)` 移交（含目标忙/拒绝/未知处理）。
5. Released 清单回填与验证。

**在以上全部用真实发布资产验证完成之前，本技能不声称生产就绪。**

## 许可

本技能目录中的所有原创代码和文档在 [MIT 许可](LICENSE) 下发布。此许可仅适用于标书检查贡献者的原创作品。不适用于第三方依赖、Python 运行时、DesireCore 平台或任何模型服务——它们各自在自己的许可和条款下提供。


本机身份检查器逐组件 NOFOLLOW 打开并保留目录描述符。Git 仅读取有界临时 objects/refs 快照，不读取仓库配置、hooks、filters、index 或 alternates；退出清理临时文件，不修改安装源码。链接 worktree 的 gitdir 文件、符号链接及外置对象库均拒绝。原始 blob 比较会拒绝 CRLF 等 checkout 字节转换。这仅验证本机文件，不认证发布者、CI、运行时或生产质量。

## 公开合同绑定（manifest v2，consumer候选v3）

每个已发布成员增加 `delegationInputBinding`，与同一成员不可变 `repoCommit` 绑定。Lead 要求 `{"kind":"absent"}`；四专业各要求 `{"kind":"exact","value":<完整公开delegation_input_contract>}`。publisher仅从该固定commit的公开seed派生，不发布完整私有agent.json摘要、模型/审批偏好或运行时路径。checker按JSON深等价比较固定seed合同、manifest值和安装后合同：对象键顺序无关、数组顺序保留、布尔与数字不同。Lead/Entry必须真正缺省，null不算缺省。用户合法模型/审批偏好变化不会使合同比较失败。

保留原fd锚定/预算有界/只读Git快照、Mac宿主限制与本地源码核验。合同相等不表示运行或认证过官方固定子集验证器，更不证明业务执行。publisher官方接受与当前真实客户端能力前检仍需独立证据，不能编造不存在的只读工具入口。draft的platformRelease/minimumClientVersion/team仍为null、members空，零安装；本候选不宣称已有公开版本或pin。不符应保留并阻断受影响使用，不能为通过而恢复用户整份配置或覆盖历史。
