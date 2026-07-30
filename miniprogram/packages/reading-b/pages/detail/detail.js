const readings = require('../../data/readings.js');

function copySource(url) {
  if (!url) return;
  wx.setClipboardData({
    data: url,
    success: () => wx.showToast({ title: '来源链接已复制', icon: 'none' })
  });
}

function openSource(url) {
  if (!url) return;
  if (url.indexOf('https://mp.weixin.qq.com/') === 0 && wx.openOfficialAccountArticle) {
    wx.openOfficialAccountArticle({ url, fail: () => copySource(url) });
    return;
  }
  copySource(url);
}

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
