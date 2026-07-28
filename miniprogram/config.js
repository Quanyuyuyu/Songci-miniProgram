// 全局配置：切换正式环境时只需修改 BASE_URL 一行
// 本地开发：在 miniprogram/ 目录执行  python -m http.server 8080
// 并在微信开发者工具「详情 → 本地设置」勾选「不校验合法域名」
module.exports = {
  BASE_URL: 'http://127.0.0.1:8080',
  DATA_VERSION: 'v5',
  STORAGE_PREFIX: 'sc_',
  CACHE_TTL: 7 * 24 * 3600 * 1000 // 数据缓存 7 天
};
