# -*- coding: utf-8 -*-
"""Import the course knowledge base into privacy-safe Markdown manuscripts.

The source folder is expected next to this repository. Source files are located
by their byte size so personal names do not need to be recorded in this script.
The generated Markdown is the editable source of truth; run md_to_workjson.py
afterward to compile the mini-program data files.
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import subprocess
import tempfile
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from PIL import Image, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KB_ROOT = REPO_ROOT.parent / "宋词小程序知识库"
MARKDOWN_DIR = REPO_ROOT / "data" / "works_src"
SOURCE_IMAGE_DIR = MARKDOWN_DIR / "images"
ARCHIVE_PATH = REPO_ROOT / "miniprogram" / "data" / "archive-all.json"

WECHAT_URLS = {
    "essay-13": "https://mp.weixin.qq.com/s/-oLUeBCHBSCwLDy_msfvjQ",
    "essay-14": "https://mp.weixin.qq.com/s/QY4wLcqbPPqZ4r_5Gk64SQ",
    "creative": "https://mp.weixin.qq.com/s/aD529aJjY1CZxAhm5NDnwQ",
}

# Byte sizes are stable identifiers for this exact knowledge-base export.
SOURCE_SIZES = {
    2: 264223,
    3: 63532753,
    4: 834900,
    5: 459149,
    6: 423344,
    7: 504583,
    8: 534112,
    9: 392698,
    10: 2619381,
    11: 1750609,
    12: 1393567,
    13: 101710629,
    14: 393220,
    17: 628815,
    18: 1840974,
    19: 690252,
    20: 118439,
    21: 285519,
    22: 483033,
    23: 1872208,
    24: 13359616,
    25: 278634,
    26: 5057711,
    27: 23403,
    28: 260347,
    29: 237229,
    30: 18906,
    31: 20697,
    32: 1211585,
    33: 29709,
    34: 300479,
    35: 291098,
    36: 193924,
    37: 149166,
    38: 16344,
}

ESSAY_SOURCES = {
    "essay-1": 27,
    "essay-2": 33,
    "essay-3": 32,
    "essay-4": 30,
    "essay-5": 34,
    "essay-6": 38,
    "essay-7": 28,
    "essay-8": 37,
    "essay-9": 31,
    "essay-10": 36,
    "essay-11": 35,
    "essay-12": 29,
}

PHOTO_SOURCES = {
    "photo-1": 14,
    "photo-2": 13,
    "photo-3": 9,
    "photo-4": 24,
    "photo-5": 25,
    "photo-6": 26,
    "photo-7": 5,
    "photo-8": 12,
    "photo-9": 11,
    "photo-10": 7,
    "photo-11": 8,
    "photo-12": 10,
    "photo-13": 6,
    "photo-14": 4,
    "photo-15": 3,
    "photo-16": 21,
    "photo-17": 22,
    "photo-18": 20,
    "photo-19": 23,
    "photo-20": 19,
    "photo-21": 17,
    "photo-22": 18,
}

# (source index, extracted media filename, caption, optional fractional crop)
PHOTO_IMAGES = {
    "photo-1": [(14, "img-000.jpg", "落花浮水", None), (14, "img-001.jpg", "锦鲤环游", None)],
    "photo-2": [(13, "img-000.png", "世纪公园春日花枝", None)],
    "photo-3": [(9, "img-000.jpg", "乌镇水穷处的戏台", None)],
    "photo-4": [(24, "img-000.png", "清平乐·村居", None)],
    "photo-5": [(25, "image1.jpeg", "校园水池秋夜", None), (25, "image2.jpeg", "故乡凉亭秋夜", None)],
    "photo-6": [(26, "image4.jpeg", "严冬富春江", None), (26, "image5.jpeg", "桐庐山水", None)],
    "photo-7": [(5, "image1.jpeg", "洱海雨后晚霞", None)],
    "photo-8": [(12, "img-007.jpg", "远山长，云山乱，晓山青", None)],
    "photo-9": [(11, "img-000.jpg", "龙华寺回廊", None)],
    "photo-10": [(7, "img-000.jpg", "生日前夜的书桌", None), (7, "img-001.jpg", "冬日疏枝", None)],
    "photo-11": [(8, "image1.jpeg", "昔日相聚", None), (8, "image2.jpeg", "今日同行", None)],
    "photo-12": [(10, "img-012.jpg", "窗边秋光", None), (10, "img-018.jpg", "橘树秋色", None)],
    "photo-13": [(6, "img-000.jpg", "明孝陵神道", None)],
    "photo-14": [(4, "img-002.jpg", "中秋夜的云间明月", None)],
    "photo-15": [(3, "img-000.png", "西湖孤山远眺", (0.0, 0.0, 0.54, 1.0))],
    "photo-16": [(21, "img-002.jpg", "花枝间掠过的飞机", None)],
    "photo-17": [(22, "img-000.jpg", "落日熔金，暮云合璧", None)],
    "photo-18": [(20, "image1.jpeg", "雨夜灯影", None)],
    "photo-19": [(23, "image1.jpeg", "花坛春色", None), (23, "image2.jpeg", "留春一瞬", None)],
    "photo-20": [(19, "image1.jpeg", "一塔间月", None)],
    "photo-21": [(17, "img-000.jpg", "云间满月", None)],
    "photo-22": [(18, "__page1__.png", "咖啡馆窗外的夕照", (0.15, 0.08, 0.85, 0.42))],
}

PHOTO_END_MARKERS = {
    "photo-11": "第二首",
    "photo-14": "黄州定慧院寓居作",
    "photo-17": "孤馆",
}

SCANNED_TEXT = {
    "photo-1": """# 词与影

> 酒罢歌馀兴未阑，小桥清水共盘桓。
> 波摇梅蕊当心白，风入罗衣贴体寒。
> 且莫思归去，须尽笙歌此夕欢。
> ——冯延巳《抛球乐·酒罢歌馀兴未阑》

# 随笔

两张照片摄于南京老山珍珠泉边。阴雨绵绵的春日，一朵海棠落在水中，寒风吹来，花影在清流里漂转；不远处的锦鲤又荡开水波，给寂静的池面添了一点生机。

清明时节，阴雨、寒风、落花与春暮叠在一起，容易让人想到沉重的往事。但儿童的笑声穿过树林，水中的鱼也打破了低沉的画面。生活总会在最细小的地方重新给人希望，正如词中由伤春转向“且莫思归去，须尽笙歌此夕欢”。

“波摇梅蕊当心白”尤其令人难忘。有人以为水波摇动的是树上梅花的倒影，但眼前所见也说明，花瓣聚在波心时，落花本身同样可以成为被水摇动的景物。词中的伤春与照片中的落花因此真正相接。""",
    "photo-2": """# 词与影

> 把酒祝东风，且共从容。垂杨紫陌洛城东。
> 总是当年携手处，游遍芳丛。
> 聚散苦匆匆，此恨无穷。今年花胜去年红。
> 可惜明年花更好，知与谁同？
> ——欧阳修《浪淘沙·把酒祝东风》

# 随笔

在相册中重看世纪公园踏青的照片、寻找配词时，一时很难把这些春景同某一种固定情感相连。那个周末暂别任务与期限，公园里的人用各自的方式享受春天，让人想起琅琊山中或歌于途、或休于树的众人，以及醉在其间的庐陵太守。

《唐宋词十七讲》说欧阳修词中有一种“遣玩的兴味”。《浪淘沙》的“从容”，正好概括了踏青时的心情；“今年花胜去年红”，又写出对自然与春光的欣喜。然而赏春之外，聚散之恨仍然存在。春花也许年年更好，与春天、与同行之人的相聚却总是匆匆。

因此，这张照片所留下的并不只是花色。它也像一次郑重的告别：知道春光会去，仍愿在此刻举杯，且共从容。""",
    "photo-4": """# 词与影

> 茅檐低小，溪上青青草。醉里吴音相媚好，白发谁家翁媪？
> 大儿锄豆溪东，中儿正织鸡笼。最喜小儿亡赖，溪头卧剥莲蓬。
> ——辛弃疾《清平乐·村居》

# 随笔

这张照片拍摄于一次乡村社会实践。那是笔者第一次真正深入乡村、深入自然：湛蓝的天、闪烁的星、朴素的乡音，以及在小路上微笑着相互招呼的人们，都让照片中的“村居”有了切身的温度。

“村居”之所以成为“村居”，关键还在一个“居”字。短暂经过只能看见风景，长一些的停留才会真正融入生活。实践的日子并不算久，却让人感到一种平淡、长久而温和的快乐。这也是笔者从《清平乐·村居》中读到的快乐。""",
    "photo-15": """# 词与影

> 但远山长，云山乱，晓山青。
> ——苏轼《行香子·过七里濑》

# 随笔

从熙宁六年到今天，如果说有什么是不变的，那便是青山。

高考结束后来到西湖孤山，眼前是绵延的远山，云水一色，乱云重叠，近处山树青翠，绿意盎然。远山似乎没有边界，像山水画里的墨色落于尘寰，慢慢漫漶开去。

云并不像山一样不变，而是瞬息万变的。二者相照，正像苏轼在词里写的：“盖将自其变者而观之，则天地曾不能以一瞬；自其不变者而观之，则物与我皆无尽也。”山树一寸寸生长，自然在此，人心在此；只有将心放平，才能享受当下景色。

“君臣一梦，今古空名。”如今再看，只有“远山长，云山乱，晓山青”。宽阔的不只是青山绿水，更是那一片心。""",
}


def load_archive() -> dict[str, dict]:
    archive = json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for key in ("creative", "photo", "essay") for item in archive[key]}


def locate_sources(root: Path) -> dict[int, Path]:
    by_size: dict[int, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".pdf", ".docx", ".pptx"}:
            by_size.setdefault(path.stat().st_size, []).append(path)
    result = {}
    for index, size in SOURCE_SIZES.items():
        candidates = by_size.get(size, [])
        if len(candidates) != 1:
            raise RuntimeError(f"知识库源文件匹配失败: index={index}, size={size}, matches={len(candidates)}")
        result[index] = candidates[0]
    return result


def collect_private_names(root: Path) -> set[str]:
    names: set[str] = set()
    ignored = {"公众号", "优秀案例", "拍照配词", "期末习作", "批改版", "一些上科大", "宋词导读"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        stem = re.sub(r"20\d{7,}", " ", path.stem)
        for token in re.findall(r"(?:(?<=^)|(?<=[\s_\-]))([\u4e00-\u9fff]{2,4})(?=$|[\s_\-])", stem):
            if token not in ignored:
                names.add(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", stem) and stem not in ignored:
            names.add(stem)
    return names


def extract_ooxml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        if path.suffix.lower() == ".docx":
            names = ["word/document.xml"]
        else:
            names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda name: int(re.search(r"\d+", Path(name).stem).group()),
            )
        paragraphs = []
        for name in names:
            root = ElementTree.fromstring(archive.read(name))
            for paragraph in root.iter():
                if not paragraph.tag.endswith("}p"):
                    continue
                text = "".join(node.text or "" for node in paragraph.iter() if node.tag.endswith("}t"))
                if text.strip():
                    paragraphs.append(text.strip())
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
    return extract_pdf_text(path, temp) if path.suffix.lower() == ".pdf" else extract_ooxml_text(path)


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
        rendered = prefix.with_suffix(".png")
        if rendered != destination:
            rendered.replace(destination)
        return destination
    if path.suffix.lower() == ".pdf":
        media_dir = temp / f"media-{path.stat().st_size}"
        marker = media_dir / ".done"
        if not marker.exists():
            media_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(["pdfimages", "-all", str(path), str(media_dir / "img")], check=True, capture_output=True)
            marker.touch()
        source = media_dir / filename
        if not source.exists():
            raise RuntimeError(f"PDF 图片不存在: {filename} ({path.name})")
        destination.write_bytes(source.read_bytes())
        return destination
    with zipfile.ZipFile(path) as archive:
        prefix = "word/media/" if path.suffix.lower() == ".docx" else "ppt/media/"
        member = prefix + filename
        destination.write_bytes(archive.read(member))
    return destination


def save_compact_image(
    source: Path,
    destination: Path,
    crop: tuple[float, float, float, float] | None = None,
) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        if crop:
            width, height = image.size
            image = image.crop(tuple(int(value * (width if i % 2 == 0 else height)) for i, value in enumerate(crop)))
        image.thumbnail((960, 960), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        quality = 76
        while True:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            if buffer.tell() <= 38000:
                destination.write_bytes(buffer.getvalue())
                break
            if quality > 36:
                quality -= 5
                continue
            width, height = image.size
            if min(width, height) <= 420:
                destination.write_bytes(buffer.getvalue())
                break
            image = image.resize((int(width * 0.86), int(height * 0.86)), Image.Resampling.LANCZOS)
            quality = 56


def redact(text: str, private_names: Iterable[str]) -> str:
    text = text.replace("\u3000", " ").replace("\ufeff", "")
    text = re.sub(r"style\.visibility", "", text)
    text = re.sub(r"(?m)^\s*(?:left\d+|0\d{5})", "", text)
    text = re.sub(r"(?<!\d)20\d{8,11}(?!\d)", "", text)
    for name in sorted(private_names, key=len, reverse=True):
        text = text.replace(name + "同学", "作者").replace(name, "作者")
    text = re.sub(r"(?m)^\s*(?:填词|文字|作者|姓名)\s*[：:].*$", "", text)
    text = re.sub(r"(?m)^.*(?:学院|本科生).*级.*$", "", text)
    text = re.sub(r"(?m)^\s*(?:供稿|编排|审校)\s*[|｜].*$", "", text)
    text = re.sub(r"(?m)^.*�.*$", "", text)
    return text


def join_wrapped(lines: list[str]) -> str:
    result = ""
    for line in lines:
        if result and re.search(r"[A-Za-z0-9]$", result) and re.match(r"[A-Za-z0-9]", line):
            result += " "
        result += line
    return result.strip()


def text_to_markdown(raw: str, title: str, private_names: set[str]) -> str:
    raw = redact(raw, private_names).replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\n[ \t]*\n", "\n\n", raw)
    blocks = []
    for raw_block in re.split(r"\n{2,}", raw):
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw_block.splitlines()]
        lines = [line for line in lines if line and line not in {title, "---"}]
        deduped = []
        for line in lines:
            if not deduped or line != deduped[-1]:
                deduped.append(line)
        if not deduped:
            continue
        joined = join_wrapped(deduped)
        if not joined or joined in {title, "作者", "拍照配词", "配词：", "配词:", "END", "【END】"}:
            continue
        looks_heading = (
            len(joined) <= 28
            and len(deduped) == 1
            and not re.search(r"[。！？；：]$", joined)
            and bool(re.match(r"^(?:[一二三四五六七八九十]+[、.]|[（(]?[一二三四五六七八九十\d]+[）).、]|参考文献|引言|结语|创作手记|教师评语|赏析)", joined))
        )
        looks_quote = (
            len(deduped) >= 2
            and len(joined) <= 420
            and max(map(len, deduped)) <= 55
            and any(mark in joined for mark in ("——", "---", "《", "兮", "也"))
        )
        if looks_heading:
            blocks.append("# " + joined)
        elif looks_quote:
            blocks.append("\n".join("> " + line for line in deduped))
        else:
            sentences = re.split(r"(?<=[。！？；])", joined)
            chunk = ""
            for sentence in sentences:
                if chunk and len(chunk) + len(sentence) > 560:
                    blocks.append(chunk)
                    chunk = ""
                chunk += sentence
            if chunk:
                blocks.append(chunk)
    return "\n\n".join(blocks).strip()


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
    lines = []
    for raw in html.unescape("".join(parser.parts)).replace("\xa0", " ").splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line and not line.startswith('id="js_content"') and (not lines or line != lines[-1]):
            lines.append(line)
    return lines


def wechat_image_urls(source: str) -> list[str]:
    urls = []
    for match in re.finditer(r"<img\b([^>]+)>", source, re.IGNORECASE):
        found = re.search(r'data-src="(https:[^"]+)"', match.group(1))
        if found:
            urls.append(html.unescape(found.group(1)))
    return urls


def lines_to_markdown(lines: list[str], private_names: set[str]) -> str:
    blocks = []
    heading_words = {
        "写在前面", "创作手记", "填词说明", "教师评语", "缘起｜姑苏印记", "读词｜荷风习习",
        "游园｜移步换景", "感受", "参考文献", "闹红一舸", "菰雨生凉轩", "水香榭", "眠云亭",
        "感知", "决策", "体验生活", "享受生活", "奇思妙想", "偶尔哲理",
    }
    for line in lines:
        line = redact(line, private_names).strip()
        if not line or line in {"作者", "上下滑动阅览", "【END】", "END", "*配合音乐食用更佳"}:
            continue
        if line in heading_words or re.fullmatch(r"[壹贰叁肆伍陆柒捌玖拾]|0?[1-9]|[一二三四五六七八九十]{1,3}", line):
            blocks.append("# " + line)
        elif line.startswith("---") or ("《" in line and len(line) < 90 and any(c in line for c in ("——", "---"))):
            blocks.append("> " + line)
        else:
            blocks.append(line)
    return "\n\n".join(blocks)


def front_matter(item: dict, original_url: str = "") -> str:
    fields = [
        "---",
        f"title: {item['title']}",
        f"form_tag: {item.get('form_tag', '')}",
        f"term: {item.get('term', '')}",
        "collecting: false",
        f"summary: {item.get('brief', '')}",
    ]
    if original_url:
        fields.append(f"original_url: {original_url}")
    fields.extend(["---", ""])
    return "\n".join(fields)


def write_manuscript(work_id: str, item: dict, body: str, original_url: str = "") -> None:
    content = front_matter(item, original_url) + body.strip() + "\n"
    (MARKDOWN_DIR / f"{work_id}.md").write_text(content, encoding="utf-8")


def image_markdown(work_id: str, images: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"![{caption}](images/{work_id}/{filename})" for filename, caption in images)


def import_photo(
    work_id: str,
    item: dict,
    source: Path,
    sources: dict[int, Path],
    private_names: set[str],
    temp: Path,
) -> None:
    saved = []
    for number, (source_index, filename, caption, crop) in enumerate(PHOTO_IMAGES[work_id], 1):
        extracted = extract_media(sources[source_index], filename, temp)
        output_name = f"{number:02d}.jpg"
        save_compact_image(extracted, SOURCE_IMAGE_DIR / work_id / output_name, crop)
        saved.append((output_name, caption))
    images = "# 镜头\n\n" + image_markdown(work_id, saved)

    if work_id in SCANNED_TEXT:
        body = SCANNED_TEXT[work_id]
        marker = "# 随笔"
        body = body.replace(marker, images + "\n\n" + marker, 1)
    else:
        raw = extract_text(source, temp)
        marker = PHOTO_END_MARKERS.get(work_id)
        if marker and marker in raw:
            raw = raw[: raw.find(marker)]
        prose = text_to_markdown(raw, item["title"], private_names)
        body = images + "\n\n# 词笺\n\n" + prose
    write_manuscript(work_id, item, body)


def save_web_image(url: str, work_id: str, number: int, caption: str) -> tuple[str, str]:
    raw = fetch(url)
    temporary = SOURCE_IMAGE_DIR / work_id / f".{number:02d}.download"
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(raw)
    name = f"{number:02d}.jpg"
    save_compact_image(temporary, SOURCE_IMAGE_DIR / work_id / name)
    temporary.unlink()
    return name, caption


def import_wechat(archive: dict[str, dict], private_names: set[str]) -> None:
    article1 = wechat_html(WECHAT_URLS["essay-13"])
    lines1 = wechat_lines(article1)
    start1 = next(i for i, line in enumerate(lines1) if line.startswith("最近，在上网冲浪"))
    end1 = next((i for i, line in enumerate(lines1) if line.startswith("文字：")), len(lines1))
    body1 = lines_to_markdown(lines1[start1:end1], private_names)
    urls1 = wechat_image_urls(article1)
    images1 = [
        save_web_image(urls1[1], "essay-13", 1, "东坡人格侧写"),
        save_web_image(urls1[15], "essay-13", 2, "东坡与人间烟火"),
    ]
    body1 = "# 图引\n\n" + image_markdown("essay-13", images1) + "\n\n" + body1
    write_manuscript("essay-13", archive["essay-13"], body1, WECHAT_URLS["essay-13"])

    article2 = wechat_html(WECHAT_URLS["essay-14"])
    lines2 = wechat_lines(article2)
    for index in range(len(lines2) - 2):
        if lines2[index : index + 3] == ["念", "奴", "娇"]:
            lines2[index : index + 3] = ["念奴娇"]
            break
    start2 = next(i for i, line in enumerate(lines2) if line == "壹")
    end2 = next((i for i, line in enumerate(lines2) if line.startswith("供稿")), len(lines2))
    body2 = lines_to_markdown(lines2[start2:end2], private_names)
    urls2 = wechat_image_urls(article2)
    images2 = [
        save_web_image(urls2[4], "essay-14", 1, "退思园荷花"),
        save_web_image(urls2[14], "essay-14", 2, "闹红一舸"),
        save_web_image(urls2[22], "essay-14", 3, "菰雨生凉轩"),
    ]
    body2 = "# 园中词境\n\n" + image_markdown("essay-14", images2) + "\n\n" + body2
    write_manuscript("essay-14", archive["essay-14"], body2, WECHAT_URLS["essay-14"])

    article3 = wechat_html(WECHAT_URLS["creative"])
    lines3 = wechat_lines(article3)
    one = lines3.index("《不醒人之梦》")
    two = lines3.index("《风雨人生》")
    end3 = next((i for i, line in enumerate(lines3) if line == "【END】"), len(lines3))
    urls3 = wechat_image_urls(article3)
    for work_id, lines, image_index, caption in (
        ("creative-2", lines3[one : two - 1] if lines3[two - 1] == "2" else lines3[one:two], 10, "梦中寻词"),
        ("creative-3", lines3[two:end3], 19, "风雨人生"),
    ):
        image = save_web_image(urls3[image_index], work_id, 1, caption)
        body = "# 作品图引\n\n" + image_markdown(work_id, [image]) + "\n\n" + lines_to_markdown(lines, private_names)
        write_manuscript(work_id, archive[work_id], body, WECHAT_URLS["creative"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base", type=Path, default=DEFAULT_KB_ROOT)
    args = parser.parse_args()
    root = args.knowledge_base.resolve()
    if not root.is_dir():
        raise SystemExit(f"知识库目录不存在: {root}")

    archive = load_archive()
    sources = locate_sources(root)
    private_names = collect_private_names(root)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="songci-import-") as raw_temp:
        temp = Path(raw_temp)
        for work_id, source_index in ESSAY_SOURCES.items():
            raw = extract_text(sources[source_index], temp)
            body = text_to_markdown(raw, archive[work_id]["title"], private_names)
            write_manuscript(work_id, archive[work_id], body)

        raw = extract_text(sources[2], temp)
        creative_body = "# 展示稿\n\n" + text_to_markdown(raw, archive["creative-1"]["title"], private_names)
        cover_source = extract_media(sources[2], "image1.jpg", temp)
        save_compact_image(cover_source, SOURCE_IMAGE_DIR / "creative-1" / "01.jpg")
        creative_body = "# 图引\n\n![古韵新声展示](images/creative-1/01.jpg)\n\n" + creative_body
        write_manuscript("creative-1", archive["creative-1"], creative_body)

        for work_id, source_index in PHOTO_SOURCES.items():
            import_photo(work_id, archive[work_id], sources[source_index], sources, private_names, temp)

        try:
            import_wechat(archive, private_names)
        except RuntimeError:
            web_ids = {"creative-2", "creative-3", "essay-13", "essay-14"}
            if not all((MARKDOWN_DIR / f"{work_id}.md").is_file() for work_id in web_ids):
                raise
            print("[WARN] 公众号返回验证页，已保留上一次成功导入的本地稿件")

    expected = {f"creative-{i}" for i in range(1, 4)} | {f"essay-{i}" for i in range(1, 15)} | {f"photo-{i}" for i in range(1, 23)}
    generated = {path.stem for path in MARKDOWN_DIR.glob("*.md") if not path.name.startswith("_") and path.name != "README.md"}
    if generated != expected:
        raise RuntimeError(f"作品集合不完整: missing={sorted(expected - generated)}, extra={sorted(generated - expected)}")
    print(f"[OK] 已生成 {len(generated)} 篇 Markdown，图片位于 {SOURCE_IMAGE_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
