# 上位机写入安全模板（必读，写之前先看）

> 本模板对应 `docs/host/README.md` 的安全红线，把"写入校验 / 超时 / 退避 / 轮询下限 / 回读确认"
> 落成**默认代码骨架**。所有通过 Modbus / S7 / MC / FINS 等向下位机写值的程序，都应套用本模板。
>
> ⚠️ 模板只解决"通信层防呆"。**任何启停、联锁、急停仍由 PLC 硬回路 / 安全继电器兜底，
> 上位机的停止只是通信指令，永远不能替代硬接线急停。**

---

## 0. 三条铁律（写任何寄存器前）

1. **写前必校验**：频率/压力/位置/速度等给定值，先夹在合法区间，超出直接拒绝并报警。
2. **通信必超时 + 异常**：所有读写包 `try/except`，设显式超时；失败进入**指数退避重连**（上限封顶），禁止无限重试打爆设备。
3. **轮询有下限**：串口 ≥ 100ms、以太网 ≥ 50ms；能用"批量读"就别"单点狂轮询"。

---

## 1. Python（pymodbus）—— 安全写单个保持寄存器（频率给定 0~500 → 0~50.0Hz）

```python
import time
from pymodbus.client import ModbusTcpClient

UNIT = 1          # 从站站号
FREQ_ADDR = 100   # 保持寄存器地址（0 基；人读 40101）
FREQ_MIN, FREQ_MAX = 0, 500   # 单位 0.1Hz，对应 0~50.0Hz

def safe_write_freq(client, raw_value):
    # 1) 写前边界校验（防呆，最关键的一步）
    if not (FREQ_MIN <= raw_value <= FREQ_MAX):
        print(f"[拒绝] 频率给定 {raw_value} 超出 [{FREQ_MIN},{FREQ_MAX}]，不写入")
        return False

    # 2) 带超时与异常地写
    try:
        # 先连（已连则跳过）；超时 1s
        if not client.connect():
            raise ConnectionError("无法连接下位机")
        # 写单个保持寄存器，unit=从站
        resp = client.write_register(FREQ_ADDR, raw_value, slave=UNIT)
        if resp.isError():
            raise RuntimeError(f"写寄存器返回错误: {resp}")
    except Exception as e:
        print(f"[失败] 写频率给定异常: {e}")
        return False

    # 3) 回读确认（写即信是最危险的习惯）
    try:
        rr = client.read_holding_registers(FREQ_ADDR, count=1, slave=UNIT)
        if rr.isError():
            raise RuntimeError("回读失败")
        if rr.registers[0] != raw_value:
            print(f"[告警] 回读值 {rr.registers[0]} ≠ 写入值 {raw_value}，请核查映射/偏移")
            return False
    except Exception as e:
        print(f"[告警] 回读确认异常: {e}（写入可能已生效，需人工核对）")
        return False

    print(f"[OK] 频率给定写入并确认: {raw_value/10.0:.1f} Hz")
    return True

# 用法示例（带退避重连）
def write_with_backoff(client, raw, max_retry=5):
    delay = 0.5
    for i in range(max_retry):
        if safe_write_freq(client, raw):
            return True
        time.sleep(delay)
        delay = min(delay * 2, 8)   # 指数退避，封顶 8s
    print("[严重] 多次写入失败，请检查设备/网络/地址映射")
    return False

if __name__ == "__main__":
    c = ModbusTcpClient("192.168.1.10", port=502, timeout=1.0)
    try:
        write_with_backoff(c, 350)   # 35.0 Hz
    finally:
        c.close()
```

---

## 2. C#（NModbus）—— 安全写并回读

```csharp
using System;
using System.Threading;
using Modbus;
using Modbus.Device;

class SafeWriter
{
    const byte Unit = 1;
    const ushort FreqAddr = 100;          // 0 基；人读 40101
    const int FreqMin = 0, FreqMax = 500; // 0.1Hz 单位

    // 写前校验 + 超时 + 回读
    static bool WriteFreq(IModbusMaster master, ushort raw)
    {
        // 1) 边界校验
        if (raw < FreqMin || raw > FreqMax)
        {
            Console.WriteLine($"[拒绝] 频率 {raw} 超出范围");
            return false;
        }
        try
        {
            // 2) 写（调用方已设连接超时）
            master.WriteSingleRegister(Unit, FreqAddr, raw);
            // 3) 回读确认
            var rb = master.ReadHoldingRegisters(Unit, FreqAddr, 1);
            if (rb[0] != raw)
            {
                Console.WriteLine($"[告警] 回读 {rb[0]} ≠ 写入 {raw}");
                return false;
            }
            Console.WriteLine($"[OK] 频率写入确认: {raw/10.0:F1} Hz");
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[失败] 写频率异常: {ex.Message}");
            return false;
        }
    }

    // 指数退避重连
    static bool WriteWithBackoff(IModbusMaster master, ushort raw, int maxRetry = 5)
    {
        int delay = 500;
        for (int i = 0; i < maxRetry; i++)
        {
            if (WriteFreq(master, raw)) return true;
            Thread.Sleep(delay);
            delay = Math.Min(delay * 2, 8000);
        }
        Console.WriteLine("[严重] 多次写入失败");
        return false;
    }
}
```

---

## 3. 轮询下限参考（防止通信风暴）

| 介质 | 建议最小轮询周期 | 说明 |
|---|---|---|
| RS-485 / Modbus RTU | ≥ 100 ms | 单条报文 + 帧间隔；过密会丢包/抖动 |
| Modbus TCP / 以太网 | ≥ 50 ms | 可批量读，减少事务数 |
| 多变量 | 合并为 1 次"读多个寄存器" | 优于逐个轮询 |
| 掉线 | 退避重连，封顶 8s | 禁止无间隔狂重连 |

---

## 4. 关联

- 上位机红线：`docs/host/README.md`
- 总体安全红线：`docs/plc/SAFETY.md`
- 通用协议与库速查：`docs/plc/hmi_scada_host.md`
- 双视角审查：`docs/review/automation_review.md`（第 3 节）
