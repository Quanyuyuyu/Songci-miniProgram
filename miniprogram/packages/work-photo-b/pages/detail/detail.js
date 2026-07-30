const { getData } = require('../../../../services/data.js');
const { errorReason } = require('../../../../utils/ui.js');
const { formatTerm } = require('../../../../utils/term.js');

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
  data: {
    loading: true,
    error: '',
    id: '',
    work: null
  },

  onLoad(options) {
    const id = options.id || '';
    this.setData({ id });
    if (!id) {
      this.setData({ loading: false, error: '缺少作品标识' });
      return;
    }

    getData('work', id)
      .then((work) => {
        const viewWork = Object.assign({}, work, { termDisplay: formatTerm(work.term) });
        this.setData({ loading: false, work: viewWork });
        wx.setNavigationBarTitle({ title: work.title || '作品详情' });
      })
      .catch((err) => this.setData({ loading: false, error: errorReason(err) }));
  },

  onSource() {
    openSource((this.data.work || {}).original_url);
  },

  onShareAppMessage() {
    const work = this.data.work || {};
    return {
      title: work.title || '宋词导读·优秀作品',
      path: '/' + this.route + '?id=' + this.data.id
    };
  }
});
