// 全局配置
// 本地开发：在 miniprogram/ 目录执行  python -m http.server 8080 --bind 127.0.0.1
// 并在微信开发者工具「详情 → 本地设置」勾选「不校验合法域名」
module.exports = {
  // —— 本地开发数据源（USE_CLOUD=true 时不再使用）——
  BASE_URL: 'http://127.0.0.1:8080',
  DATA_VERSION: 'v1',
  STORAGE_PREFIX: 'sc_',
  CACHE_TTL: 7 * 24 * 3600 * 1000, // 数据缓存 7 天

  // ===== 微信云开发开关 =====
  // 上线步骤：
  // 1) 公众平台 / 开发者工具开通云开发，拿到环境 ID（形如 cloud1-xxxxxxxx）
  // 2) 把下面 CLOUD_ENV 改为你的环境 ID
  // 3) 确认无误后把 USE_CLOUD 改为 true，前端即走云数据库 / 云存储
  // ⚠️ 注意：免费环境在「小程序发布后第 15 天」自动到期，务必改用
  //   按量付费环境，或报名「AI 小程序成长计划」领取 6 个月个人版环境。
  USE_CLOUD: true,
  CLOUD_ENV: 'cloudbase-d2gl2ugjed4801d9f',

  // ===== 建议留言窗口（自建提交，个人主体风险提示）=====
  // true  = 启用自建「建议窗口」，用户留言直存云库 suggestions 集合（不依赖微信官方反馈）
  // ⚠️ 个人主体下「自建内容收集（评价/建议）」属社交-笔记未开放类目，提审有被驳风险。
  //    若审核被驳，把本项改为 false，题壁页底部自动回退为 open-type="feedback" 官方通道（零风险），无需改其他代码。
  ENABLE_SELF_SUGGEST: true
};
