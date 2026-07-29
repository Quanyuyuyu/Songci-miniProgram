const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    textbooks: [],
    readings: [],
    booksNote: ''
  },

  onLoad() {
    getData('books').then((data) => {
      this.setData({
        loading: false,
        textbooks: data.textbooks || [],
        readings: data.readings || [],
        booksNote: data.note || ''
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  go(e) {
    wx.navigateTo({ url: e.currentTarget.dataset.url });
  },

  onReadingTap(e) {
    const item = e.currentTarget.dataset.item || {};
    if (item.id) {
      const packageName = ['reading-1', 'reading-2'].indexOf(item.id) >= 0
        ? 'reading-a'
        : 'reading-b';
      wx.navigateTo({ url: '/packages/' + packageName + '/pages/detail/detail?id=' + item.id });
      return;
    }
    if (item.url) {
      wx.setClipboardData({
        data: item.url,
        success: () => wx.showToast({ title: '网站地址已复制', icon: 'none' })
      });
    }
  }
});
