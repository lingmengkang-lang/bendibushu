# 组态软件（SCADA/HMI）与上位机程序编写

> **分品牌深度能力已拆到独立目录**：
> - `docs/scada/` — 组态软件 **TOP5**（组态王 / MCGS / WinCC / 力控 / 威纶通 EBPro）各一份"AI 自动编程能力"文档；
> - `docs/host/` — 上位机程序样例（你们自己持续补充）。
>
> 本文件保留**通用概念与协议速查**，作为上面两个目录的基础。

本文件覆盖两类"工控人机/监控软件"：**组态软件**（在 PC 或触摸屏上做监控画面、变量、报警、趋势、脚本）与**上位机程序编写**（用 C#/Python/LabVIEW 等自己写 PC 端软件，通过通信协议读写下位机）。
所有内容**仅供起草与教学**，须工程师审核并在离线/仿真环境验证（见 `SAFETY.md`）。

## 一、组态软件（SCADA / HMI 配置软件）

组态软件的核心套路各家大同小异，掌握通用概念即可跨品牌迁移：

| 通用概念 | 说明 |
|---|---|
| **变量 / 标签（Tag）** | 分 I/O 变量（绑定设备寄存器）与内存变量（内部计算）；每个变量有地址、数据类型、读写权限 |
| **设备 / 通信驱动** | 在"设备窗口/设备配置"里加 PLC/仪表驱动（串口或以太网），设站号、波特率、IP、端口 |
| **画面** | 启停按钮、状态显示、数据输入、报警列表、实时/历史趋势 |
| **报警 & 趋势** | 触发条件、确认机制、历史存储 |
| **脚本/命令语言** | 组态王"命令语言"、MCGS"脚本程序"、WinCC"VBScript/C 脚本"等，用于复杂逻辑 |

### 常见品牌 / 软件对照
| 品牌/阵营 | 组态软件 | 脚本/语言 | 备注 |
|---|---|---|---|
| 台达 Delta | **DIAEntegro**（台达组态）/ DOPSoft（HMI） | 台达 HMI 宏指令 / 组态脚本 | DIAEntegro 为台达 SCADA 组态；DOPSoft 管台达触摸屏 |
| 组态王 KingView | KingView（北京亚控） | **命令语言**（数据改变/事件/定时） | 经典国产 SCADA；变量分 I/O 变量、内存变量；通过"设备配置"挂 PLC 驱动 |
| 昆仑通态 MCGS | MCGS 嵌入版（屏）/ MCGS 通用版（PC） | **脚本程序**（类似类 C） | 实时数据库 + 设备窗口 + 运行策略；屏与 PC 版通用 |
| 西门子 Siemens | WinCC（TIA 内 / WinCC flexible / WinCC OA） | VBScript / C 脚本 / 图形脚本 | 与 TIA Portal 一体；变量直接绑 DB |
| 三菱 Mitsubishi | GT Designer3（HMI）/ MX Component（PC 通信） | GOT 脚本 / VB.NET(COM) | 上位机可用 MX Component 走 MC 协议 |
| 欧姆龙 Omron | NB/CX-Designer（HMI）/ CX-Server（PC） | NB 宏 / VB | 上位机可用 FINS / CX-Server |
| 威纶通 Weinview | EBPro（EasyBuilder Pro） | 宏（macro） | 第三方屏，跨品牌兼容好 |
| 力控 ForceControl | pSpace / ForceControl（北京力控） | 力控脚本 | 国产 SCADA 另一主流 |
| 通用 | 各品牌屏均可配 | — | Modbus RTU/TCP 是跨品牌通用协议 |

> **AI 能帮什么**：起草**变量点表**（变量名/地址/类型/权限清单）、**设备通信参数**、**命令语言/脚本逻辑**、**画面组态思路**。
> 它**不点 GUI**（不含 RPA）；产出的点表/脚本/参数你填进软件即可。地址映射（如 Modbus 保持寄存器 ↔ PLC D 区）务必按手册核对。

## 二、上位机程序编写（PC 主机软件）

"上位机"指运行在 PC 上的监控/控制软件，通过**通信协议**与 PLC、仪表、变频器、伺服等下位机交换数据。

### 常用语言 / 工具
| 语言/平台 | 典型库 / 组件 | 适用 |
|---|---|---|
| **C# / .NET** | `NModbus`（Modbus）、`S7.Net` / `Sharp7`（西门子 S7）、`OPC UA .NET` | 工业现场最常用，WinForms/WPF 做界面 |
| **Python** | `pymodbus`、`python-snap7`、`python-opcua`、`pyserial` | 快速做采集/测试/数据分析脚本 |
| **LabVIEW** | NI VISA、DSC 模块、Modbus/TCP 工具包 | 测控、仪器集成 |
| **C/C++** | `libmodbus`、`Snap7`、`OPC UA`（open62541） | 性能/嵌入式场景 |

### 常用通信协议
| 协议 | 场景 | 说明 |
|---|---|---|
| **Modbus TCP / RTU** | 跨品牌通用 | TCP 走 502 端口；RTU 走串口；寄存器分线圈/离散输入/保持/输入 |
| **OPC UA / DA** | 跨厂商数据集成 | UA 跨平台、安全；DA 仅 Windows COM |
| **S7（西门子）** | 西门子 PLC | S7-1200/1500 走 TCP；用 S7.Net/Sharp7/Snap7 |
| **MC 协议（三菱）** | 三菱 PLC | 以太网/串口；MX Component 封装 |
| **Ethernet/IP、FINS、串口自由协议、MQTT** | 各场景 | 按设备手册选 |

### 示例：C# 用 NModbus 读保持寄存器（示意，非生产代码）
```csharp
// ⚠️ 包名/版本随 NuGet 演进（NModbus / NModbus4），以官方为准
using Modbus.Device;
using System.Net.Sockets;

using var client = new TcpClient("192.168.1.10", 502);          // PLC 的 IP 与端口
using var master = ModbusIpMaster.CreateIp(client);
ushort[] regs = master.ReadHoldingRegisters(slaveId: 1, startAddress: 0, numberOfPoints: 10);
// ⚠️ 台达/三菱/西门子地址与 Modbus 地址的映射不同，必须按手册换算（如 D0 对应哪个保持寄存器）
```

### 示例：Python 用 pymodbus 读保持寄存器（示意）
```python
# ⚠️ API 随 pymodbus 版本变化（v3+ 为 ModbusTcpClient），以官方文档为准
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("192.168.1.10", port=502)
if client.connect():
    rr = client.read_holding_registers(0, 10, slave=1)   # 起始地址0，读10个，从站1
    if not rr.isError():
        print(rr.registers)
    client.close()
```

> **AI 能帮什么**：起草读写寄存器代码、数据采集/日志、报警、曲线、通信**异常/超时处理**、多线程/异步轮询；也可帮你设计数据字典与寄存器分配表。
> **硬红线**：上位机写入寄存器必须做边界/合法性校验；**软件互锁不能替代硬接线急停**；轮询频率要控制，避免打扰设备。

## 三、给模型的提示词建议（带上品牌/软件/协议）
- "用 **组态王** 写一段**命令语言**，每 500ms 读 **S7-1200** 的 **DB1.DBD0** 并存到内存变量"
- "用 **MCGS 通用版** 怎么建 **西门子 S7-1200** 的**设备窗口**和**变量**"
- "用 **C# + NModbus** 读 **台达 ISPSoft D0~D9** 的保持寄存器，并做**超时重试**"
- "用 **Python + pymodbus** 通过 Modbus TCP 给 **汇川变频器** 写频率给定（40001 对应哪个地址）"
- "**昆仑通态 MCGS** 屏怎么和 **三菱 FX5U** 做 **Modbus TCP** 通信"

## 四、重要提醒
- 以上软件/协议/脚本名随版本变化，**务必以官方最新手册为准**；
- 本文件与 `brands.md`、`commissioning.md`、`SAFETY.md` 仅作方向性参考，**部署前按 `SAFETY.md` 红线审核仿真**；
- 把你们的组态工程样例、上位机程序（**脱敏**：去真实 IP/账号/工艺机密）喂进 RAG（见 `rag_guide.md`），领域准确性会大幅提升；
- **分品牌的变量点表 / 脚本 / 画面清单写法见 `docs/scada/`；上位机样例见 `docs/host/`。**

## 五、关联文档
- `../scada/README.md` — 组态 TOP5 自动编程能力总览
- `../host/README.md` — 上位机样例
- `how_to_extend.md` — 增加新品牌 / 新器件的方法
