// 网络与缓存均不可用时启用；阅读周历完整打包，保证真机也能离线打开。
const bundledData = require('./bundled-data.js');
// 本地内容兜底（档案/词牌/脉络图/篇目详情）：由 tools/gen_local_content.js 生成，
// 云模式查不到云端文档时回退到此，保证体验版/正式版无需逐条发布也能显示。
const localContent = require('./local-content.js');

module.exports = Object.assign({}, localContent, {
  course: bundledData.course,
  weeks: bundledData.weeks,
  schedule: bundledData.schedule,
  'ci-index': bundledData['ci-index'],
  books: bundledData.books,
  'semester__26spring': bundledData['semester-26spring'],
  // 题壁：云端未发布时的兜底（空留言流，页面渲染空态）
  board: { messages: [] }
});
