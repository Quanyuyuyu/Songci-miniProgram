const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    keyword: '',
    cipaiList: [],
    authorList: [],
    schoolList: [],
    activeCipai: '',
    activeAuthor: '',
    activeSchool: '',
    filtered: [],
    total: 0
  },

  onLoad(options) {
    getData('ci-index').then((idx) => {
      const list = idx.list || [];
      this._list = list;
      const uniq = (arr) => Array.from(new Set(arr));
      this.setData({
        loading: false,
        total: list.length,
        cipaiList: uniq(list.map((c) => c.cipai)),
        authorList: uniq(list.map((c) => c.author)),
        schoolList: uniq(list.map((c) => c.school)),
        activeCipai: options.cipai || ''
      });
      this.applyFilter();
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  applyFilter() {
    const kw = (this.data.keyword || '').trim();
    let list = this._list || [];
    if (this.data.activeCipai) list = list.filter((c) => c.cipai === this.data.activeCipai);
    if (this.data.activeAuthor) list = list.filter((c) => c.author === this.data.activeAuthor);
    if (this.data.activeSchool) list = list.filter((c) => c.school === this.data.activeSchool);
    if (kw) {
      list = list.filter((c) =>
        (c.cipai + (c.title || '') + c.author + (c.first_line || '')).indexOf(kw) >= 0
      );
    }
    list = list.slice().sort((a, b) => a.week - b.week || a.id.localeCompare(b.id));
    this.setData({ filtered: list });
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
    this.applyFilter();
  },

  onFilterTap(e) {
    const { kind, value } = e.currentTarget.dataset;
    const key = kind === 'cipai' ? 'activeCipai' : kind === 'author' ? 'activeAuthor' : 'activeSchool';
    this.setData({ [key]: this.data[key] === value ? '' : value });
    this.applyFilter();
  },

  onClearFilter() {
    this.setData({ activeCipai: '', activeAuthor: '', activeSchool: '', keyword: '' });
    this.applyFilter();
  }
});
