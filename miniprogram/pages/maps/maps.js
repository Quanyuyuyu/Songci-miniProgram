const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

const FAMILY_LABEL = { xiaoling: '小令', zhongdiao: '中调', manci: '慢词' };

Page({
  data: {
    loading: true,
    error: '',
    view: 'timeline',     // timeline | family | theme
    timeline: [],
    eras: [],
    currentWeek: 0,
    family: [],
    themes: [],
    expandedTheme: '',
    themeItems: {}
  },

  onLoad() {
    Promise.all([
      getData('maps'),
      getData('ci-index'),
      getData('semester', '26spring')
    ]).then(([maps, idx, semester]) => {
      const indexMap = {};
      (idx.list || []).forEach((c) => { indexMap[c.id] = c; });
      this._index = indexMap;

      const family = Object.keys(maps.family || {}).map((k) => ({
        key: k,
        label: FAMILY_LABEL[k] || k,
        names: maps.family[k]
      }));

      const themes = (maps.themes || []).map((t) => ({
        tag: t.tag,
        desc: t.desc,
        count: (t.ci_ids || []).length,
        ci_ids: t.ci_ids || []
      }));

      this.setData({
        loading: false,
        timeline: maps.timeline || [],
        eras: maps.eras || [],
        currentWeek: (semester && semester.current_week) || 0,
        family: family,
        themes: themes
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  onSegTap(e) {
    this.setData({ view: e.currentTarget.dataset.view });
  },

  onThemeTap(e) {
    const tag = e.currentTarget.dataset.tag;
    const expanded = this.data.expandedTheme === tag ? '' : tag;
    const themeItems = Object.assign({}, this.data.themeItems);
    if (expanded && !themeItems[expanded]) {
      const theme = this.data.themes.find((t) => t.tag === expanded);
      themeItems[expanded] = (theme ? theme.ci_ids : [])
        .map((id) => this._index[id]).filter(Boolean);
    }
    this.setData({ expandedTheme: expanded, themeItems: themeItems });
  },

  goCipaiList(e) {
    wx.navigateTo({ url: '/pages/ci-list/ci-list?cipai=' + encodeURIComponent(e.currentTarget.dataset.name) });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  }
});
