# docs/host — 上位机程序样例

> 上位机 = 跑在 PC 上的监控/控制软件，通过通信协议（Modbus/OPC UA/S7/MC/FINS…）
> 读写下位机（PLC、变频器、伺服、仪表）。
> 本目录放**你们自己的上位机样例**，让本地助手按你们的风格生成代码。

## 放什么

- C# / .NET：NModbus、S7.Net/Sharp7、OPC UA（WinForms/WPF 界面思路）
- Python：pymodbus、python-snap7、python-opcua、pyserial
- LabVIEW：VISA、DSC、Modbus 工具包
- C/C++：libmodbus、Snap7、open62541

每个样例建议包含：

1. **寄存器分配表**（哪个地址放什么，AI 最需要这个）
2. 通信参数（协议、IP、端口、站号）
3. 核心代码片段（标注库与版本 ⚠️）
4. 异常/超时/重试处理思路
5. 数据字典与日志格式

## 怎么加

1. 新建 `docs/host/<项目名>.md`（参考 `../devices/example_通用Modbus变频器.md` 的写法）
2. `python scripts\rag_manager.py add-all`
3. `python scripts\rag_manager.py scan` 确认入库

完整说明见 [how_to_extend.md](../plc/how_to_extend.md)。

## ⚠️ 脱敏（重要）

这个目录的文件会进入 Git 仓库。提交前务必去掉：

- 真实 IP / 端口 / 站号（用 `192.168.x.x` 占位）
- 数据库连接串、账号密码、Token
- 工艺参数、客户与项目名称

不能公开的内容放 `data/knowledge_base/docs/`（已被 `.gitignore` 排除）。

## 安全红线（上位机特有）

- **写入寄存器必须做边界与合法性校验**，尤其是频率、压力、位置给定
- **轮询频率要控制**，别把设备通信塞满
- **软件互锁不能替代硬接线急停**；上位机的"停止"只是通信指令
- 首次联机先用**只读**跑通，再逐步开放写操作

## 关联

- 协议与库速查：[../plc/hmi_scada_host.md](../plc/hmi_scada_host.md)
- 组态 TOP5：[../scada/README.md](../scada/README.md)
- 安全红线：[../plc/SAFETY.md](../plc/SAFETY.md)
