# -*- coding: utf-8 -*-
"""Import authorized works without rewriting the authors' text.

The knowledge-base directory is read-only input. Text-backed sources preserve every
non-whitespace character in source order. PDFs whose text cannot be extracted
reliably are rendered as page images instead of being transcribed or paraphrased.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageOps
import fitz


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KB_ROOT = REPO_ROOT.parent / "宋词小程序知识库"
MARKDOWN_DIR = REPO_ROOT / "data" / "works_src"
SOURCE_IMAGE_DIR = MARKDOWN_DIR / "images"
ARCHIVE_PATH = REPO_ROOT / "miniprogram" / "data" / "archive-all.json"
WORK_JSON_DIR = REPO_ROOT / "miniprogram" / "data" / "works"
MANIFEST_PATH = MARKDOWN_DIR / "source-manifest.json"

WECHAT_URLS = {
    "essay-13": "https://mp.weixin.qq.com/s/-oLUeBCHBSCwLDy_msfvjQ",
    "essay-14": "https://mp.weixin.qq.com/s/QY4wLcqbPPqZ4r_5Gk64SQ",
    "creative": "https://mp.weixin.qq.com/s/aD529aJjY1CZxAhm5NDnwQ",
}
WEB_TERMS = {"essay-13": "23Fall", "essay-14": "26Spring"}

SOURCE_SIZES = {
    "creative-1": 264223,
    "photo-1": 393220,
    "photo-2": 101710629,
    "photo-28": 101710629,
    "photo-3": 392698,
    "photo-4": 13359616,
    "photo-29": 13359616,
    "photo-5": 278634,
    "photo-6": 5057711,
    "photo-7": 459149,
    "photo-8": 1393567,
    "photo-9": 1750609,
    "photo-10": 504583,
    "photo-11": 534112,
    "photo-12": 2619381,
    "photo-13": 423344,
    "photo-14": 834900,
    "photo-15": 63532753,
    "photo-16": 285519,
    "photo-17": 483033,
    "photo-18": 118439,
    "photo-19": 1872208,
    "photo-20": 690252,
    "photo-21": 628815,
    "photo-22": 1840974,
    "photo-23": 534112,
    "photo-24": 534112,
    "photo-25": 834900,
    "photo-26": 63532753,
    "photo-27": 483033,
    "essay-1": 23403,
    "essay-2": 29709,
    "essay-3": 1211585,
    "essay-4": 18906,
    "essay-5": 300479,
    "essay-6": 16344,
    "essay-7": 260347,
    "essay-8": 149166,
    "essay-9": 20697,
    "essay-10": 193924,
    "essay-11": 291098,
    "essay-12": 237229,
}

PHOTO_MEDIA = {
    "photo-1": [("img-000.jpg", None), ("img-001.jpg", None)],
    "photo-2": [("img-000.png", None)],
    "photo-28": [("img-001.png", None)],
    "photo-3": [("img-000.jpg", None)],
    "photo-4": [("img-000.png", (0.0, 0.35, 1.0, 1.0))],
    "photo-29": [("img-002.png", (0.0, 0.0, 1.0, 0.64))],
    "photo-5": [("image1.jpeg", None), ("image2.jpeg", None)],
    "photo-6": [("image4.jpeg", None), ("image5.jpeg", None)],
    "photo-7": [("image1.jpeg", None)],
    "photo-8": [("img-007.jpg", None)],
    "photo-9": [("img-000.jpg", None)],
    "photo-10": [("img-000.jpg", None), ("img-001.jpg", None)],
    "photo-11": [("image1.jpeg", None)],
    "photo-12": [("img-012.jpg", None), ("img-018.jpg", None)],
    "photo-13": [("img-000.jpg", None)],
    "photo-14": [("img-002.jpg", None)],
    "photo-15": [("img-000.png", (0.0, 0.0, 0.5, 1.0))],
    "photo-16": [("img-002.jpg", None)],
    "photo-17": [("img-000.jpg", None)],
    "photo-18": [("image1.jpeg", None)],
    "photo-19": [("image1.jpeg", None), ("image2.jpeg", None)],
    "photo-20": [("image1.jpeg", None)],
    "photo-21": [("img-000.jpg", None)],
    "photo-22": [("__page1__.png", (0.15, 0.08, 0.85, 0.42))],
    "photo-23": [("image2.jpeg", None)],
    "photo-24": [("image4.jpeg", None)],
    "photo-25": [("img-010.jpg", None)],
    "photo-26": [("img-002.png", (0.0, 0.45, 1.0, 1.0))],
    "photo-27": [("img-001.jpg", None)],
}

# These layout-heavy sources need a human-checked Markdown transcript.
# Re-importing refreshes selected photos where present but preserves the curated manuscript.
CURATED_MARKDOWN_WORKS = {
    "creative-1", "creative-2", "creative-3",
    "essay-1", "essay-2", "essay-3", "essay-4", "essay-5", "essay-6",
    "essay-7", "essay-8", "essay-9", "essay-10", "essay-11", "essay-12",
    "essay-13", "essay-14",
    "photo-11", "photo-14", "photo-15", "photo-17",
    "photo-1", "photo-3", "photo-5", "photo-6", "photo-7", "photo-8",
    "photo-9", "photo-10", "photo-12", "photo-13", "photo-16", "photo-18",
    "photo-19", "photo-20", "photo-21", "photo-22", "photo-23",
    "photo-24", "photo-25", "photo-26", "photo-27", "photo-28",
    "photo-29", "photo-2", "photo-4",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def text_sha256(value: str) -> str:
    return sha256_bytes(canonical_text(value).encode("utf-8"))


def term_from_filename(path: Path) -> str:
    match = re.search(r"(20\d{2})(春|秋)", path.stem)
    if not match:
        raise RuntimeError(f"作品文件名缺少学期: {path.name}")
    season = "Spring" if match.group(2) == "春" else "Fall"
    return match.group(1)[2:] + season


def locate_sources(root: Path) -> dict[str, Path]:
    by_size: dict[int, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".pdf", ".docx", ".pptx"}:
            by_size.setdefault(path.stat().st_size, []).append(path)
    result: dict[str, Path] = {}
    for work_id, size in SOURCE_SIZES.items():
        matches = by_size.get(size, [])
        if len(matches) != 1:
            raise RuntimeError(
                f"知识库源文件匹配失败: work={work_id}, size={size}, matches={len(matches)}"
            )
        result[work_id] = matches[0]
    return result


def extract_ooxml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        if path.suffix.lower() == ".docx":
            names = ["word/document.xml"]
        else:
            names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda name: int(re.search(r"\d+", Path(name).stem).group()),
            )
        paragraphs: list[str] = []
        for name in names:
            root = ElementTree.fromstring(archive.read(name))
            for paragraph in root.iter():
                if paragraph.tag.endswith("}p"):
                    value = "".join(
                        node.text or "" for node in paragraph.iter() if node.tag.endswith("}t")
                    )
                    if value.strip():
                        paragraphs.append(value.strip())
        return "\n\n".join(paragraphs)


def extract_pdf_text(path: Path, temp: Path) -> str:
    output = temp / f"{path.stat().st_size}.txt"
    subprocess.run(
        ["pdftotext", "-layout", "-nopgbrk", str(path), str(output)],
        check=True,
        capture_output=True,
    )
    return output.read_text(encoding="utf-8", errors="replace")


def extract_text(path: Path, temp: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path, temp)
    return extract_ooxml_text(path)


def clear_generated_images(work_id: str) -> Path:
    directory = SOURCE_IMAGE_DIR / work_id
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()
    return directory


def extract_media(path: Path, filename: str, temp: Path) -> Path:
    destination = temp / f"{path.stat().st_size}-{filename}"
    if destination.exists():
        return destination
    if filename == "__page1__.png":
        prefix = destination.with_suffix("")
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-r", "180", "-png", str(path), str(prefix)],
            check=True,
            capture_output=True,
        )
        prefix.with_suffix(".png").replace(destination)
        return destination
    if path.suffix.lower() == ".pdf":
        media_dir = temp / f"media-{path.stat().st_size}"
        if not media_dir.exists():
            media_dir.mkdir(parents=True)
            subprocess.run(
                ["pdfimages", "-all", str(path), str(media_dir / "img")],
                check=True,
                capture_output=True,
            )
        source = media_dir / filename
        if not source.exists():
            raise RuntimeError(f"PDF 图片不存在: {filename} ({path.name})")
        shutil.copy2(source, destination)
        return destination
    with zipfile.ZipFile(path) as archive:
        prefix = "word/media/" if path.suffix.lower() == ".docx" else "ppt/media/"
        destination.write_bytes(archive.read(prefix + filename))
    return destination


def save_compact_image(
    source: Path,
    destination: Path,
    crop: tuple[float, float, float, float] | None = None,
    max_size: tuple[int, int] = (960, 960),
    max_bytes: int = 38_000,
) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        if crop:
            width, height = image.size
            box = tuple(
                int(value * (width if index % 2 == 0 else height))
                for index, value in enumerate(crop)
            )
            image = image.crop(box)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        quality = 78
        while True:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            if buffer.tell() <= max_bytes or quality <= 38:
                destination.write_bytes(buffer.getvalue())
                return
            quality -= 5


def render_pdf_pages(path: Path, work_id: str, temp: Path) -> list[str]:
    output_dir = clear_generated_images(work_id)
    render_dir = temp / f"pages-{work_id}"
    render_dir.mkdir(parents=True, exist_ok=True)
    pages: list[str] = []
    document = fitz.open(path)
    for index, page in enumerate(document, 1):
        scale = 1600 / max(page.rect.width, page.rect.height)
        source = render_dir / f"page-{index:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(source)
        name = f"page-{index:02d}.jpg"
        save_compact_image(source, output_dir / name, max_size=(1500, 2100), max_bytes=180_000)
        pages.append(name)
    document.close()
    if not pages:
        raise RuntimeError(f"PDF 页面渲染失败: {path.name}")
    return pages


def image_markdown(work_id: str, names: list[str]) -> str:
    return "\n\n".join(f"![](images/{work_id}/{name})" for name in names)


class FragmentTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "section", "div", "h1", "h2", "h3", "br", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def fetch(url: str, user_agent: str | None = None) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent or "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) MicroMessenger/8.0",
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def wechat_html(url: str) -> str:
    agents = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) MicroMessenger/8.0",
        "Mozilla/5.0 (WindowsWechat/4.0) Chrome/108 Safari/537.36",
    )
    for user_agent in agents:
        source = fetch(url, user_agent).decode("utf-8", errors="ignore")
        if 'id="js_content"' in source:
            return source
    raise RuntimeError(f"公众号正文未能加载: {url}")


def wechat_lines(source: str) -> list[str]:
    start = source.find('id="js_content"')
    end = source.find("<script", start)
    parser = FragmentTextParser()
    parser.feed(source[start:end])
    lines: list[str] = []
    for raw in html.unescape("".join(parser.parts)).replace("\xa0", " ").splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line and not line.startswith('id="js_content"'):
            lines.append(line)
    return lines


def wechat_image_urls(source: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"<img\b([^>]+)>", source, re.IGNORECASE):
        found = re.search(r'data-src="(https:[^"]+)"', match.group(1))
        if found:
            urls.append(html.unescape(found.group(1)))
    return urls


def build_web_sources() -> tuple[dict[str, str], dict[str, tuple[str, list[int]]]]:
    article1 = wechat_html(WECHAT_URLS["essay-13"])
    lines1 = wechat_lines(article1)
    start1 = next(index for index, line in enumerate(lines1) if line.startswith("最近，在上网冲浪"))
    end1 = next((index for index, line in enumerate(lines1) if line.startswith("文字：")), len(lines1))

    article2 = wechat_html(WECHAT_URLS["essay-14"])
    lines2 = wechat_lines(article2)
    start2 = next(index for index, line in enumerate(lines2) if line == "壹")
    end2 = next((index for index, line in enumerate(lines2) if line.startswith("供稿")), len(lines2))

    article3 = wechat_html(WECHAT_URLS["creative"])
    lines3 = wechat_lines(article3)
    one = lines3.index("《不醒人之梦》")
    two = lines3.index("《风雨人生》")
    end3 = next((index for index, line in enumerate(lines3) if line == "【END】"), len(lines3))

    bodies = {
        "essay-13": "\n".join(lines1[start1:end1]),
        "essay-14": "\n".join(lines2[start2:end2]),
        "creative-2": "\n".join(lines3[one:two]),
        "creative-3": "\n".join(lines3[two:end3]),
    }
    images = {
        "essay-13": (article1, [1, 15]),
        "essay-14": (article2, [4, 14, 22]),
        "creative-2": (article3, [10]),
        "creative-3": (article3, [19]),
    }
    return bodies, images


def front_matter(item: dict, original_url: str = "") -> str:
    fields = [
        "---",
        f"title: {item['title']}",
        f"form_tag: {item.get('form_tag', '')}",
        f"term: {item.get('term', '')}",
        "collecting: false",
        "verbatim: true",
    ]
    if original_url:
        fields.append(f"original_url: {original_url}")
    fields.extend(["---", ""])
    return "\n".join(fields)


def write_manuscript(
    work_id: str,
    item: dict,
    source_text: str,
    image_names: list[str] | None = None,
    original_url: str = "",
) -> None:
    parts: list[str] = []
    if image_names:
        parts.append(image_markdown(work_id, image_names))
    if source_text.strip():
        parts.append(source_text.replace("\r\n", "\n").replace("\r", "\n").strip("\n"))
    body = "\n\n".join(parts)
    (MARKDOWN_DIR / f"{work_id}.md").write_text(
        front_matter(item, original_url) + body + "\n",
        encoding="utf-8",
    )


def save_selected_images(work_id: str, source: Path, temp: Path) -> list[str]:
    output_dir = clear_generated_images(work_id)
    names: list[str] = []
    for index, (filename, crop) in enumerate(PHOTO_MEDIA.get(work_id, []), 1):
        extracted = extract_media(source, filename, temp)
        name = f"{index:02d}.jpg"
        save_compact_image(extracted, output_dir / name, crop)
        names.append(name)
    return names


def import_local_work(
    work_id: str,
    item: dict,
    source: Path,
    temp: Path,
) -> dict:
    if work_id in CURATED_MARKDOWN_WORKS:
        manuscript = MARKDOWN_DIR / f"{work_id}.md"
        if not manuscript.is_file():
            raise RuntimeError(f"缺少人工校订稿: {manuscript}")
        image_names = save_selected_images(work_id, source, temp)
        try:
            from .md_to_workjson import compile_markdown
        except ImportError:
            from md_to_workjson import compile_markdown
        document = compile_markdown(manuscript, copy_images=False)
        image_count = sum(section["type"] == "img" for section in document["sections"])
        if image_count != len(image_names):
            raise RuntimeError(
                f"人工校订稿图片数量不一致: work={work_id}, "
                f"markdown={image_count}, extracted={len(image_names)}"
            )
        curated_text = "".join(
            section.get("text", "")
            for section in document["sections"]
            if section["type"] != "img"
        )
        return {
            "mode": "curated_markdown",
            "source_sha256": sha256_bytes(source.read_bytes()),
            "text_sha256": text_sha256(curated_text),
            "text_characters": len(canonical_text(curated_text)),
            "image_count": len(image_names),
            "term": item.get("term", ""),
        }

    raw = extract_text(source, temp)
    use_pages = source.suffix.lower() == ".pdf" and (not raw.strip() or "�" in raw)
    if use_pages:
        page_names = render_pdf_pages(source, work_id, temp)
        write_manuscript(work_id, item, "", page_names)
        return {
            "mode": "page_images",
            "source_sha256": sha256_bytes(source.read_bytes()),
            "page_count": len(page_names),
            "term": item.get("term", ""),
        }

    images: list[str] = []
    if work_id.startswith("photo-"):
        images = save_selected_images(work_id, source, temp)
    elif work_id == "creative-1":
        output_dir = clear_generated_images(work_id)
        image = extract_media(source, "image1.jpg", temp)
        save_compact_image(image, output_dir / "01.jpg")
        images = ["01.jpg"]
    else:
        clear_generated_images(work_id)
    write_manuscript(work_id, item, raw, images)
    return {
        "mode": "source_text",
        "source_sha256": sha256_bytes(source.read_bytes()),
        "text_sha256": text_sha256(raw),
        "text_characters": len(canonical_text(raw)),
        "term": item.get("term", ""),
    }


def import_web_works(archive: dict[str, dict]) -> dict[str, dict]:
    bodies, image_sources = build_web_sources()
    url_for = {
        "essay-13": WECHAT_URLS["essay-13"],
        "essay-14": WECHAT_URLS["essay-14"],
        "creative-2": WECHAT_URLS["creative"],
        "creative-3": WECHAT_URLS["creative"],
    }
    result: dict[str, dict] = {}
    for work_id, body in bodies.items():
        if work_id in CURATED_MARKDOWN_WORKS:
            try:
                from .md_to_workjson import compile_markdown
            except ImportError:
                from md_to_workjson import compile_markdown
            document = compile_markdown(MARKDOWN_DIR / f"{work_id}.md", copy_images=False)
            current = "".join(
                section.get("text", "")
                for section in document["sections"]
                if section["type"] != "img"
            )
            result[work_id] = {
                "mode": "curated_markdown",
                "original_url": url_for[work_id],
                "text_sha256": text_sha256(current),
                "text_characters": len(canonical_text(current)),
                "image_count": sum(section["type"] == "img" for section in document["sections"]),
                "term": archive[work_id].get("term", ""),
            }
            continue
        article, indexes = image_sources[work_id]
        urls = wechat_image_urls(article)
        output_dir = clear_generated_images(work_id)
        image_names: list[str] = []
        for number, image_index in enumerate(indexes, 1):
            temporary = output_dir / f".{number:02d}.download"
            temporary.write_bytes(fetch(urls[image_index]))
            name = f"{number:02d}.jpg"
            save_compact_image(temporary, output_dir / name)
            temporary.unlink()
            image_names.append(name)
        write_manuscript(work_id, archive[work_id], body, image_names, url_for[work_id])
        result[work_id] = {
            "mode": "web_text",
            "original_url": url_for[work_id],
            "text_sha256": text_sha256(body),
            "text_characters": len(canonical_text(body)),
            "term": archive[work_id].get("term", ""),
        }
    return result


def synchronize_archive(sources: dict[str, Path]) -> tuple[dict, dict[str, dict]]:
    data = json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
    flat = {item["id"]: item for category in ("creative", "photo", "essay") for item in data[category]}
    for work_id, source in sources.items():
        if work_id != "creative-1":
            flat[work_id]["term"] = term_from_filename(source)
    for work_id, term in WEB_TERMS.items():
        flat[work_id]["term"] = term
    for item in flat.values():
        item["brief"] = ""
    ARCHIVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data, flat


def import_all(root: Path) -> None:
    sources = locate_sources(root)
    _, archive = synchronize_archive(sources)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="songci-faithful-") as raw_temp:
        temp = Path(raw_temp)
        for work_id, source in sources.items():
            manifest[work_id] = import_local_work(work_id, archive[work_id], source, temp)
        manifest.update(import_web_works(archive))
    MANIFEST_PATH.write_text(
        json.dumps({"version": 1, "works": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 已按原文重建 {len(manifest)} 篇稿件；知识库目录未写入")


def refresh_curated_manifest(root: Path) -> None:
    """Refresh checksums for reviewed Markdown without rebuilding any source files."""
    manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = manifest_data["works"]
    sources = locate_sources(root)
    try:
        from .md_to_workjson import compile_markdown
    except ImportError:
        from md_to_workjson import compile_markdown

    for work_id in sorted(CURATED_MARKDOWN_WORKS):
        document = compile_markdown(MARKDOWN_DIR / f"{work_id}.md", copy_images=False)
        current = "".join(
            section.get("text", "")
            for section in document["sections"]
            if section["type"] != "img"
        )
        record = {
            "mode": "curated_markdown",
            "text_sha256": text_sha256(current),
            "text_characters": len(canonical_text(current)),
            "image_count": sum(section["type"] == "img" for section in document["sections"]),
            "term": document.get("term", ""),
        }
        if work_id in sources:
            record = {
                "mode": record["mode"],
                "source_sha256": sha256_bytes(sources[work_id].read_bytes()),
                **{key: value for key, value in record.items() if key != "mode"},
            }
        elif document.get("original_url"):
            record = {
                "mode": record["mode"],
                "original_url": document["original_url"],
                **{key: value for key, value in record.items() if key != "mode"},
            }
        manifest[work_id] = record

    MANIFEST_PATH.write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 已刷新 {len(CURATED_MARKDOWN_WORKS)} 篇人工校订稿清单")


def compiled_text(work_id: str) -> str:
    document = json.loads((WORK_JSON_DIR / f"{work_id}.json").read_text(encoding="utf-8"))
    return "".join(
        section.get("text", "") for section in document["sections"] if section["type"] != "img"
    )


def audit(root: Path) -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["works"]
    sources = locate_sources(root)
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="songci-audit-") as raw_temp:
        temp = Path(raw_temp)
        web_bodies = {}
        if any(record["mode"] == "web_text" for record in manifest.values()):
            web_bodies, _ = build_web_sources()
        for work_id, record in manifest.items():
            if record["mode"] == "web_text":
                current = web_bodies[work_id]
                if text_sha256(current) != record["text_sha256"]:
                    failures.append(f"{work_id}: 公众号原文已变化")
            elif record["mode"] == "curated_markdown":
                if "source_sha256" in record:
                    source = sources[work_id]
                    if sha256_bytes(source.read_bytes()) != record["source_sha256"]:
                        failures.append(f"{work_id}: 知识库源文件已变化")
                try:
                    from .md_to_workjson import compile_markdown
                except ImportError:
                    from md_to_workjson import compile_markdown
                document = compile_markdown(
                    MARKDOWN_DIR / f"{work_id}.md",
                    copy_images=False,
                )
                current = "".join(
                    section.get("text", "")
                    for section in document["sections"]
                    if section["type"] != "img"
                )
                if text_sha256(current) != record["text_sha256"]:
                    failures.append(f"{work_id}: 人工校订稿与清单不一致")
                count = sum(section["type"] == "img" for section in document["sections"])
                if count != record["image_count"]:
                    failures.append(f"{work_id}: 人工校订稿图片数量不一致")
            else:
                source = sources[work_id]
                if sha256_bytes(source.read_bytes()) != record["source_sha256"]:
                    failures.append(f"{work_id}: 知识库源文件已变化")
                if record["mode"] == "source_text":
                    raw = extract_text(source, temp)
                    if text_sha256(raw) != record["text_sha256"]:
                        failures.append(f"{work_id}: 源文提取结果不一致")
            if record["mode"] in {"source_text", "web_text", "curated_markdown"}:
                if text_sha256(compiled_text(work_id)) != record["text_sha256"]:
                    failures.append(f"{work_id}: 小程序正文与原文不一致")
            else:
                document = json.loads((WORK_JSON_DIR / f"{work_id}.json").read_text(encoding="utf-8"))
                count = sum(section["type"] == "img" for section in document["sections"])
                if count != record["page_count"]:
                    failures.append(f"{work_id}: 原页图片数量不一致")
    if failures:
        for failure in failures:
            print("[FAIL] " + failure)
        return 1
    print(f"[OK] {len(manifest)} 篇作品通过原文一致性审计")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base", type=Path, default=DEFAULT_KB_ROOT)
    parser.add_argument("--audit", action="store_true", help="核对源文件、稿源与生成 JSON")
    parser.add_argument(
        "--refresh-curated",
        action="store_true",
        help="只刷新人工校订稿的清单，不覆盖 Markdown 或图片",
    )
    args = parser.parse_args()
    root = args.knowledge_base.resolve()
    if not root.is_dir():
        raise SystemExit(f"知识库目录不存在: {root}")
    if args.audit:
        return audit(root)
    if args.refresh_curated:
        refresh_curated_manifest(root)
        return 0
    import_all(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
