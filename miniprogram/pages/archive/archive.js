const { getData } = require('../../services/data.js');
const { errorReason, toast } = require('../../utils/ui.js');
const { formatTerm } = require('../../utils/term.js');

Page({
  data: {
    loading: true,
    error: '',
    terms: [],
    categories: [],
    activeTerm: '26Spring',
    activeTermDisplay: '2026 春',
    activeCategory: 'photo',
    works: [],
    note: '',
    returnTarget: null
  },

  onLoad() {
    Promise.all([getData('archive-index'), getData('archive', 'all')])
      .then(([index, all]) => {
        const terms = (index.terms || []).map((term) => {
          const count = ['photo', 'essay'].reduce((total, category) => {
            return total + (all[category] || []).filter((work) => work.term === term.term).length;
          }, 0);
          return Object.assign({}, term, {
            count: count,
            statusText: count ? '已收录 ' + count + ' 篇' : '暂未收录'
          });
        });
        this.setData({
          loading: false,
          terms: terms,
          categories: index.categories || [],
          note: index.note || '',
          _all: all
        }, () => {
          this.applyFilters(this._pendingCategory || 'photo', this.data.activeTerm);
        });
      })
      .catch((err) => {
        this.setData({ loading: false, error: errorReason(err) });
      });
  },

  onShow() {
    const app = getApp();
    const entry = app.globalData.archiveEntry;
    if (!entry) {
      this.setData({ returnTarget: null });
      return;
    }

    this._pendingCategory = entry.category || 'photo';
    this.setData({
      returnTarget: {
        url: entry.returnUrl,
        label: entry.returnLabel || '返回上一页'
      }
    });
    if (this.data._all) {
      this.applyFilters(this._pendingCategory, this.data.activeTerm);
    }
  },

  applyFilters(category, term) {
    const all = this.data._all || {};
    const source = all[category] || [];
    const works = category === 'creative'
      ? source
      : source.filter((work) => work.term === term);
    this.setData({
      activeCategory: category,
      activeTerm: term,
      activeTermDisplay: formatTerm(term),
      works: works.map((work) => Object.assign({}, work, {
        termDisplay: formatTerm(work.term)
      }))
    });
  },

  onCategoryTap(e) {
    this.applyFilters(e.currentTarget.dataset.key, this.data.activeTerm);
  },

  onTermTap(e) {
    this.applyFilters(this.data.activeCategory, e.currentTarget.dataset.term);
  },

  onWorkTap(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) {
      toast('作品内容整理中');
      return;
    }
    let packageName = 'work-text';
    if (id.indexOf('photo-') === 0) {
      const number = Number(id.split('-')[1]);
      packageName = number <= 11 ? 'work-photo-a' : 'work-photo-b';
    }
    wx.navigateTo({ url: '/packages/' + packageName + '/pages/detail/detail?id=' + id });
  },

  onReturn() {
    const target = this.data.returnTarget;
    if (!target || !target.url) return;
    getApp().globalData.archiveEntry = null;
    this._pendingCategory = '';
    this.setData({ returnTarget: null });
    wx.navigateTo({ url: target.url });
  }
});
