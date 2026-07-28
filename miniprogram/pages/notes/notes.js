const { getData } = require('../../services/data.js');
const { copyText } = require('../../utils/ui.js');
const store = require('../../utils/store.js');
const { NOTE_PREFIX } = require('../../utils/constants.js');

Page({
  data: {
    loading: true,
    notes: [],
    hint: '笔记仅保存在本机；期末习作可由平时积累的词作体悟连缀成文。'
  },

  onShow() {
    this.loadNotes();
  },

  loadNotes() {
    const keys = store.keysWithPrefix(NOTE_PREFIX);
    const records = keys
      .map((k) => store.getByFullKey(k, null))
      .filter((r) => r && r.text && r.ci_id);

    getData('ci-index').then((idx) => {
      const indexMap = {};
      (idx.list || []).forEach((c) => { indexMap[c.id] = c; });
      const notes = records.map((r) => {
        const ci = indexMap[r.ci_id] || {};
        return {
          ci_id: r.ci_id,
          cipai: ci.cipai || '',
          title: ci.title || '',
          author: ci.author || '',
          text: r.text,
          updated_at: r.updated_at || 0
        };
      }).sort((a, b) => b.updated_at - a.updated_at);
      this.setData({ loading: false, notes: notes });
    }).catch(() => {
      const notes = records.map((r) => ({
        ci_id: r.ci_id, cipai: '', title: '', author: '', text: r.text, updated_at: r.updated_at || 0
      }));
      this.setData({ loading: false, notes: notes });
    });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  },

  onCopyAll() {
    if (!this.data.notes.length) return;
    const text = this.data.notes.map((n) => {
      const head = n.cipai ? '《' + n.cipai + (n.title ? '·' + n.title : '') + '》' + n.author : n.ci_id;
      return head + '\n' + n.text;
    }).join('\n\n——\n\n');
    copyText(text, '全部笔记已复制');
  }
});
