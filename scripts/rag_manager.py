#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_manager.py — local-offline-assistant RAG 知识库管理脚本

子命令：
  add <path> [--recursive]   导入文件或目录到 Chroma 向量库（幂等：同内容不重复入库）
  search <query> [--top-k N] 语义检索
  list                       列出已导入的源文件
  stats                      查看集合统计
  clear [--yes]              清空向量库集合（高危，默认需交互确认）

依赖：chromadb（PDF 支持另需 pypdf）
运行环境：Python 3.10+，在工程根目录或任意目录执行均可（自动定位工程根）
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Windows 中文输出防乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent  # 工程根目录
CONFIG_PATH = ROOT / "config" / "rag.config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[FAIL] 配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_client(cfg: dict):
    """创建 Chroma 持久化客户端"""
    try:
        import chromadb
    except ImportError:
        print("[FAIL] 未安装 chromadb。请先在工程 venv 中执行: pip install -r requirements.txt")
        sys.exit(1)
    persist_dir = ROOT / cfg["chroma"]["persist_dir"]
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def get_embedding_fn(cfg: dict):
    """按配置返回嵌入函数；chroma-default 时返回 None（使用 Chroma 内置默认嵌入）"""
    provider = cfg.get("embedding", {}).get("provider", "chroma-default")
    if provider == "chroma-default":
        return None
    if provider == "ollama":
        try:
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
            return OllamaEmbeddingFunction(
                url="http://127.0.0.1:11434/api/embeddings",
                model_name=cfg["embedding"].get("ollama_model", "nomic-embed-text"),
            )
        except Exception as e:
            print(f"[WARN] Ollama 嵌入函数加载失败（{e}），回退到 Chroma 默认嵌入")
            return None
    print(f"[WARN] 未知 embedding provider: {provider}，回退到 Chroma 默认嵌入")
    return None


def read_text_file(path: Path) -> str:
    """读取文本内容，支持 md/txt/pdf"""
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            print(f"[WARN] 跳过 PDF（未安装 pypdf）: {path}")
            return ""
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return ""


def chunk_text(text: str, size: int, overlap: int) -> list:
    """固定长度分块，带重叠"""
    text = text.strip()
    if not text:
        return []
    if size <= overlap:
        raise ValueError("chunk size 必须大于 overlap")
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def cmd_add(args, cfg):
    target = Path(args.path)
    if not target.is_absolute():
        target = ROOT / target
    if not target.exists():
        print(f"[FAIL] 路径不存在: {target}")
        sys.exit(1)

    files = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = "**/*" if args.recursive else "*"
        for p in sorted(target.glob(pattern)):
            if p.is_file() and p.suffix.lower() in [e.lower() for e in cfg["supported_ext"]]:
                files.append(p)
    if not files:
        print("[WARN] 未找到可导入的文件（检查 supported_ext 与 --recursive）")
        return

    client = get_client(cfg)
    ef = get_embedding_fn(cfg)
    collection = client.get_or_create_collection(
        name=cfg["chroma"]["collection"], embedding_function=ef
    )

    size = cfg["chunk"]["size"]
    overlap = cfg["chunk"]["overlap"]
    added, skipped, failed = 0, 0, 0

    for fp in files:
        try:
            text = read_text_file(fp)
            chunks = chunk_text(text, size, overlap)
            if not chunks:
                skipped += 1
                print(f"[SKIP] 空内容: {fp.name}")
                continue
            rel = str(fp.relative_to(ROOT)) if fp.is_relative_to(ROOT) else str(fp)
            ids, docs, metas = [], [], []
            for i, c in enumerate(chunks):
                # 幂等键：文件路径 + 块序号 + 内容哈希，重复导入走 upsert 不产生重复
                h = hashlib.md5(c.encode("utf-8")).hexdigest()[:8]
                ids.append(f"{rel}::{i}::{h}")
                docs.append(c)
                metas.append({"source": rel, "chunk": i})
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            added += len(chunks)
            print(f"[OK] {fp.name}: {len(chunks)} 块")
        except Exception as e:
            failed += 1
            print(f"[ERR] {fp.name}: {e}")

    total = collection.count()
    print(f"\n完成：新增/更新 {added} 块，跳过 {skipped} 个文件，失败 {failed} 个。集合当前共 {total} 块。")


def cmd_search(args, cfg):
    client = get_client(cfg)
    ef = get_embedding_fn(cfg)
    try:
        collection = client.get_collection(name=cfg["chroma"]["collection"], embedding_function=ef)
    except Exception:
        print("[FAIL] 向量库为空或集合不存在，请先执行 add 导入文档")
        sys.exit(1)
    if collection.count() == 0:
        print("[FAIL] 集合为空，请先执行 add 导入文档")
        sys.exit(1)
    res = collection.query(query_texts=[args.query], n_results=args.top_k)
    print(f"查询: {args.query}\n")
    for i, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), 1
    ):
        print(f"--- 结果 {i} | 来源: {meta.get('source')} | 块 {meta.get('chunk')} | 距离 {dist:.4f} ---")
        print(doc[:300].replace("\n", " ") + ("..." if len(doc) > 300 else ""))
        print()


def cmd_list(args, cfg):
    client = get_client(cfg)
    try:
        collection = client.get_collection(name=cfg["chroma"]["collection"])
    except Exception:
        print("集合不存在（尚未导入任何文档）")
        return
    data = collection.get(include=["metadatas"])
    sources = sorted({m.get("source", "?") for m in data["metadatas"]})
    print(f"已导入源文件 {len(sources)} 个：")
    for s in sources:
        print(f"  - {s}")


def cmd_stats(args, cfg):
    client = get_client(cfg)
    ef = get_embedding_fn(cfg)
    try:
        collection = client.get_collection(name=cfg["chroma"]["collection"], embedding_function=ef)
        count = collection.count()
    except Exception:
        count = 0
    print(f"集合名称 : {cfg['chroma']['collection']}")
    print(f"数据目录 : {ROOT / cfg['chroma']['persist_dir']}")
    print(f"嵌入方式 : {cfg['embedding']['provider']}")
    print(f"块总数   : {count}")


def cmd_clear(args, cfg):
    if not args.yes:
        ans = input("高危操作：将删除整个向量库集合，输入 yes 确认: ")
        if ans.strip().lower() != "yes":
            print("已取消。")
            return
    client = get_client(cfg)
    try:
        client.delete_collection(name=cfg["chroma"]["collection"])
        print(f"集合 {cfg['chroma']['collection']} 已删除。")
    except Exception as e:
        print(f"集合不存在或删除失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="local-offline-assistant RAG 知识库管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="导入文件或目录")
    p_add.add_argument("path", help="文件或目录路径（相对路径基于工程根目录）")
    p_add.add_argument("--recursive", "-r", action="store_true", help="目录递归导入")

    p_search = sub.add_parser("search", help="语义检索")
    p_search.add_argument("query", help="查询文本")
    p_search.add_argument("--top-k", type=int, default=5)

    sub.add_parser("list", help="列出已导入源文件")
    sub.add_parser("stats", help="集合统计")
    p_clear = sub.add_parser("clear", help="清空集合（高危）")
    p_clear.add_argument("--yes", action="store_true", help="跳过交互确认")

    args = parser.parse_args()
    cfg = load_config()
    {"add": cmd_add, "search": cmd_search, "list": cmd_list,
     "stats": cmd_stats, "clear": cmd_clear}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
