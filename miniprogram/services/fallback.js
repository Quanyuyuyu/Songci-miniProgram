// 网络与缓存均不可用时启用；阅读周历完整打包，保证真机也能离线打开。
const bundledData = require('./bundled-data.js');

module.exports = {
  course: {
    course: {
      name: '宋词导读', code: 'GEHA1117', credits: 2, hours: 32,
      school: '人文科学研究院', teacher: '陈娅妮', type: '通识选修'
    },
    grade: [
      { item: '考勤', percent: 5, note: '点名；含缺勤扣分硬规则' },
      { item: '课堂报告', percent: 20, note: '即讨论课展示，主题与周次逐学期变化' },
      { item: '平时表现与作业', percent: 35, note: '拍照配词 1 次 + 约 2 次词作反馈 + 课堂表现' },
      { item: '期末习作', percent: 40, note: '体悟与思考类习作，形式开放' }
    ],
    disclaimer: '本产品为学生个人创作的学习辅助工具，非课程或学校官方发布，内容仅供参考，一切要求以教师课堂通知为准。'
  },
  weeks: {
    weeks: [
      { w: 1, theme: '何谓「词」', period: 'tang' },
      { w: 2, theme: '唐人之词', period: 'tang' },
      { w: 3, theme: '花间词派', period: 'tang' },
      { w: 4, theme: '南唐词', period: 'tang' },
      { w: 5, theme: '北宋初期词风（一）', period: 'beisong' },
      { w: 6, theme: '北宋初期词风（二）', period: 'beisong' },
      { w: 7, theme: '柳永', period: 'beisong' },
      { w: 8, theme: '苏轼', period: 'beisong' },
      { w: 9, theme: '淮海词与山谷词', period: 'beisong' },
      { w: 10, theme: '咏物词专题', period: 'beisong' },
      { w: 11, theme: '周邦彦', period: 'beisong' },
      { w: 12, theme: '讨论课 1', period: 'beisong' },
      { w: 13, theme: '讨论课 2', period: 'beisong' },
      { w: 14, theme: '李清照', period: 'nansong' },
      { w: 15, theme: '辛弃疾', period: 'nansong' },
      { w: 16, theme: '姜夔', period: 'nansong' },
      { w: 17, theme: '期末习作提交', period: 'nansong' },
      { w: 18, theme: '考试周', period: 'nansong' }
    ],
    notice: '以教师课堂通知为准'
  },
  schedule: bundledData.schedule,
  'ci-index': bundledData['ci-index'],
  books: bundledData.books,
  'semester__26spring': bundledData['semester-26spring']
};
