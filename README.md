# 宋词导读 · 课程助手（微信小程序）

《宋词导读》(GEHA1117) 单课程查询工具：全学期每周读哪些词、本学期要交什么、往届同学做成过什么样、词作原文与自撰简注去哪看。

**本产品为学生个人创作的学习辅助工具，非课程或学校官方发布，内容仅供参考，一切要求以教师课堂通知为准。**

## 快速开始（本地开发演示）

1. **启动数据服务**（JSON 数据层，小程序通过 wx.request 异步读取）：
   ```bash
   cd songci-miniprogram/miniprogram
   python -m http.server 8080
   ```
   数据地址即 `http://127.0.0.1:8080/data/*.json`。
2. **导入微信开发者工具**：选择本目录（`songci-miniprogram/`），AppID 选「测试号」。
3. **关闭域名校验**：详情 → 本地设置 → 勾选「不校验合法域名、web-view…」。
4. 编译运行即可。真机预览时 127.0.0.1 不可达，请将 `miniprogram/config.js` 的 `BASE_URL` 改为局域网 IP（如 `http://192.168.x.x:8080`）。

## 切换到正式环境

1. 将 `miniprogram/data/` 整个目录上传到任意 HTTPS 静态托管（自有服务器 / COS / 任意静态站点服务）。
2. 修改 `miniprogram/config.js` 的 `BASE_URL` 为正式域名（仅此一行）。
3. 在小程序后台「开发管理 → 服务器域名」将该域名加入 request 合法域名。

## 架构约定（重要）

- **数据读取唯一入口**：`services/data.js` 的 `getData(type, key)`。页面中禁止出现 `wx.request`、禁止 `require` 任何 JSON 文件；新增数据文件时只需在 `services/registry.js` 注册一条 type → 路径映射。
- **降级链**：内存缓存 → storage 离线缓存（7 天）→ `services/fallback.js` 内联兜底（仅 course/weeks）→ 空态文案。
- **本地功能只存本机**（wx.storage，不回传、不具凭证效力）：拍照配词自检、期末规范自检、私人笔记（`sc_note_{ci_id}`，「我的笔记」页可汇总复制）。
- **阅读周历**：`data/schedule.json` 只维护全学期教学周与阅读词目，不设实时周状态；实际进度始终以当学期课堂安排为准。
- **词作详情**：`data/ci-detail/` 中每首词都使用统一字段，均提供原文、注音、简注、背景、阅读问题与互读链接，不划分阅读等级。
- **作品写作**：知识库授权原件先导入 `data/works_src/` 的保真 Markdown，再由 `tools/md_to_workjson.py` 生成小程序原生 `sections` JSON；扫描件使用原页图片，不转写。
- **课程阅读**：`tools/import_readings.py` 将阅读 PDF 生成为页图型 Markdown 和 JSON，分别进入两个阅读分包，资料页可在小程序内直接打开。
- **包体结构**：主包只保留公共页面和索引；优秀作品与阅读原页按五个分包发布，每个包均控制在 2 MiB 内。

## 内容红线（验收时 grep 应为空）

- 作品必须有作者授权，导入时不得改写或擅自脱敏原文；无 QQ 群号、网盘地址、腾讯文档链接；无任何截止日期或倒计时（数据文件不得出现 `date` / `ddl` / `deadline` 字段）；词作注音简注全部自撰，词话摘引仅限公有领域文献。

## 目录速览

```
miniprogram/
├─ app.json / app.js / app.wxss   # 全局：4 个 tab、设计 token（宣纸/墨蓝/青磁/朱砂）
├─ config.js                      # BASE_URL 一行切环境
├─ services/                      # data.js(唯一入口) registry.js fallback.js
├─ utils/                         # store(storage) ui constants
├─ components/                    # 8 个展示组件
├─ pages/                         # 4 tab + 9 子页
└─ data/                          # 远端 JSON（本地开发时由 python 静态服务提供）
```
