# 作品导入方法（markdown → 小程序闭环）

目标：每个 IMA 里的作品，用 **markdown 写稿** → 转换器生成 `miniprogram/data/works/<id>.json`
→ 小程序 `work-detail` 页直接渲染，全程**内部闭环**，无需外链/网页。

---

## 一、为什么不用"真·markdown 网页"

小程序**没有原生 markdown 渲染器**，也不能用 web-view 内嵌 IMA 网页（个人主体无 web-view 权限）。
我们已有的 `work-detail` 页用 `sections` 结构化数组渲染（`h / p / quote / img`），
它等价于"小程序原生版的 markdown"，且无需运行时解析、零依赖、最稳。
所以流程是：**你用 markdown 写作 → 转换器把 markdown 编译成 sections JSON**。

---

## 二、写稿规范（每个作品一个 .md）

文件名即作品 id，需与 `archive-all.json` 里的 id 一致：
`essay-2.md` → `essay-2.json`；`photo-5.md` → `photo-5.json`。

文件结构：

```
---
title: 作品标题（必填）
form_tag: 文字        # 文字 | 摄影 | 创作
term: 2026春          # 收录学期，可空
collecting: false     # true 则显示"内容整理中"空态
---

正文段落写这里，空行分段。

# 小标题（可选）

> 引用/金句（可多行，保留换行）

![图片说明](图片地址)
```

语法对照：
- 普通行 → `type:"p"`
- `# 标题` → `type:"h"`
- `> 引用` → `type:"quote"`（连续多行 `>` 自动合并并保留换行）
- `![说明](地址)` → `type:"img"`（独立成行；也支持行内穿插）

---

## 三、图片怎么放（闭环成败关键点）

| 写法 | 结果 | 适用 |
|------|------|------|
| `![x](https://...)` | 原样保留 | 生产环境必须是 **HTTPS** 且在小程序后台「downloadFile 合法域名」白名单内 |
| `![x](images/works/xxx.jpg)` | 自动拷贝到 `miniprogram/images/works/`，改写为本地路径 `/images/works/xxx.jpg` | **推荐**：无需联网，模拟器+真机都能显示 |
| IMA 带签名链接 | ❌ 会过期失效 | 不建议写死 |

**推荐做法**：把图片下载到 `miniprogram/images/works/`，md 里写相对路径。
注意主包 2MB / 总包 20MB 上限，图片多时按需压缩或走子包。

> 真机预览时，若图片走开发服务器（http://127.0.0.1:8080/...），手机连的是自己，
> 必须改成开发机的**局域网 IP**（如 http://192.168.x.x:8080/...）。本地图片打包则无此问题。

---

## 四、转换 & 刷新

```bash
# 进入项目根目录
cd songci-miniprogram

# 批量转换 works_src/ 下所有 .md（README 与 _ 开头的文件自动跳过）
python tools/md_to_workjson.py data/works_src

# 或转换单个文件
python tools/md_to_workjson.py data/works_src/essay-2.md

# 只想看生成结果、不写文件（调试用）
python tools/md_to_workjson.py --demo data/works_src/_example.md
```

转换后，在微信开发者工具里 **Ctrl/Cmd + R 重新编译** 即可看到新作品，
无需重启本地数据服务（它只托管静态 JSON/图片）。

---

## 五、从 IMA 拉内容的脱敏提醒

- 作品正文**不要出现学生姓名/学号**（合规红线），用「某同学」「笔者」等代替。
- 不要写 QQ 群、网盘、腾讯文档等外部拉人链接。
- 文案避免"开课倒计时/date 字段"等时效表述。
