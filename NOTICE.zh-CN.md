# 第三方声明

## 组件与运行时

本 Agent 以 DesireCore Agent 文件形式分发，不打包任何第三方库。其 Python 脚本仅使用 Python 标准库。

以下组件**不属于**本 Agent，由其各自提供方按独立许可条款提供：

| 组件 | 提供方 | 用途 | 许可 |
| --- | --- | --- | --- |
| Python 运行时 | Python 软件基金会（或系统供应商） | 执行 Agent 脚本 | Python Software Foundation License |
| DesireCore 平台 | DesireCore | Agent 运行时、工具、图形界面、工作目录管理 | 见已安装 DesireCore 版本附带的 LICENSE/NOTICE |
| 云端模型服务 | 各供应商（通过 DesireCore 算力配置） | 文档分析、文本生成、图像理解 | 各供应商自有条款与定价 |
| PDF 渲染能力 | DesireCore 平台 | `Read(pdf_mode=render)` 页面渲染（由平台提供，非本 Agent 打包） | 见已安装 DesireCore 版本附带的 LICENSE/NOTICE |

**许可说明：** 本 Agent 的 MIT 许可仅覆盖本目录内的原创资产（代码、文档、persona、principles、skills）。不重新许可或扩展至 Python 运行时、DesireCore 平台、云端模型服务或任何其他第三方组件。各组件均按其安装版本的许可条款使用。

## 本 Agent 不包含以下内容

- 无 OCR 引擎
- 无网页抓取或 URL 上传库
- 无电子邮件客户端库
- 脚本中无外部网络调用
- 无打包的模型权重或 API 密钥

## 资产来源

本 Agent 目录中的所有原创文件由标书审查贡献者作为 `tender-review-assistant` Agent 的一部分编写。

入口引导技能（`skills/tender-entry-bootstrap/`）中包含一份非敏感的 smoke PDF（`assets/smoke-tender-entry.pdf`），该文件为合成测试文件，不含标书内容、个人数据或报价信息。
