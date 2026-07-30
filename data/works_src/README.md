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

当前已收录 46 篇：`creative-1..3`、`photo-1..29`、`essay-1..14`。

## 日常维护

作品文件名必须与 `archive-all.json` 的 `id` 一致，例如 `essay-2.md`。

```markdown
---
title: 作品标题
form_tag: 文字
byline: 作者署名
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

手写稿支持的正文结构编译为 `h / p / quote / note / img`。`#`、`##`、`###` 分别对应三级正文标题；
整行 `*斜体*` 会渲染为小号附注，适合拍摄时间、地点、设备和参考信息。这是刻意限制的稳定子集，
能避免在小程序中引入 Markdown 运行时和额外包体。

图片放在 `data/works_src/images/<id>/`。编译器会按作品类型复制到
`miniprogram/packages/work-*/images/<id>/` 并改写为小程序分包路径；缺图、目录穿越、HTTP 图片都会使校验失败。

## 编译与校验

```powershell
# 只校验 Markdown、元数据与图片
python tools/md_to_workjson.py data/works_src --check

# 生成全部 JSON 并复制本地图片
python tools/md_to_workjson.py data/works_src

# 调试单篇，只打印结果
python tools/md_to_workjson.py data/works_src/essay-2.md --demo
```

生成 JSON 还包含 `byline`、`reading_minutes` 与 `image_urls`，供详情页显示署名、阅读时长和打开图片预览。

## 从知识库重新导入

仅在原始知识库更新时运行：

```powershell
python tools/import_knowledgebase.py
python tools/md_to_workjson.py data/works_src
```

导入器按稳定文件指纹定位当前知识库导出，并从当前文件名读取收录学期。可可靠提取文字的
PDF/DOCX/PPTX 与公众号正文使用 `verbatim: true` 模式，所有非空白字符按来源保存；编译时会
自动合并页面行宽造成的硬换行，并把章节标题、拍摄信息和配词整理为阅读区块。扫描件、
乱码文字层和无法可靠还原顺序的版面直接生成原页图片，不使用人工转写或摘要代替原文。

人工校订 `verbatim: true` 稿件时仍可使用结构标记：`##` 生成横排小标题，`>` 生成诗词
引文区块，`*出处*` 生成小字出处。标记只控制渲染结构，不进入小程序正文。

每次导入都会生成 `source-manifest.json`。以下命令会重新读取知识库源文件、校验 SHA-256，
并比对编译后 JSON 的正文哈希或原页数量：

```powershell
python tools/import_knowledgebase.py --audit
```

人工校订过的稿件不会被后续导入覆盖。修改这类稿件并重新编译后，只刷新校验清单：

```bash
python tools/import_knowledgebase.py --refresh-curated
```

## 内容红线

- 只收录已取得作者授权的文件；导入脚本不得擅自增删、脱敏或改写原文。
- 不写入 IMA 临时签名图、HTTP 图片或本机绝对路径。
- 原文链接只作为来源信息；正文与必要配图必须在小程序内完整可读。
- 改稿后始终先跑 `--check`，再覆盖 JSON。
