const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

const FAMILY_LABEL = { xiaoling: '小令', zhongdiao: '中调', manci: '慢词' };

Page({
  data: {
    loading: true,
    error: '',
    list: [],
    expanded: ''
  },

  onLoad() {
    Promise.all([getData('cipai'), getData('ci-index')]).then(([cipai, idx]) => {
      const indexMap = {};
      (idx.list || []).forEach((c) => { indexMap[c.id] = c; });
      const list = (cipai.list || []).map((cp) => ({
        name: cp.name,
        familyLabel: FAMILY_LABEL[cp.family] || '',
        meter: cp.meter,
        tone: cp.tone,
        items: (cp.ci_ids || []).map((id) => indexMap[id]).filter(Boolean)
      }));
      this.setData({ loading: false, list: list });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  onExpand(e) {
    const name = e.currentTarget.dataset.name;
    this.setData({ expanded: this.data.expanded === name ? '' : name });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  }
});
