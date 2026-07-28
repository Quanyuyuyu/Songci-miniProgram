const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    view: 'week',          // week | all
    ruleText: '',
    currentLesson: 0,
    weekLesson: null,      // 本周课次对象
    lessons: [],           // 全学期（已合并篇目信息）
    notice: ''
  },

  onLoad() {
    Promise.all([
      getData('schedule'),
      getData('ci-index'),
      getData('semester', '26spring'),
      getData('weeks')
    ]).then(([schedule, ciIndex, semester, weeks]) => {
      const indexMap = {};
      (ciIndex.list || []).forEach((c) => { indexMap[c.id] = c; });

      const lessons = (schedule.lessons || []).map((les) => ({
        lesson: les.lesson,
        topic: les.topic,
        items: (les.items || []).map((it) => {
          const ci = indexMap[it.ci_id] || {};
          return {
            ci_id: it.ci_id,
            updated: !!it.updated,
            cipai: ci.cipai || '',
            title: ci.title || '',
            author: ci.author || '',
            dynasty: ci.dynasty || '',
            level: ci.level || 'skim'
          };
        })
      }));

      const currentWeek = (semester && semester.current_week) || 0;
      const weekLesson = lessons.find((l) => l.lesson === currentWeek) || null;
      const weekInfo = (weeks.weeks || []).find((w) => w.w === currentWeek);

      this.setData({
        loading: false,
        ruleText: schedule.rule_text || '',
        lessons: lessons,
        currentLesson: currentWeek,
        weekLesson: weekLesson,
        notice: weekLesson
          ? ('本周（W' + currentWeek + ' · ' + (weekInfo ? weekInfo.theme : '') + '）精读词目')
          : '本学期当前周不在精读课次范围内（第 3–14 课），可在全学期视图查看'
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  onSegTap(e) {
    this.setData({ view: e.currentTarget.dataset.view });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  }
});
