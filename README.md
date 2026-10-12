# 宋词导读 · 课程助手（微信小程序）

《宋词导读》(GEHA1117) 单课程查询工具：全学期每周读哪些词、本学期要交什么、往届同学做成过什么样、词作原文与自撰简注去哪看。

**本产品为学生个人创作的学习辅助工具，非课程或学校官方发布，内容仅供参考，一切要求以教师课堂通知为准。**

---

## 目录

- [线上架构](#线上架构)
- [更新作品（一键发布）](#更新作品一键发布)
- [新作品上架流程](#新作品上架流程)
- [本地开发（排查/调试用）](#本地开发排查调试用)
- [工具链](#工具链)
- [包体结构](#包体结构)
- [内容红线](#内容红线)
- [目录速览](#目录速览)

---

## 线上架构

小程序已接入**微信云开发**（CloudBase），线上版本 `config.js` 配置如下：

```javascript
// miniprogram/config.js
module.exports = {
  BASE_URL: 'http://127.0.0.1:8080',   // 保留位，云模式下不生效
  DATA_VERSION: 'v1',
  STORAGE_PREFIX: 'sc_',
  CACHE_TTL: 7 * 24 * 3600 * 1000,
  USE_CLOUD: true,                      // 云端优先
  CLOUD_ENV: 'cloudbase-d2gl2ugjed4801d9f'
};
```

### 数据取数顺序（USE_CLOUD = true）

```
云数据库 content 集合（_id = cacheKey，如 work__essay-2）
    ↓ 云端未命中
包内兜底 fallback.js（archive / cipai / maps / ci-detail 已内嵌，course/weeks 等 6 类随包发布）
    ↓ 兜底也不存在
空态：「暂未收录，陆续收录中」
```

- **course / weeks / schedule / ci-index / books / semester**：包内随发 → 离线可用。
- **archive / cipai / maps / ci-detail（52 篇）**：内嵌于 `services/local-content.js` → 云端空时自动兜底。
- **works（44 篇作品）**：被 `packOptions.ignore` 排除出包（节省主包体积） → **必须发到云端 `content` 集合**。
- **readings（阅读材料）**：由 `tools/import_readings.py` 生成 JS 模块 → 直接放进分包，不走云数据库。

### 数据更新免提审

**所有 `content` 集合内的文档改后即时生效，无需重新提交审核。** 作品/档案/词牌卡/篇目详情等都走这个通道：云端有同名 `_id` 文档 → 优先采用；没有 → 回退包内兜底。

---

## 更新作品（一键发布）

新增或修改作品后，在管理页一键发到云端：

1. **重生成内嵌数据**：`node tools/gen_local_content.js`
2. **开发者工具 `Ctrl / Cmd + R` 重编译**
3. **进入管理页**：页面底部 →「管理后台 · 一键发布作品」
4. **点按钮**：并发批量调 `saveContent` 云函数，44 篇 10-20 秒完成

### 权限说明

- `saveContent` 云函数校验 `ADMIN_OPENIDS` 环境变量白名单（在云开发控制台「云函数 → saveContent → 配置 → 环境变量」设置），非管理员调用返回 403。
- 管理页进入后自动显示当前微信的 OPENID，方便与白名单对比。

### 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 全部失败 403 + "OPENID 不在白名单" | 环境变量里的 OPENID 与当前扫码微信不匹配，或改环境变量后未重传云函数 | 复制管理页显示的 OPENID → 覆盖 `ADMIN_OPENIDS` → 右键 `cloudfunctions/saveContent` 上传部署 |
| 页面空白 | 云端有空文档但字段不完整 | 在 `content` 集合里删除 `_id = course / weeks / schedule / ci-index / books` 等空文档（这些类型应走包内兜底） |

---

## 新作品上架流程

完整的「写稿 → 上架」链条：

```
1. 在 data/works_src/ 下按模板写 Markdown（见 data/works_src/_example.md）
2. python tools/md_to_workjson.py        → 生成 data/works/{id}.json
3. node tools/gen_local_content.js       → 更新 services/works-bundled.js + services/local-content.js
4. 开发者工具 Ctrl/Cmd + R 重编译
5. 「关于」→「管理后台」→ 点击一键发布
6. 云数据库 content 集合即时生效（免提审）
```

---

## 本地开发（排查/调试用）

排查问题时临时切回本地数据源（不依赖云端）：

```bash
cd miniprogram
python -m http.server 8080 --bind 127.0.0.1
```

然后把 `config.js` 的 `USE_CLOUD` 改为 `false`，重编译即可。排查完改回 `true`。

---

## 工具链

| 工具 | 用途 | 命令 |
|---|---|---|
| `tools/gen_local_content.js` | 生成 `services/local-content.js`（包内兜底）+ `services/works-bundled.js`（一键发布数据源） | `node tools/gen_local_content.js` |
| `tools/md_to_workjson.py` | Markdown 作品稿 → `data/works/{id}.json` sections 格式 | `python tools/md_to_workjson.py` |
| `tools/import_readings.py` | 阅读 PDF 页图 → 阅读分包 Markdown / JSON | `python tools/import_readings.py` |
| `tools/build_bundled_data.py` | course / weeks 等核心 6 类随包发布数据 | `python tools/build_bundled_data.py` |

稿源目录说明见 `data/works_src/README.md` 和 `data/works_src/_example.md`。

---

## 包体结构

| 区域 | 内容 | 说明 |
|---|---|---|
| 主包（≤ 2MB） | 4 tab + 公共子页 + services / components / utils | local-content.js（119KB）+ works-bundled.js（262KB）均进主包，总量约 400KB，远在 2MB 限制内 |
| 分包 work-text | 文字类作品详情 | ≤ 2MB |
| 分包 work-photo-a / work-photo-b | 摄影类作品详情 | ≤ 2MB |
| 分包 reading-a / reading-b | 阅读材料原页 | ≤ 2MB |

被排除出包（`project.config.json` 的 `packOptions.ignore`）：`data/works`（作品 JSON，只走云端）、`data/readings`。

---

## 内容红线（验收时 grep 应为空）

- 作品必须有作者授权，导入时不得改写或擅自脱敏原文
- 学生姓名/学号用「某同学 / 笔者」，正文不出现真实姓名
- 无 QQ 群号、网盘地址、腾讯文档链接
- 无截止日期或倒计时（数据文件不得出现 `date` / `ddl` / `deadline` 字段）
- 词作注音简注全部自撰，词话摘引仅限公有领域文献
- 非官方声明常驻（各页面 `disclaimer-bar` 组件）

---

## 目录速览

```
cloudfunctions/                       # 云函数（通过开发者工具上传部署）
├─ login/         → wx-server-sdk 登录，返回 OPENID
├─ saveContent/   → 管理员发布内容到 content 集合（ADMIN_OPENIDS 白名单）
└─ submitWork/    → 学生投稿写 works_submissions（个人主体暂未开放）

miniprogram/
├─ app.json / app.js / app.wxss      # 全局：4 tab + 14 页，古典中国风设计
├─ config.js                          # USE_CLOUD / CLOUD_ENV 开关
├─ project.config.json               # appid / cloudfunctionRoot / packOptions
├─ services/
│  ├─ data.js          # 数据层唯一入口 getData(type,key)，云优先→兜底→空态
│  ├─ cloud.js         # 云开发封装（readContent / callFunction / uploadFile）
│  ├─ registry.js      # type → URL 注册表
│  ├─ fallback.js      # 包内兜底（合并 bundled-data + local-content）
│  ├─ bundled-data.js  # course / weeks / schedule / ci-index / books（由 build_bundled_data.py 生成）
│  ├─ local-content.js # archive / cipai / maps / ci-detail 内嵌（由 gen_local_content.js 生成）
│  └─ works-bundled.js # 44 篇作品内嵌，供管理页一键发布用（由 gen_local_content.js 生成）
├─ pages/
│  ├─ admin-publish/   # 管理后台：一键发布作品 + OPENID 诊断
│  ├─ overview/        # 首页「课程概览」
│  ├─ homework/        # 作业
│  ├─ archive/         # 档案（学期作品索引）
│  ├─ library/         # 资料
│  ├─ schedule/        # 教学周历
│  ├─ ci-list/         # 词作列表
│  ├─ ci-detail/       # 单首词详情
│  ├─ cipai/           # 词牌卡
│  ├─ maps/            # 脉络图
│  ├─ notes/           # 我的笔记
│  ├─ about/           # 关于 / 定位声明 / 管理入口
│  └─ task/            # 任务页
├─ packages/
│  ├─ work-text/       # 文字作品详情
│  ├─ work-photo-a/    # 摄影作品详情（A 组）
│  ├─ work-photo-b/    # 摄影作品详情（B 组）
│  ├─ reading-a/       # 阅读材料（A 组）
│  └─ reading-b/       # 阅读材料（B 组）
├─ components/         # 复用展示组件
├─ utils/              # store / constants / ui 工具
├─ images/             # tabbar 图标等
└─ data/               # 本地数据 JSON（云模式下不直接读取，部分被排除出包）
   ├─ ci-detail/       # 52 首词（已内嵌进 local-content.js 兜底）
   ├─ works/           # 44 篇作品（排除出包，仅云端；原始 JSON 供 gen_local_content 读）
   └─ readings/        # 阅读材料（排除出包，由 import_readings.py 进分包）

tools/
├─ gen_local_content.js      # 生成 local-content.js + works-bundled.js
├─ md_to_workjson.py         # Markdown → works JSON
├─ import_readings.py        # 阅读 PDF → 分包数据
└─ build_bundled_data.py     # 核心 6 类 → bundled-data.js
```
