# 阅读材料工作流

知识库中的课程阅读 PDF 先生成页图型 Markdown，再编译为小程序原生 `sections` JSON。
不使用 OCR，不重排正文，不改写原文；每个 Markdown 图片引用对应原 PDF 的一页。

```powershell
python tools/import_readings.py
python tools/import_readings.py --audit
```

生成位置：

- Markdown：`data/readings_src/reading-*.md`
- JSON：`miniprogram/data/readings/reading-*.json`
- 分包数据与页图：`miniprogram/packages/reading-a/` 与 `reading-b/`
