#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app/webui.py — 本地离线工控助手 · 内置 Web 聊天界面（纯标准库，零新增依赖）

为什么用标准库：本工程核心依赖已含 chromadb；Web 界面若再引 Flask 会增加安装体积与失败面。
这里用 http.server 实现一个轻量服务，直接对接：
  - Ollama /api/chat（推理）
  - Chroma RAG（复用 scripts/rag_manager.py 的客户端与配置）

设计原则（对应"本机不装任何东西"的运维约束）：
  - 不安装任何包；仅用 Python 标准库 + 已装的 chromadb。
  - RAG 不可用时优雅降级：聊天仍可用，只是没有知识库上下文。
  - Ollama 不可用时返回清晰报错，而不是崩溃。

运行：
  python app/webui.py                 # 默认 127.0.0.1:8500
  python app/webui.py --port 9000     # 指定端口
  python app/webui.py --host 0.0.0.0  # 允许局域网访问（仅在你信任的网络下）
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# 中文输出防乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
ASSISTANT_PORT = int(os.environ.get("ASSISTANT_PORT", "8500"))
ASSISTANT_HOST = os.environ.get("ASSISTANT_HOST", "127.0.0.1")

SYSTEM_PROMPT = (
    "你是本地离线运行的「工控软件应用辅助助手」，服务于 PLC 编程、变频器/伺服调试、"
    "触摸屏(HMI)/组态软件、编码器、上位机程序与自动控制软件写程序等场景。\n"
    "规则：\n"
    "1) 仅作为起草与查错参考，输出代码/配置/参数后必须提示用户经合格工程师审核 + 仿真验证，"
    "绝不能直接下装到现场设备。\n"
    "2) 涉及联锁、急停、限位、过载等安全回路，明确提醒用户由硬接线/安全继电器兜底，"
    "软件互锁不可替代硬急停。\n"
    "3) 不照搬示例的 PID 参数/电子齿轮比/阈值，提醒按实际对象整定。\n"
    "4) 若提供了知识库上下文，优先依据上下文作答并标注来源文件；上下文不足时如实说明，可建议补充文档到知识库。\n"
    "5) 回答用中文，工程术语可中英混用。"
)


# ----------------------------------------------------------------------------
# RAG（最佳努力；失败则降级为无上下文）
# ----------------------------------------------------------------------------
def _rag_module():
    try:
        import scripts.rag_manager as rm  # noqa
        return rm
    except Exception:
        return None


def rag_context(query: str, top_k: int = 4):
    """返回 [(source, text), ...]；任何异常（缺集合/嵌入下载失败/未配置）返回空列表。"""
    rm = _rag_module()
    if rm is None:
        return []
    try:
        cfg = rm.load_config()
        client = rm.get_client(cfg)
        ef = rm.get_embedding_fn(cfg)
        collection = client.get_collection(name=cfg["chroma"]["collection"], embedding_function=ef)
        if collection.count() == 0:
            return []
        res = collection.query(query_texts=[query], n_results=top_k,
                               include=["documents", "metadatas"])
        out = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        for d, m in zip(docs, metas):
            src = (m or {}).get("source", "?")
            out.append((src, (d or "").strip()))
        return out
    except Exception:
        # 嵌入模型未下载/无网络、集合不存在等：降级
        return []


def _rag_config_safe():
    """纯标准库读取 rag.config.json，不触碰 chromadb；失败返回 None。"""
    try:
        raw = (ROOT / "config/rag.config.json").read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return None


def rag_available() -> bool:
    # 关键：先只用标准库做文件系统短路，避免每次 health 都冷加载 chromadb（初始化约 4s）。
    # 仅当向量库目录确实存在“真实内容”时，才 import rag_manager → chromadb。
    cfg = _rag_config_safe()
    if cfg is None:
        return False
    try:
        persist = ROOT / cfg["chroma"]["persist_dir"]
        if not persist.exists():
            return False
        real = [p for p in persist.iterdir()
                if p.name not in (".gitkeep",) and not p.name.startswith(".")]
        if not real:
            return False
    except Exception:
        return False
    # 到此说明磁盘上真有向量数据，才值得付出 chromadb 的导入成本
    rm = _rag_module()
    if rm is None:
        return False
    try:
        client = rm.get_client(cfg)
        ef = rm.get_embedding_fn(cfg)
        col = client.get_collection(name=cfg["chroma"]["collection"], embedding_function=ef)
        return col.count() > 0
    except Exception:
        return False


# ----------------------------------------------------------------------------
# Ollama 调用
# ----------------------------------------------------------------------------
def ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def ollama_health():
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/version", timeout=3) as r:
            return json.loads(r.read().decode("utf-8")).get("version")
    except Exception:
        return None


# 健康检查用的并发探测 + 短缓存：避免 Ollama 未运行时顺序 3s+3s 超时拖垮前端轮询
_HEALTH_TTL = 3.0
_health_cache = {"ts": 0.0, "data": None}


def _ollama_probe():
    """并发探测 Ollama 版本与模型列表，超时 1.5s；失败返回 (None, [])。"""
    ver = [None]
    models = [[]]

    def _ver():
        try:
            with urllib.request.urlopen(f"{OLLAMA_BASE}/api/version", timeout=1.5) as r:
                ver[0] = json.loads(r.read().decode("utf-8")).get("version")
        except Exception:
            ver[0] = None

    def _tags():
        try:
            with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=1.5) as r:
                d = json.loads(r.read().decode("utf-8"))
                models[0] = [m.get("name", "") for m in d.get("models", [])]
        except Exception:
            models[0] = []

    a = threading.Thread(target=_ver, daemon=True)
    b = threading.Thread(target=_tags, daemon=True)
    a.start(); b.start(); a.join(); b.join()
    return ver[0], models[0]


def default_model():
    # 取 ollama-models.txt 第一个未注释的模型名
    p = ROOT / "config/ollama-models.txt"
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            t = line.strip()
            if not t or t.startswith("#"):
                continue
            return t.split("#")[0].strip()
    except Exception:
        pass
    return "qwen2.5:14b"


def ollama_chat(model: str, messages: list, timeout: int = 120):
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("message", {}).get("content", "")


# ----------------------------------------------------------------------------
# HTTP 处理
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_html(INDEX_HTML)
        elif self.path == "/api/health":
            now = time.time()
            if _health_cache["data"] is not None and now - _health_cache["ts"] < _HEALTH_TTL:
                self._send_json(_health_cache["data"])
                return
            ver, models = _ollama_probe()
            data = {
                "ollama": ver is not None,
                "ollama_version": ver,
                "rag": rag_available(),
                "models": models,
                "default_model": default_model(),
            }
            _health_cache["data"] = data
            _health_cache["ts"] = now
            self._send_json(data)
        elif self.path == "/api/models":
            _, models = _ollama_probe()
            self._send_json({"models": models, "default_model": default_model()})
        else:
            self._send_json({"error": "not found"}, code=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"error": "bad json"}, code=400)
            return
        if self.path == "/api/chat":
            self._handle_chat(payload)
        elif self.path == "/api/search":
            self._handle_search(payload)
        else:
            self._send_json({"error": "not found"}, code=404)

    def _handle_chat(self, payload):
        message = (payload.get("message") or "").strip()
        history = payload.get("history") or []
        model = payload.get("model") or default_model()
        use_rag = bool(payload.get("rag", True))
        if not message:
            self._send_json({"error": "empty message"}, code=400)
            return
        if not ollama_health():
            self._send_json({
                "error": "Ollama 未运行或未安装。请先安装 Ollama 并启动（详见 README 使用指南），"
                         "再重试。", "reply": None, "sources": [], "rag_used": False,
            }, code=200)
            return
        context = []
        if use_rag:
            context = rag_context(message, top_k=4)
        sys_prompt = SYSTEM_PROMPT
        if context:
            ctx_text = "\n\n".join(f"[来源 {s}]\n{t}" for s, t in context)
            sys_prompt += f"\n\n===== 知识库上下文（仅作参考，需工程师核实）=====\n{ctx_text}\n====="
        messages = [{"role": "system", "content": sys_prompt}]
        for h in history[-20:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                messages.append({"role": h["role"], "content": str(h.get("content", ""))})
        messages.append({"role": "user", "content": message})
        try:
            reply = ollama_chat(model, messages, timeout=180)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300] if hasattr(e, "read") else ""
            self._send_json({"error": f"Ollama 调用失败（模型可能未拉取？）: {detail}",
                             "reply": None, "sources": [], "rag_used": bool(context)},
                            code=200)
            return
        except Exception as e:
            self._send_json({"error": f"Ollama 调用异常: {e}",
                             "reply": None, "sources": [], "rag_used": bool(context)},
                            code=200)
            return
        self._send_json({
            "reply": reply,
            "sources": [s for s, _ in context],
            "rag_used": bool(context),
            "model": model,
        })

    def _handle_search(self, payload):
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k", 5))
        if not query:
            self._send_json({"error": "empty query"}, code=400)
            return
        results = rag_context(query, top_k=top_k)
        self._send_json({"query": query, "results": [
            {"source": s, "text": t} for s, t in results
        ], "count": len(results)})

    def log_message(self, fmt, *args):
        # 简化日志，避免刷屏
        sys.stderr.write("[webui] " + (fmt % args) + "\n")


# ----------------------------------------------------------------------------
# 内嵌前端（单文件，零静态资源）
# ----------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>本地离线工控助手</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
         background:#0f1115; color:#e6e6e6; height:100vh; display:flex; flex-direction:column; }
  header { padding:10px 16px; background:#161b22; border-bottom:1px solid #30363d; }
  header h1 { font-size:16px; margin:0 0 4px; }
  header .sub { font-size:12px; color:#9aa4b2; }
  .bar { display:flex; gap:8px; align-items:center; padding:8px 16px; background:#11161d;
         border-bottom:1px solid #30363d; flex-wrap:wrap; }
  .bar label { font-size:12px; color:#9aa4b2; }
  select, button, input[type=text] { background:#21262d; color:#e6e6e6; border:1px solid #30363d;
         border-radius:6px; padding:6px 10px; font-size:13px; }
  button { cursor:pointer; }
  button:hover { background:#2d333b; }
  #status { font-size:12px; margin-left:auto; color:#9aa4b2; }
  #msgs { flex:1; overflow:auto; padding:16px; display:flex; flex-direction:column; gap:10px; }
  .msg { max-width:80%; padding:10px 12px; border-radius:10px; line-height:1.5; white-space:pre-wrap; word-break:break-word; }
  .user { align-self:flex-end; background:#1f6feb; color:#fff; }
  .bot { align-self:flex-start; background:#21262d; border:1px solid #30363d; }
  .src { font-size:11px; color:#7d8590; margin-top:6px; }
  .warn { font-size:12px; color:#e3b341; }
  .err { font-size:12px; color:#f85149; }
  .input { display:flex; gap:8px; padding:12px 16px; border-top:1px solid #30363d; background:#11161d; }
  .input textarea { flex:1; resize:none; height:48px; background:#21262d; color:#e6e6e6;
         border:1px solid #30363d; border-radius:6px; padding:10px; font-size:14px; }
</style>
</head>
<body>
<header>
  <h1>本地离线工控助手</h1>
  <div class="sub">Ollama 本地推理 + Chroma 知识库 · 数据不出本机 · ⚠️ 仅辅助起草，输出须经工程师审核与仿真验证后方可下装</div>
</header>
<div class="bar">
  <label>模型</label>
  <select id="model"><option>加载中...</option></select>
  <label><input type="checkbox" id="rag" checked> 启用知识库(RAG)</label>
  <span id="status">连接中...</span>
</div>
<div id="msgs"></div>
<div class="input">
  <textarea id="text" placeholder="输入工控问题，例如：三菱 FX5U 通过 Modbus TCP 读 D100，地址怎么填？"></textarea>
  <button id="send">发送</button>
</div>
<script>
const $ = s => document.querySelector(s);
let history = [];
async function health(){
  try{
    const r = await fetch('/api/health'); const j = await r.json();
    let txt = j.ollama ? ('Ollama ✓ '+j.ollama_version) : 'Ollama ✗ 未运行';
    txt += j.rag ? ' · 知识库 ✓' : ' · 知识库 ✗(未导入)';
    $('#status').textContent = txt;
    const sel = $('#model'); sel.innerHTML='';
    (j.models.length?j.models:[j.default_model]).forEach(m=>{
      const o=document.createElement('option'); o.value=m; o.textContent=m; sel.appendChild(o);
    });
    if(!j.ollama) $('#status').innerHTML='<span class="err">Ollama 未运行：请先安装并启动 Ollama</span>';
  }catch(e){ $('#status').innerHTML='<span class="err">无法连接服务</span>'; }
}
function addMsg(role, text, src){
  const d=document.createElement('div'); d.className='msg '+(role==='user'?'user':'bot');
  d.textContent=text;
  if(src&&src.length){ const s=document.createElement('div'); s.className='src'; s.textContent='来源: '+src.join(', '); d.appendChild(s); }
  $('#msgs').appendChild(d); $('#msgs').scrollTop=$('#msgs').scrollHeight;
}
async function send(){
  const text=$('#text').value.trim(); if(!text) return;
  addMsg('user', text); history.push({role:'user',content:text}); $('#text').value='';
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text,history,model:$('#model').value,rag:$('#rag').checked})});
    const j=await r.json();
    if(j.error && !j.reply){ addMsg('bot', j.error, null); $('#status').innerHTML='<span class="err">'+j.error+'</span>'; return; }
    addMsg('bot', j.reply||'(无回复)', j.sources||[]);
    if(j.reply) history.push({role:'assistant',content:j.reply});
  }catch(e){ addMsg('bot', '请求失败: '+e, null); }
}
$('#send').onclick=send;
$('#text').addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); send(); } });
health(); setInterval(health, 15000);
</script>
</body>
</html>"""


def main():
    global ASSISTANT_HOST, ASSISTANT_PORT
    ap = argparse.ArgumentParser(description="本地离线工控助手 Web 界面（标准库）")
    ap.add_argument("--host", default=ASSISTANT_HOST)
    ap.add_argument("--port", type=int, default=ASSISTANT_PORT)
    args = ap.parse_args()

    ASSISTANT_HOST, ASSISTANT_PORT = args.host, args.port

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"===== 本地离线工控助手 Web 界面 =====")
    print(f"访问: {url}  （本机浏览器打开）")
    print(f"Ollama: {OLLAMA_BASE}   知识库目录见 config/rag.config.json")
    print(f"RAG 当前可用: {rag_available()}  |  默认模型: {default_model()}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
