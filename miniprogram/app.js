// 宋词导读·课程助手 —— 学生个人创作的学习辅助工具，非课程或学校官方发布
const { USE_CLOUD, CLOUD_ENV } = require('./config.js');

App({
  globalData: {
    // 当前学期（与 data/archive-index.json 中最近一期保持一致）
    currentTerm: '26Spring',
    currentTermDisplay: '2026 春',
    archiveEntry: null,
    cloudReady: false
  },
  onLaunch() {
    // 初始化微信云开发（USE_CLOUD=true 且已填入真实环境 ID 时生效）
    if (USE_CLOUD && CLOUD_ENV && CLOUD_ENV !== 'your-cloud-env-id') {
      if (wx.cloud) {
        wx.cloud.init({
          env: CLOUD_ENV,
          traceUser: true
        });
        this.globalData.cloudReady = true;
      } else {
        console.warn('[cloud] 当前基础库不支持 wx.cloud，请升级开发者工具 / 基础库版本');
      }
    }
  }
});
