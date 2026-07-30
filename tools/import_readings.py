# -*- coding: utf-8 -*-
"""Import course readings as page-faithful Markdown and mini-program JSON."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT.parent / "宋词小程序知识库" / "阅读材料"
SOURCE_DIR = ROOT / "data" / "readings_src"
SOURCE_IMAGE_DIR = SOURCE_DIR / "images"
JSON_DIR = ROOT / "miniprogram" / "data" / "readings"
PACKAGE_ROOT = ROOT / "miniprogram" / "packages"
BOOKS_PATH = ROOT / "miniprogram" / "data" / "books.json"
MANIFEST_PATH = SOURCE_DIR / "source-manifest.json"
MAX_PAGE_IMAGE_BYTES = 92_000
MIN_JPEG_QUALITY = 28


def cnki_search(title: str) -> str:
    return "https://kns.cnki.net/kns8s/defaultresult/index?kw=" + quote(title)


READINGS = (
    {
        "id": "reading-1",
        "filename_prefix": "“放情须远”与“用意愈深”",
        "title": "“放情须远”与“用意愈深”——潘阆《酒泉子》的两面",
        "author": "马里扬",
        "source": "《古典文学知识》2017 年第 2 期",
        "original_url": "https://m.pinshiwen.com/shishu/yanjiu/20191202254800.html",
        "source_label": "公开全文网页",
    },
    {
        "id": "reading-2",
        "filename_prefix": "彼岸的逍遥",
        "title": "彼岸的逍遥——略论宋初隐士词人潘阆",
        "author": "郑联",
        "source": "《名作欣赏》",
        "original_url": cnki_search("彼岸的逍遥 略论宋初隐士词人潘阆 郑联"),
        "source_label": "中国知网原文检索",
    },
    {
        "id": "reading-3",
        "filename_prefix": "采诗入律",
        "title": "采诗入律，别领风骚——“隐括词”撷英",
        "author": "孟庆洁、王书华",
        "source": "《语文知识》1997 年第 6 期",
        "original_url": "https://doi.org/10.13513/j.cnki.41-1041/h.1997.06.004",
        "source_label": "DOI 原文页",
    },
    {
        "id": "reading-4",
        "filename_prefix": "苏轼与黄庭坚",
        "title": "苏轼与黄庭坚",
        "author": "彭玉平",
        "source": "《名作欣赏》2023 年第 22 期",
        "original_url": cnki_search("苏轼与黄庭坚 彭玉平 名作欣赏 2023 22"),
        "source_label": "中国知网原文检索",
    },
)

WEBSITE = {
    "kind": "website",
    "title": "龙榆生先生纪念网站",
    "author": "",
    "source": "词学资料网站",
    "url": "https://longyusheng.org/",
}


def package_for_reading(reading_id: str) -> str:
    return "reading-a" if reading_id in {"reading-1", "reading-2"} else "reading-b"


def bundle_path(package: str) -> Path:
    return PACKAGE_ROOT / package / "data" / "readings.js"


def source_for(meta: dict) -> Path:
    matches = [
        path for path in KB_DIR.glob("*.pdf")
        if path.name.startswith(meta["filename_prefix"])
    ]
    if len(matches) != 1:
        raise RuntimeError(f"阅读材料匹配失败: {meta['id']} ({len(matches)} files)")
    return matches[0]


def compact_page(pixmap: fitz.Pixmap, destination: Path) -> None:
    source = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    source.thumbnail((1150, 1600), Image.Resampling.LANCZOS)
    quality = 82
    while True:
        buffer = io.BytesIO()
        source.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
        if buffer.tell() <= MAX_PAGE_IMAGE_BYTES or quality <= MIN_JPEG_QUALITY:
            destination.write_bytes(buffer.getvalue())
            return
        quality -= 5


def render_source(meta: dict, source: Path) -> tuple[list[str], str]:
    reading_id = meta["id"]
    directory = SOURCE_IMAGE_DIR / reading_id
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("page-*.jpg"):
        stale.unlink()

    document = fitz.open(source)
    names: list[str] = []
    for index, page in enumerate(document, 1):
        scale = 1600 / max(page.rect.width, page.rect.height)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        name = f"page-{index:02d}.jpg"
        compact_page(pixmap, directory / name)
        names.append(name)
    document.close()
    return names, hashlib.sha256(source.read_bytes()).hexdigest()


def write_markdown(meta: dict, page_names: list[str]) -> Path:
    lines = [
        "---",
        f"title: {meta['title']}",
        f"author: {meta['author']}",
        f"source: {meta['source']}",
        f"original_url: {meta['original_url']}",
        f"source_label: {meta['source_label']}",
        "verbatim: true",
        "---",
        "",
    ]
    for index, name in enumerate(page_names, 1):
        lines.extend([f"![原文第 {index} 页](images/{meta['id']}/{name})", ""])
    output = SOURCE_DIR / f"{meta['id']}.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def parse_frontmatter(markdown: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    text = markdown.read_text(encoding="utf-8").replace("\r\n", "\n")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise RuntimeError(f"front matter 无效: {markdown.name}")
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    images = re.findall(r"!\[([^]]*)\]\(([^)]+)\)", parts[2])
    if not images:
        raise RuntimeError(f"阅读稿没有原文页: {markdown.name}")
    return meta, images


def compile_markdown(markdown: Path) -> dict:
    meta, images = parse_frontmatter(markdown)
    reading_id = markdown.stem
    package = package_for_reading(reading_id)
    destination = PACKAGE_ROOT / package / "images" / reading_id
    destination.mkdir(parents=True, exist_ok=True)
    for stale in destination.glob("page-*.jpg"):
        stale.unlink()

    sections = []
    urls = []
    for alt, relative in images:
        source = (markdown.parent / relative).resolve()
        if not source.is_file() or SOURCE_DIR.resolve() not in source.parents:
            raise RuntimeError(f"阅读稿图片路径无效: {relative}")
        shutil.copy2(source, destination / source.name)
        url = f"/packages/{package}/images/{reading_id}/{source.name}"
        urls.append(url)
        sections.append({"type": "img", "url": url, "alt": alt})

    return {
        "id": reading_id,
        "title": meta["title"],
        "author": meta["author"],
        "summary": meta["source"],
        "kicker": "宋词导读 · 推荐阅读",
        "form_tag": "阅读",
        "collecting": False,
        "original_url": meta["original_url"],
        "source_label": meta["source_label"],
        "page_count": len(sections),
        "image_urls": urls,
        "sections": sections,
    }


def write_outputs(documents: dict[str, dict]) -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    for reading_id, document in documents.items():
        (JSON_DIR / f"{reading_id}.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    for package in ("reading-a", "reading-b"):
        selected = {
            reading_id: document
            for reading_id, document in documents.items()
            if package_for_reading(reading_id) == package
        }
        output = bundle_path(package)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "// Generated by tools/import_readings.py.\nmodule.exports = "
            + json.dumps(selected, ensure_ascii=False, indent=2)
            + ";\n",
            encoding="utf-8",
        )

    books = json.loads(BOOKS_PATH.read_text(encoding="utf-8"))
    books["readings"] = [
        {
            "id": meta["id"],
            "kind": "document",
            "title": meta["title"],
            "author": meta["author"],
            "source": meta["source"],
            "url": meta["original_url"],
        }
        for meta in READINGS
    ] + [WEBSITE]
    books["note"] = "阅读材料保留原页版式与出处。"
    BOOKS_PATH.write_text(json.dumps(books, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit(manifest: dict) -> None:
    documents = {}
    for package in ("reading-a", "reading-b"):
        source = bundle_path(package).read_text(encoding="utf-8")
        documents.update(json.loads(source.split("=", 1)[1].rsplit(";", 1)[0]))
    for meta in READINGS:
        source = source_for(meta)
        record = manifest.get(meta["id"], {})
        current_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if current_hash != record.get("source_sha256"):
            raise RuntimeError(f"阅读源文件已变化: {source.name}")
        document = documents.get(meta["id"], {})
        if document.get("page_count") != record.get("page_count"):
            raise RuntimeError(f"阅读页数不一致: {meta['id']}")
        for url in document.get("image_urls", []):
            if not (ROOT / "miniprogram" / url.lstrip("/")).is_file():
                raise RuntimeError(f"阅读页图缺失: {url}")
    print(f"[OK] {len(READINGS)} 篇阅读材料通过原页一致性审计")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if args.audit:
        audit(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
        return 0

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for meta in READINGS:
        source = source_for(meta)
        pages, source_hash = render_source(meta, source)
        write_markdown(meta, pages)
        manifest[meta["id"]] = {
            "source": str(source.relative_to(ROOT.parent)),
            "source_sha256": source_hash,
            "page_count": len(pages),
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    documents = {
        meta["id"]: compile_markdown(SOURCE_DIR / f"{meta['id']}.md")
        for meta in READINGS
    }
    write_outputs(documents)
    print(f"[OK] {len(documents)} 篇阅读材料已生成 Markdown 与 sections JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
