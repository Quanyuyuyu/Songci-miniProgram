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
  }
});
