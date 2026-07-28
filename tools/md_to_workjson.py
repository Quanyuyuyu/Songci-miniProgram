# -*- coding: utf-8 -*-
"""
markdown -> 小程序作品 sections JSON 转换器
============================================
把每个作品用熟悉的 markdown 写稿，转换为 work-detail 页能直接渲染的 JSON。

输出 schema（与 work-detail.wxml 完全对齐）:
  {
    "title": "...",
    "form_tag": "文字|摄影|创作",
    "term": "2026春",
    "collecting": false,
    "sections": [
      {"type":"h",     "text":"..."},
      {"type":"p",     "text":"..."},
      {"type":"quote", "text":"..."},
      {"type":"img",   "url":"...", "alt":"..."}
    ]
  }

图片处理（闭环关键）:
  - http(s) 链接: 原样保留（生产环境必须是 HTTPS 且在小程序后台 downloadFile 合法域名白名单内）
  - 本地相对路径（如 images/works/essay-2-1.jpg）: 自动拷贝到 miniprogram/images/works/，
    并改写为小程序本地路径 /images/works/<文件名>，无需联网即可显示
  - IMA 带时效签名的图片链接【不推荐】直接写死，会因过期而失效

用法:
  python tools/md_to_workjson.py data/works_src            # 批量转换目录下所有 .md（跳过 README/_ 开头）
  python tools/md_to_workjson.py data/works_src/essay-2.md # 转换单个文件
  python tools/md_to_workjson.py --demo data/works_src/_example.md  # 仅打印结果，不写文件/不拷图

依赖: 仅 Python 标准库
"""
import os
import re
import sys
import json
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # songci-miniprogram/
IMG_DEST = os.path.join(REPO_ROOT, "miniprogram", "images", "works")
OUT_DIR_DEFAULT = os.path.join(REPO_ROOT, "miniprogram", "data", "works")

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEAD_RE = re.compile(r"^#{1,6}\s+(.*)$")
QUOTE_RE = re.compile(r"^>\s?")
BLOCKQUOTE_INLINE_RE = re.compile(r"^>\s?(.*)$")


def parse_front_matter(text):
    """解析顶部的 --- ... --- 区块，返回 (meta dict, body string)。"""
    meta = {"title": "", "form_tag": "", "term": "", "collecting": False}
    if not text.startswith("---"):
        return meta, text
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return meta, text
    end = None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            end = i
            break
    if end is None:
        return meta, text
    for line in parts[1:end]:
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k == "title":
            meta["title"] = v
        elif k == "form_tag":
            meta["form_tag"] = v
        elif k == "term":
            meta["term"] = v
        elif k == "collecting":
            meta["collecting"] = v.lower() in ("true", "1", "yes")
    body = "\n".join(parts[end + 1:])
    return meta, body


def resolve_image(alt, url, src_dir):
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return {"type": "img", "url": url, "alt": alt}
    # 本地相对路径
    src = os.path.normpath(os.path.join(src_dir, url))
    if os.path.exists(src):
        os.makedirs(IMG_DEST, exist_ok=True)
        base = os.path.basename(url)
        shutil.copy(src, os.path.join(IMG_DEST, base))
        return {"type": "img", "url": "/images/works/" + base, "alt": alt}
    print("  [WARN] 图片源文件不存在，保留原相对路径（小程序内将加载失败）: %s" % url)
    return {"type": "img", "url": url, "alt": alt}


def parse_body(body, src_dir):
    sections = []
    para_buf = []
    quote_buf = []

    def flush_para():
        if para_buf:
            t = "\n".join(para_buf).strip()
            if t:
                sections.append({"type": "p", "text": t})
            para_buf.clear()

    def flush_quote():
        if quote_buf:
            t = "\n".join(quote_buf).strip()
            if t:
                sections.append({"type": "quote", "text": t})
            quote_buf.clear()

    for raw in body.split("\n"):
        stripped = raw.strip()
        if not stripped:
            flush_para()
            flush_quote()
            continue
        hm = HEAD_RE.match(stripped)
        if hm:
            flush_para()
            flush_quote()
            sections.append({"type": "h", "text": hm.group(1).strip()})
            continue
        if QUOTE_RE.match(stripped):
            flush_para()
            quote_buf.append(BLOCKQUOTE_INLINE_RE.match(stripped).group(1))
            continue
        if "![" in stripped:
            flush_para()
            flush_quote()
            parts = re.split(r"(!\[[^\]]*\]\([^)]+\))", stripped)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                im = IMG_RE.match(part)
                if im:
                    sections.append(resolve_image(im.group(1), im.group(2), src_dir))
                else:
                    sections.append({"type": "p", "text": part})
            continue
        flush_quote()
        para_buf.append(stripped)

    flush_para()
    flush_quote()
    return sections


def convert_file(md_path, out_dir, demo=False):
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    meta, body = parse_front_matter(text)
    if not meta["title"]:
        print("[SKIP] 缺少 title 前置信息: %s" % md_path)
        return None
    src_dir = os.path.dirname(os.path.abspath(md_path))
    sections = parse_body(body, src_dir)
    doc = {
        "title": meta["title"],
        "form_tag": meta["form_tag"],
        "term": meta["term"],
        "collecting": bool(meta["collecting"]),
        "sections": sections,
    }
    stem = os.path.splitext(os.path.basename(md_path))[0]
    if demo:
        print("=== %s.json (demo) ===" % stem)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return doc
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("[OK] %s -> %s  (sections=%d)" % (stem + ".md", out_path, len(sections)))
    return doc


def is_skippable(name):
    base = os.path.basename(name)
    return base.upper() == "README.md" or base.startswith("_")


def main():
    args = sys.argv[1:]
    demo = False
    if "--demo" in args:
        demo = True
        args.remove("--demo")
    if not args:
        print(__doc__)
        return
    target = args[0]
    out_dir = OUT_DIR_DEFAULT
    if os.path.isdir(target):
        files = sorted(
            f for f in os.listdir(target)
            if f.endswith(".md") and not is_skippable(f)
        )
        if not files:
            print("目录内无可转换的 .md 文件: %s" % target)
            return
        for f in files:
            convert_file(os.path.join(target, f), out_dir, demo)
    else:
        convert_file(target, out_dir, demo)


if __name__ == "__main__":
    main()
