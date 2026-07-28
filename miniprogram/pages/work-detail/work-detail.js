const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');
const { formatTerm } = require('../../utils/term.js');

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
      .catch((err) => {
        this.setData({ loading: false, error: errorReason(err) });
      });
  },

  onPreviewImage(event) {
    const current = event.currentTarget.dataset.src;
    const work = this.data.work || {};
    const urls = work.image_urls || [];
    if (!current || !urls.length) return;
    wx.previewImage({ current, urls });
  },

  onShareAppMessage() {
    const work = this.data.work || {};
    return {
      title: work.title || '宋词导读·优秀作品',
      path: '/pages/work-detail/work-detail?id=' + this.data.id
    };
  }
});
