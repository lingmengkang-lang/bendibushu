# 组态软件第二梯队 —— AI 自动编程能力

> 除 TOP5 外，这些品牌在现场也很常见，本地助手同样能起草工件。
> 覆盖较浅：给出点表框架、设备配置项、脚本方向与提示词；细节按各品牌手册补齐。

| 软件 | 厂商 | 场景 | 自动编程能力 |
|---|---|---|---|
| **台达 DIAEntegro** | 台达 Delta | 台达自家 SCADA 组态，配台达 PLC/HMI 生态 | 变量点表、设备配置、画面清单、台达 HMI 宏方向 |
| **紫金桥 RealInfo** | 大庆紫金桥 | 国产 SCADA，油气/电力项目多 | 实时数据库点表、驱动配置、脚本框架 |
| **Wonderware InTouch / iFIX** | AVEVA | 老牌外资，存量项目多 | ArchestrA/InTouch  QuickScript、Tag 点表 |
| **Ignition** | Inductive Automation | 新建项目常用，跨平台 | Tag 点表、Expression/Script（Python）、Perspective 画面 |
| **组态王 Web 版 / KingHistorian** | 北京亚控 | 需要 Web 发布与历史库 | Web 工程清单、历史库采集点表 |
| **三菱 GT Designer3** | 三菱 | 三菱 GOT 触摸屏 | 画面清单、GOT 脚本/基本功能、MX Component 上位机 |
| **欧姆龙 NB-Designer** | 欧姆龙 | NB 系列屏 | 元件地址表、宏、事件 |

## 一、台达 DIAEntegro（用户点名要支持）

- **生态定位**：台达自家的组态/SCADA 软件，与台达 PLC（ISPSoft 编程）、HMI（DOPSoft）配套。
- **AI 能产出**：
  - 变量点表（变量名/台达 PLC 地址 D/M/X/Y/继电器/计数器）
  - 设备配置（台达 PLC 型号、通信方式：RS-232/485、Ethernet，COM 号/波特率/IP）
  - 画面清单与动画连接思路
  - 与 DOPSoft 的分工建议（屏内显示 vs PC 端集中监控）
- **提示词**：

```
用【台达 DIAEntegro】做一个【产线计数监控】：
PLC 是【台达 DVP-20PM00，走 Ethernet】，需要【产量计数/节拍/故障报警/趋势】。
输出变量点表（含 D 区地址）+ 设备配置 + 画面清单 + 报警配置清单。
```

## 二、Ignition（Python 脚本，AI 优势明显）

- **特点**：脚本是 **Python**，Jython 环境；有 **Perspective**（现代 Web 端画面）与 Vision（经典桌面）。
- **AI 能产出**：Tag 点表（OPC UA 来源）、Expression Language 绑定、Python 脚本（报警、写入校验）、Perspective 视图结构。
- **提示词**：

```
用【Ignition（Perspective 模块）】做【电机监控】：
数据源是【S7-1200，OPC UA】。输出 Tag 点表 + 视图结构 + 报警配置 +
一段 Python 脚本（读取 Tag 判断联锁，写入时做范围校验）。
```

## 三、三菱 GT Designer3 / 欧姆龙 NB-Designer（HMI 侧）

- 两者都偏"触摸屏组态"，产出**元件地址表 + 画面清单 + 屏内脚本**。
- 上位机侧可分别用 **MX Component**（三菱）与 **CX-Server / FINS**（欧姆龙）配合，见 `docs/plc/hmi_scada_host.md`。

## 四、提示词模板（通用改法）

```
用【<品牌><软件名>】做一个【<场景>】：
下位机是【<PLC/仪表型号>】，通信【<协议，IP/端口/站号/波特率>】，
需要【<监控点列表>】和【<控制/报警需求>】。
请输出：1) 变量点表 2) 设备配置 3) 脚本/逻辑 4) 画面清单
5) 报警/趋势配置 6) 离线仿真验证步骤。
```

## 五、红线（同 TOP5）

- 地址映射必须按各品牌手册人工核对。
- 软件层保护不能替代硬接线急停。
- 上线前离线仿真。

## 六、关联

- TOP5 总览：[README.md](README.md)
- 通用概念：`docs/plc/hmi_scada_host.md`
