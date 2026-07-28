# 作品内容工作流

小程序不在运行时解析 Markdown。这里的 `.md` 是可维护的写作源文件，
`tools/md_to_workjson.py` 会把它们编译为详情页原生支持的 `sections` JSON。

完整链路：

```text
知识库 PDF / DOCX / PPTX / 公众号
  -> data/works_src/<id>.md
  -> miniprogram/data/works/<id>.json
  -> work-detail 原生渲染
```

当前已收录 39 篇：`creative-1..3`、`photo-1..22`、`essay-1..14`。

## 日常改稿

作品文件名必须与 `archive-all.json` 的 `id` 一致，例如 `essay-2.md`。

```markdown
---
title: 作品标题
form_tag: 文字
term: 2026春
collecting: false
summary: 卡片摘要
---

# 小标题

## 次级标题

正文以空行分段。

> 连续引用第一行
> 连续引用第二行

*拍摄信息：南京 · 手机拍摄*

![图片说明](images/essay-2/01.jpg)
```

支持的正文结构编译为 `h / p / quote / note / img`。`#`、`##`、`###` 分别对应三级正文标题；
整行 `*斜体*` 会渲染为小号附注，适合拍摄时间、地点、设备和参考信息。这是刻意限制的稳定子集，
能避免在小程序中引入 Markdown 运行时和额外包体。

图片放在 `data/works_src/images/<id>/`。编译器会复制到
`miniprogram/images/works/<id>/` 并改写为小程序本地路径；缺图、目录穿越、HTTP 图片都会使校验失败。

## 编译与校验

```powershell
# 只校验 Markdown、元数据与图片
python tools/md_to_workjson.py data/works_src --check

# 生成全部 JSON 并复制本地图片
python tools/md_to_workjson.py data/works_src

# 调试单篇，只打印结果
python tools/md_to_workjson.py data/works_src/essay-2.md --demo
```

生成 JSON 还包含 `reading_minutes` 与 `image_urls`，供详情页显示阅读时长和打开图片预览。

## 从知识库重新导入

仅在原始知识库更新时运行：

```powershell
python tools/import_knowledgebase.py
python tools/md_to_workjson.py data/works_src
```

导入器按文件指纹定位当前知识库导出，提取 PDF/DOCX/PPTX 正文与图片，压缩本地配图，
并对学生姓名、学号、院系署名做脱敏。公众号偶尔会返回验证页；已有成功导入稿件时，脚本会保留本地版本并提示警告。

两份扫描/双栏作业采用人工校订文本，定义在 `SCANNED_TEXT` 中，避免重新导入时退化为乱码或错栏。

## 内容红线

- Markdown 与生成 JSON 中不得出现学生姓名、学号、班级或院系署名。
- 不写入 IMA 临时签名图、HTTP 图片或本机绝对路径。
- 原文链接只作为来源信息；正文与必要配图必须在小程序内完整可读。
- 改稿后始终先跑 `--check`，再覆盖 JSON。
