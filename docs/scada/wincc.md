# 西门子 WinCC —— AI 自动编程能力

> WinCC 家族要分清：**WinCC Professional / Advanced**（TIA Portal 内，最常见）、
> **WinCC V7.x**（经典）、**WinCC OA**（另一个平台，脚本为 CTRL/Java/Python）。
> 本文件针对**TIA Portal 内的 WinCC Professional/Advanced**，这是西门子用户事实标配。
> ⚠️ VBS 属性与方法随版本变化，以你所用版本手册为准。

## 一、核心概念速查

| 概念 | 说明 |
|---|---|
| **变量（Tag）** | 内部变量 / 外部变量；外部变量绑定 PLC 地址（DB、M、Q、I） |
| **连接** | "通信 → 连接"里建 HMI 与 PLC 的连接（Ethernet / PROFINET / Modbus TCP 通道） |
| **HMI 变量表** | 统一管理变量、地址、数据类型、采集周期 |
| **画面** | 图形编辑器，元件 + 动画 + 事件 |
| **报警（Alarm Logging）** | 模拟量/离散量报警、报警类别、确认机制 |
| **记录（Tag Logging）** | 过程值归档，喂给趋势视图 |
| **全局脚本** | VBScript / C 脚本，分项目脚本与画面脚本 |
| **SmartTags** | V7.2+ 提供，可直接 `SmartTags("Tag").Value` 读写 |

## 二、AI 能自动产出什么

- **HMI 变量表**：变量名、数据类型（Bool/Int/Real/DInt）、PLC 地址（DB10.DBD0 等）、采集周期、读写
- **连接配置清单**：PLC 型号、IP、机架/槽号（S7 通道）或 Modbus TCP 参数
- **VBS 脚本**：启停互锁、报警判断、画面切换、用户权限、参数写入校验
- **画面组态清单**：元件、动画、事件、模板/画面对象复用
- **报警与趋势配置清单**：报警类别、限值、归档变量、趋势时间窗
- **离线仿真验证方案**（PLCSIM + WinCC 模拟）

## 三、HMI 变量表样例（AI 输出格式示范）

场景：S7-1200 + 水泵房监控，变量在 DB10

| 变量名 | 数据类型 | PLC 地址 | 采集周期 | 读写 | 说明 |
|---|---|---|---|---|---|
| MotorStart | Bool | DB10.DBX0.0 | 100ms | 读写 | 启动命令 |
| MotorRun | Bool | DB10.DBX0.1 | 100ms | 只读 | 运行反馈 |
| MotorFault | Bool | DB10.DBX0.2 | 100ms | 只读 | 故障 |
| WaterLevel | Real | DB10.DBD4 | 500ms | 只读 | 水位 m，量程 0~10 |
| PressSet | Real | DB10.DBD8 | 500ms | 读写 | 压力设定，0~1.6MPa |
| RunSeconds | Int | DB10.DBW12 | 1s | 读写 | 运行秒累计 |

> ⚠️ DB 内偏移必须与 PLC 程序里的符号表一致；**PLC 侧没这个地址时画面会一直显示 `####`/旧值**。

## 四、VBS 脚本样例

### 4.1 启动/停止按钮的点击事件（带互锁）

```vbscript
' 启动按钮点击：先查故障，无故障才允许启动
Dim runTag, faultTag
Set runTag  = HMIRuntime.Tags("MotorRun")
Set faultTag = HMIRuntime.Tags("MotorFault")

faultTag.Read
If faultTag.Value = True Then
    HMIRuntime.Tags("AlarmMsg").Value = "设备故障中，禁止启动"
    Exit Sub
End If

HMIRuntime.Tags("MotorStart").Value = True
```

### 4.2 全局脚本：水位超限报警 + 自动记录

```vbscript
' 画面循环调用（如 1s 定时器触发）
Dim lvl
Set lvl = HMIRuntime.Tags("WaterLevel")
lvl.Read

If lvl.Value >= 9.5 Then
    HMIRuntime.Tags("WaterHighAlarm").Value = True
Else
    HMIRuntime.Tags("WaterHighAlarm").Value = False
End If

' 累计运行秒（也可放 PLC 侧做，推荐放 PLC）
Dim rs
Set rs = HMIRuntime.Tags("RunSeconds")
rs.Read
If HMIRuntime.Tags("MotorRun").Value = True Then
    rs.Value = rs.Value + 1
End If
```

> ⚠️ `HMIRuntime.Tags("...").Read/Write` 是经典写法；V7.2+ 也可用 `SmartTags("...").Value`。
> ⚠️ 在 VBS 里频繁 `.Read` 有通信开销，别在每个定时器里刷几十个变量。
> **建议把累加/联锁逻辑放 PLC 侧做**，HMI 只做显示与下发命令——这是更稳的分工。

## 五、画面 / 报警 / 趋势配置清单

**画面清单**
1. `总览画面`：水泵房示意图、运行状态灯、水位/压力显示、启停按钮、导航
2. `参数画面`：压力/水位设定输入框（带上下限动画）、权限分级
3. `报警画面`：当前报警 + 历史报警（时间/类别/状态/确认）
4. `趋势画面`：水位/压力实时曲线 + 历史曲线（时间轴可调）

**报警配置要点**
- 离散量报警：MotorFault、水位超限
- 模拟量报警：水位高/低限、压力高/低限，设死区防抖
- 报警类别按"故障/警告/提示"分级，故障类必须确认

**趋势配置要点**
- 归档变量：WaterLevel、PressSet、RunSeconds
- 采集周期与归档周期分开设（采集 500ms、归档 1min 很常见）
- 磁盘占用要估算：变量数 × 采样数 × 保存时长

## 六、提示词模板

```
用【WinCC（TIA Portal，WinCC Professional）】做【水泵房监控】：
PLC 是【S7-1200，IP 192.168.0.1】，变量在【DB10】。
请输出：
1) HMI 变量表（变量名/数据类型/DB 地址/采集周期/读写）
2) 连接配置清单（含机架槽号）
3) VBS 脚本：启动互锁（故障时禁止）、水位超限报警、运行计时
4) 画面组态清单（总览/参数/报警/趋势）
5) 报警与趋势（Tag Logging）配置清单
6) PLCSIM 离线仿真验证步骤
```

```
【WinCC Professional】通过【Modbus TCP 通道】接【汇川 AM400】，
监控【输出频率/电流/故障码】，写【频率给定】。
输出 HMI 变量表（含 Modbus 地址）+ 连接配置 + 写入校验的 VBS。
```

## 七、红线

- **DB 偏移与 PLC 符号表必须一致**，否则画面长期显示旧值（很容易被误认为"程序没跑"）。
- 联锁/保护逻辑放 **PLC**，不要只靠 WinCC 脚本（画面关掉脚本就不执行了）。
- **软件停止按钮不能替代硬接线急停**。
- 大量 `.Read` 有通信开销，注意定时器周期与变量数。
- 归档数据要估算磁盘，避免把 HMI 存储写满。

## 八、关联

- 通用概念：`docs/plc/hmi_scada_host.md`
- 调试清单：`docs/plc/commissioning.md`（第五节）
- 安全红线：`docs/plc/SAFETY.md`
- TOP5 总览：[README.md](README.md)
