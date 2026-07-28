const { getData } = require('../../services/data.js');
const { errorReason, toast } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    terms: [],
    categories: [],
    activeCategory: 'creative',
    works: [],
    note: ''
  },

  onLoad() {
    Promise.all([getData('archive-index'), getData('archive', 'all')])
      .then(([index, all]) => {
        this.setData({
          loading: false,
          terms: index.terms || [],
          categories: index.categories || [],
          note: index.note || '',
          _all: all
        });
        this.applyCategory('creative');
      })
      .catch((err) => {
        this.setData({ loading: false, error: errorReason(err) });
      });
  },

  applyCategory(key) {
    const all = this.data._all || {};
    this.setData({
      activeCategory: key,
      works: all[key] || []
    });
  },

  onCategoryTap(e) {
    this.applyCategory(e.currentTarget.dataset.key);
  },

  onWorkTap(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) {
      toast('作品内容整理中');
      return;
    }
    wx.navigateTo({ url: '/pages/work-detail/work-detail?id=' + id });
  },

  onTermTap(e) {
    const item = e.currentTarget.dataset.item;
    if (item.status === 'ready') {
      wx.navigateTo({ url: '/pages/task/task?type=discussion' });
    } else {
      toast(item.display + '：内容陆续收录中');
    }
  }
});
