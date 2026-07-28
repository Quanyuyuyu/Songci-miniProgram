const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    weeks: [],
    notice: ''
  },

  onLoad() {
    Promise.all([
      getData('schedule'),
      getData('ci-index')
    ]).then(([schedule, ciIndex]) => {
      const indexMap = {};
      (ciIndex.list || []).forEach((c) => { indexMap[c.id] = c; });

      const weeks = (schedule.weeks || []).map((week) => ({
        week: week.week,
        topic: week.topic,
        items: (week.items || []).map((it) => {
          const ci = indexMap[it.ci_id] || {};
          return {
            ci_id: it.ci_id,
            cipai: ci.cipai || '',
            title: ci.title || '',
            author: ci.author || '',
            dynasty: ci.dynasty || ''
          };
        })
      }));

      this.setData({
        loading: false,
        weeks: weeks,
        notice: schedule.note || ''
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  }
});
