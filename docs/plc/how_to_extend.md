# 如何给本地助手"增加应用场景"

> 你提的三个诉求，本质是同一件事：**这个本地助手要能随你的现场不断成长**。
> - "PLC 我还要增加一个品牌" → 新增品牌资料，AI 就能按它自动部署
> - "某个电器件我经常使用，要增加使用方法" → 新增器件文档，AI 就能答用法
> - "组态要覆盖全网使用率前 5" → 已内置，见 `docs/scada/`
>
> **不需要改任何代码**：加文档 → `add-all` → 提问验证。三分钟搞定。

## 一、总流程（所有场景通用）

```
① 写文档（用模板填空）
      ↓
② python scripts\rag_manager.py add-all     # 一键入库（幂等，可反复跑）
      ↓
③ python scripts\rag_manager.py scan        # 确认没漏入库
      ↓
④ python scripts\rag_manager.py search "..."  # 验证能检索到
      ↓
⑤ 提问验证：问 AI 一个只有你文档里才有的细节，看它答不答得对
```

## 二、场景 A：新增一个 PLC 品牌

**目标**：让 AI 能针对这个品牌自动产出 ST 程序、点表、通信配置。

1. 复制 `docs/plc/brand_onboarding_template.md` 的模板，保存为
   `docs/plc/brands/<品牌名>.md`（如 `docs/plc/brands/xinje.md`）。
2. 重点填三节：**第 3 节寄存器映射表**、**第 4 节常用操作**、**第 9 节我方惯用做法**。
3. 可选：在 `docs/plc/brands.md` 的对照表里加一行（让人和 AI 都知道这个品牌已覆盖）。
4. `add-all` → `scan` → 提问验证。

**提问验证示例**：

```
按我新增的 <品牌> 资料，写一段 ST 程序：用 Modbus TCP 读 D100~D109，
转成 REAL 后做超限报警，报警时置位 M200。所有地址按我文档的映射表，
不确定的地方明确说"需核对"，不要自行推断。
```

## 三、场景 B：新增一个常用电气件的使用方法

**目标**：AI 能准确回答"这个器件怎么用、怎么接线、故障码什么意思"。

1. 复制模板，保存为 `docs/devices/<器件名>.md`
   （如 `docs/devices/汇川_MD290_变频器.md`、`docs/devices/西门子_V90_伺服.md`）。
2. 重点填：**第 3 节映射表**、**第 4 节操作方法**、**第 6 节故障代码表**、**第 7 节接线**。
3. 有官方手册 PDF 的话，把 PDF 放进 `data/knowledge_base/docs/<器件名>/`（`pypdf` 会解析文本）。
4. `add-all` → `scan` → 提问验证。

**提问验证示例**：

```
<器件型号> 的 <故障码> 是什么意思？怎么处理？接线时要注意什么？
```

## 四、场景 C：新增上位机 / 组态样例

| 类型 | 放哪 | 要点 |
|---|---|---|
| 上位机源码（C#/Python/LabVIEW） | `docs/host/<项目名>.md` | 贴核心代码 + **寄存器分配表** + 通信参数 + 异常处理思路 |
| 组态样例工程说明 | `docs/scada/<项目名>.md` | 变量点表 + 设备配置 + 脚本 + 画面清单 |
| 自己的调试笔记 / 踩坑记录 | `docs/devices/` 或 `docs/plc/` | **这段最值钱**，AI 会优先参考 |

> **必须脱敏**：去掉真实 IP、账号、密码、工艺机密、涉密图纸。
> `data/knowledge_base/docs/` 与 `docs/devices/` 等目录下的文件会被提交到 Git，
> **不要把不能公开的内容放进去**（或加进 `.gitignore`）。

## 五、新建了一个目录怎么办

`add-all` 只导入 `config/rag.config.json` 里 `knowledge_dirs` 列出的目录。
新建目录后加一行即可：

```json
"knowledge_dirs": [
  "data/knowledge_base/docs",
  "docs/plc",
  "docs/scada",
  "docs/host",
  "docs/devices",
  "docs/deploy",
  "docs/我的新目录"
]
```

## 六、常用命令速查

```powershell
python scripts\rag_manager.py add-all                  # 一键导入所有知识目录
python scripts\rag_manager.py scan                     # 看哪些文件还没入库
python scripts\rag_manager.py scan -a                  # 同时看已入库的
python scripts\rag_manager.py add <路径> -r            # 只导某个目录/文件
python scripts\rag_manager.py search "关键词" --top-k 8 # 检索验证
python scripts\rag_manager.py list                     # 已导入的源文件清单
python scripts\rag_manager.py stats                    # 集合统计
```

> 文档改了内容再跑一次 `add-all` 即可，脚本用 upsert，不会产生重复块。

## 七、FAQ

**Q：add-all 报 `The read operation timed out in upsert`？**
A：嵌入模型权重没下完（首次要联网下约 80MB）。解法见 `rag_guide.md` 第 4.1 节。

**Q：scan 显示"未入库"，但刚跑过 add-all？**
A：看文件后缀是否在 `supported_ext`（默认 `.md/.txt/.pdf`）；或该目录不在 `knowledge_dirs` 里。

**Q：改了 `provider`（嵌入模型）后要重建库吗？**
A：要。不同嵌入模型的向量不兼容，`clear` 后重新 `add-all`。

**Q：PDF 解析出来是乱码/空？**
A：扫描版 PDF 没有文本层，需要 OCR 后另存为文本；表格型 PDF 提取效果通常较差，建议手工整理成 md。

**Q：AI 还是答错地址？**
A：把你手册里的**原始截图文字**也贴进文档（越接近原文，检索命中越准），并在提示词里强调"按我文档第 3 节，不确定就说需核对"。

## 八、关联

- 填空模板：[brand_onboarding_template.md](brand_onboarding_template.md)
- 知识库总览：[rag_guide.md](rag_guide.md)
- 组态 TOP5 能力：[../scada/README.md](../scada/README.md)
- 安全红线：[SAFETY.md](SAFETY.md)
