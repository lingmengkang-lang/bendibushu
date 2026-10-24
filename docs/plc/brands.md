# 多品牌 PLC / 自动化配件 / HMI / 组态软件 / 上位机 对照速查

本助手覆盖以下**常用品牌**及**自动化配件、人机界面、组态软件、上位机开发**。各品牌指令集、软件、编程习惯差异大，
**以官方手册为最终权威**——把手册喂进 RAG（见 `rag_guide.md`）后，模型可按你实际型号作答。

## 一、PLC 品牌
| 品牌 | 常用编程软件 | 主要语言 | 备注 |
|---|---|---|---|
| **西门子 Siemens** | TIA Portal（博途） | LAD / FBD / **SCL**（≈ST） | S7-1200/1500 主流；SCL 与 IEC 61131-3 ST 高度相近 |
| **三菱 Mitsubishi** | GX Works2 / GX Works3 | 梯形图 / **ST** / SFC | MELSEC iQ-R/iQ-F 系列；指令名与欧系有差异 |
| **欧姆龙 Omron** | Sysmac Studio / CX-Programmer | 梯形图 / **ST** | NX/NJ 系列用 Sysmac；ST 标准 |
| **台达 Delta** | ISPSoft | 梯形图 / ST | 中小型 PLC 性价比高 |
| **信捷 Xinje** | XD/XL 编程软件 | 梯形图 / ST | 国产，指令体系偏日系风格 |
| **汇川 Inovance** | InoProShop（基于 CODESYS） | 梯形图 / **ST** | 国产，CODESYS 内核，ST 标准，兼伺服/变频 |

> 通用建议：以 **IEC 61131-3 ST** 为中立基底（见 `st_template.st`），再按品牌改写；
> SCL、欧姆龙 ST、汇川 ST 与标准 ST 几乎互通，差异主要在库函数名与系统变量。

## 二、自动化配件（伺服 / 驱动 / 变频）
| 类别 | 典型关注点 | 常见通信/配置 |
|---|---|---|
| **伺服电机 + 驱动器** | 原点回归、电子齿轮、力矩/速度/位置三模式、加减速、限位 | 脉冲 + 方向、EtherCAT、Modbus、CANopen |
| **变频器 / 变频电源（VFD）** | 加减速时间、载波频率、电机额定参数匹配、多段速 | Modbus RTU/TCP、模拟量、端子控制 |
| **步进系统** | 细分、电流、加减速 | 脉冲方向 |

## 三、触摸屏（HMI / 人机界面，面板侧）
不同品牌的 PLC 通常搭配各自的 HMI 软件；变量地址、通信协议、画面组态逻辑各不相同。

| 品牌/阵营 | 常用 HMI 软件 | 常见通信驱动 | 备注 |
|---|---|---|---|
| 西门子 | WinCC（TIA 内 / WinCC flexible） | S7(ISO/TCP)、MPI/DP | 与 TIA Portal 一体化；变量可直接绑定 DB |
| 三菱 | GT Designer3（GOT 系列） | MC Protocol（串口/以太网） | 与 GX Works 配套 |
| 欧姆龙 | NB 软件 / CX-Designer（NS 系列） | FINS、Host Link | NB 系列用 NB-Designer |
| 台达 | DOPSoft（台达 HMI） | Modbus、Delta 专有 | 性价比高 |
| 汇川 | InoProShop / HMI 软件 | Modbus TCP、CODESYS 变量 | 与汇川 PLC 同生态 |
| 信捷 | 信捷触摸屏软件 | Modbus、XJ 专有 | 与信捷 PLC 配套 |
| 通用/国产 | MCGS（昆仑通态）、EBPro（威纶通） | Modbus RTU/TCP、多数主流 PLC | 跨品牌兼容好，常被用作第三方屏 |

> HMI 要点：① 通信口/协议必须与 PLC 一致；② 变量地址/类型/读写权限与 PLC 一一对应；
> ③ 画面至少含启停、状态、报警、趋势；④ **离线模拟通过后再下装**（见 `SAFETY.md`）。

## 四、编码器（位置/速度反馈）
编码器把机械位移变成电脉冲/数字量，接 PLC 高速计数器（HSC）或运动控制轴。

| 类型 | 信号 | 典型接口 | 要点 |
|---|---|---|---|
| **增量式** | A/B 正交 + Z 零位 | 差分 RS422 / 集电极开路 | 靠计数得位置；上电需回零；A/B 相序决定方向 |
| **绝对式（单圈/多圈）** | 数字位置 | SSI、EnDat、BiSS-C、Hiperface | 上电即知位置，省回零；首用按手册校准零点 |
| **选型参数** | 分辨率（线数/PPR）、输出形式、轴径、防护等级 | — | 分辨率影响定位精度；注意与 PLC 高速计数频率匹配 |

> 编码器要点：双绞线 + 屏蔽单端接地、远离动力线；A/B/Z 接线与电源上电前核对，
> 极性/相序错会反向计数；AI 可辅助型号选型、接线说明、与 HSC/运动指令配合逻辑。

## 五、组态软件（SCADA / HMI 配置，PC 或屏侧）
组态软件 = 在 PC 或触摸屏上做监控画面、变量、报警、趋势、脚本。通用概念见 `hmi_scada_host.md`。

| 品牌/阵营 | 组态软件 | 脚本/语言 | 备注 |
|---|---|---|---|
| 台达 Delta | **DIAEntegro**（台达组态）/ DOPSoft | 台达 HMI 宏 / 组态脚本 | DIAEntegro 为台达 SCADA 组态；DOPSoft 管台达触摸屏 |
| 组态王 KingView | KingView（北京亚控） | **命令语言**（数据改变/事件/定时） | 经典国产 SCADA；变量分 I/O 变量、内存变量 |
| 昆仑通态 MCGS | MCGS 嵌入版（屏）/ 通用版（PC） | **脚本程序**（类 C） | 实时数据库 + 设备窗口 + 运行策略；屏与 PC 版通用 |
| 西门子 Siemens | WinCC（TIA 内 / WinCC OA） | VBScript / C 脚本 | 与 TIA Portal 一体；变量直绑 DB |
| 三菱 Mitsubishi | GT Designer3（HMI）/ MX Component（PC） | GOT 脚本 / VB.NET(COM) | 上位机可用 MX Component 走 MC 协议 |
| 欧姆龙 Omron | NB/CX-Designer（HMI）/ CX-Server（PC） | NB 宏 / VB | 上位机可用 FINS / CX-Server |
| 威纶通 Weinview | EBPro（EasyBuilder Pro） | 宏（macro） | 第三方屏，跨品牌兼容好 |
| 力控 ForceControl | pSpace / ForceControl（北京力控） | 力控脚本 | 国产 SCADA 另一主流 |

> 组态软件要点：AI 可起草**变量点表**（名/地址/类型/权限）、**设备通信参数**、**命令语言/脚本**；
> 它**不点 GUI**；地址映射（如 Modbus 保持寄存器 ↔ PLC D 区）务必按手册核对（见 `hmi_scada_host.md`）。

## 六、上位机程序开发（PC 主机软件）
上位机 = PC 侧监控/控制软件，通过通信协议读写下位机。详细示例见 `hmi_scada_host.md`。

| 语言/平台 | 典型库 / 组件 | 适用 |
|---|---|---|
| **C# / .NET** | `NModbus`（Modbus）、`S7.Net` / `Sharp7`（西门子 S7）、`OPC UA .NET` | 工业现场最常用，做 WinForms/WPF 界面 |
| **Python** | `pymodbus`、`python-snap7`、`python-opcua`、`pyserial` | 快速做采集/测试/数据分析脚本 |
| **LabVIEW** | NI VISA、DSC 模块、Modbus/TCP 工具包 | 测控、仪器集成 |
| **C/C++** | `libmodbus`、`Snap7`、`open62541`(OPC UA) | 性能/嵌入式场景 |

> 协议：Modbus TCP/RTU（跨品牌通用）、OPC UA/DA（跨厂商集成）、S7（西门子）、MC（三菱）、Ethernet/IP、FINS、串口自由协议、MQTT。
> AI 可起草读写寄存器代码、采集/日志、报警、曲线、异常/超时处理；**写入必须做校验，软件互锁不能替代硬接线急停**。

## 七、给模型的提示词建议
提问时**带上品牌、型号与具体软件/协议**，答案更准，例如：
- "**西门子 S7-1200**，用 **SCL** 写一个电机启停+急停联锁程序"
- "**汇川 IS620P 伺服** 怎么通过 **Modbus** 设置电子齿轮比"
- "**三菱 FX5U** 的 **高速计数器** 怎么配置接 **增量编码器**"
- "**威纶通 EBPro** 怎么和 **台达 ISPSoft** 的 **D0/D1** 变量做 **Modbus TCP** 通信"
- "**变频器** 多段速用 **端子 + Modbus** 怎么设参数"
- "用 **组态王** 写一段**命令语言**每 500ms 读 **S7-1200** 的 **DB1.DBD0**"
- "用 **C# + NModbus** 读 **台达 D0~D9** 保持寄存器并做**超时重试**"
- "用 **MCGS 通用版** 建 **西门子 S7-1200** 的**设备窗口**和**变量**"

## 八、重要提醒
- 以上品牌/软件/指令名/协议可能随版本变化，**务必以官方最新手册为准**；
- 本文件与 `st_template.st`、`hmi_scada_host.md`、`commissioning.md`、`SAFETY.md` 仅作方向性参考，
  **部署前按 `SAFETY.md` 红线审核仿真**。
