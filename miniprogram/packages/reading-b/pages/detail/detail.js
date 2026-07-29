const readings = require('../../data/readings.js');
const { openSource } = require('../../../../utils/work-detail-page.js');

Page({
  data: { loading: true, error: '', id: '', work: null },
  onLoad(options) {
    const id = options.id || '';
    const work = readings[id];
    if (!work) {
      this.setData({ loading: false, error: '暂未收录该阅读材料' });
      return;
    }
    this.setData({ loading: false, id, work });
    wx.setNavigationBarTitle({ title: work.title || '推荐阅读' });
  },
  onSource() { openSource((this.data.work || {}).original_url); },
  onShareAppMessage() {
    const work = this.data.work || {};
    return { title: work.title || '宋词导读·推荐阅读', path: '/' + this.route + '?id=' + this.data.id };
  }
});
