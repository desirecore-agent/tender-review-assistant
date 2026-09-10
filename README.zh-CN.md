# 标书检查助手（tender-review-assistant）

DesireCore 平台上的协作式标书审查入口 Agent。

## 功能

安装本 Agent 后，它提供首用引导流程：

1. 核验平台审查所需能力。
2. 安装审查团队（仅在真实团队已发布时）。
3. 等待真人规则核准。
4. 把真实请求与材料移交给总审。

**本 Agent 不自行执行标书专业审查，不保证合规、通过审查或中标。** 所有审查结论由已安装的团队成员产出。

## 关键资源

- **首用引导技能**：[`skills/tender-entry-bootstrap/README.zh-CN.md`](skills/tender-entry-bootstrap/README.zh-CN.md) — 完整使用指南、能力前检、PDF smoke 测试、失败恢复、数据处理说明。
- **English version**：[`skills/tender-entry-bootstrap/README.md`](skills/tender-entry-bootstrap/README.md)

## 许可

本 Agent 目录中所有原创代码和文档在 [MIT 许可](LICENSE) 下发布。

参见 [NOTICE](NOTICE) 了解第三方组件声明（Python 运行时、DesireCore 平台、云端模型服务——各自在自己的许可下提供）。
