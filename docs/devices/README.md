# docs/devices — 常用电气件使用方法

> 这个目录是**你自己持续扩充的器件知识库**：每加一个常用电气件，
> 放一个 md 进来，跑一次 `add-all`，本地助手就能准确回答它的用法、接线、故障码，
> 并按它生成上位机/组态/ST 程序。

## 放什么

- **变频器 / 伺服驱动器**：参数表、Modbus 地址、故障码、调试步骤
- **PLC / 触摸屏**：寄存器映射、通信参数、惯用配置
- **仪表 / 传感器 / 编码器**：量程、接线、协议、校准
- **你自己的调试笔记与踩坑记录**（最有价值，AI 会优先参考）

## 怎么加（三步）

1. 复制 `docs/plc/brand_onboarding_template.md` 的模板，填好保存为
   `docs/devices/<器件名>.md`
2. `python scripts\rag_manager.py add-all`
3. `python scripts\rag_manager.py scan` 确认入库，再 `search` 验证

完整说明见 [how_to_extend.md](../plc/how_to_extend.md)。

## 命名建议

`<品牌>_<型号>_<器件类型>.md`，例如：

- `汇川_MD290_变频器.md`
- `西门子_V90PN_伺服.md`
- `欧姆龙_E6B2_编码器.md`
- `信捷_XD5E_PLC.md`

## ⚠️ 提交前必读（脱敏）

这个目录的文件会进入 Git 仓库。请务必去掉：

- 真实 IP、端口、站号等网络信息（可用 `192.168.x.x` 占位）
- 账号、密码、Token
- 工艺参数、产能、涉密图纸
- 客户名称与项目名称

拿不准的内容，放在 `data/knowledge_base/docs/`（该目录已被 `.gitignore` 排除，不会入库），
或单独加进 `.gitignore`。

## 示例

- [example_通用Modbus变频器.md](example_通用Modbus变频器.md) —— 一份填好的模板示例，演示应该写到什么程度
