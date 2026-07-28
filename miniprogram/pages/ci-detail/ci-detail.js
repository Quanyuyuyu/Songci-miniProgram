const { getData } = require('../../services/data.js');
const { errorReason, toast } = require('../../utils/ui.js');
const store = require('../../utils/store.js');
const { NOTE_PREFIX } = require('../../utils/constants.js');

const REL_LABEL = {
  same_cipai: '同调',
  same_author: '同人',
  same_theme: '同题',
  same_technique: '同法',
  same_source: '同源'
};

Page({
  data: {
    loading: true,
    error: '',
    ci: null,
    links: [],
    noteText: '',
    noteSaved: false
  },

  onLoad(options) {
    const id = options.id;
    if (!id) {
      this.setData({ loading: false, error: '缺少篇目参数' });
      return;
    }
    this._id = id;

    getData('ci-index').then((idx) => {
      const meta = (idx.list || []).find((c) => c.id === id);
      if (!meta) throw { code: 'EMPTY', reason: '未找到该篇目' };
      this._index = idx.list || [];
      this._meta = meta;
      if (meta.level === 'intensive') {
        return getData('ci-intensive', id).then((ci) => this.render(ci, meta));
      }
      return getData('ci-skim').then((skim) => {
        const ci = (skim.list || []).find((c) => c.id === id);
        if (!ci) throw { code: 'EMPTY', reason: '该篇目内容陆续整理中' };
        this.render(ci, meta);
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  render(ci, meta) {
    // 关联篇目：intensive 用人工连线；skim 及补充用索引现算（同调/同人）
    const links = [];
    const seen = { [meta.id]: true };
    (ci.links || []).forEach((l) => {
      const target = this._index.find((c) => c.id === l.ci_id);
      if (target && !seen[target.id]) {
        seen[target.id] = true;
        links.push({
          ci_id: target.id,
          relLabel: REL_LABEL[l.rel] || '关联',
          cipai: target.cipai,
          title: target.title,
          author: target.author,
          note: l.note || ''
        });
      }
    });
    // 双向兜底：从索引现算同调/同人，补到 6 条为止
    const sameCipai = this._index.filter((c) => c.cipai === meta.cipai && !seen[c.id]);
    const sameAuthor = this._index.filter((c) => c.author === meta.author && !seen[c.id]);
    sameCipai.concat(sameAuthor).slice(0, Math.max(0, 6 - links.length)).forEach((c) => {
      seen[c.id] = true;
      links.push({
        ci_id: c.id,
        relLabel: c.cipai === meta.cipai ? '同调' : '同人',
        cipai: c.cipai,
        title: c.title,
        author: c.author,
        note: ''
      });
    });

    const savedNote = store.get(NOTE_PREFIX + meta.id, null);
    this.setData({
      loading: false,
      ci: Object.assign({}, ci, { level: meta.level, school: meta.school }),
      links: links,
      noteText: savedNote && savedNote.text ? savedNote.text : '',
      noteSaved: !!(savedNote && savedNote.text)
    });
    wx.setNavigationBarTitle({ title: meta.cipai + '·' + (meta.title || '') });
  },

  goLinked(e) {
    wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + e.currentTarget.dataset.id });
  },

  onNoteInput(e) {
    this.setData({ noteText: e.detail.value });
  },

  onNoteSave() {
    const text = (this.data.noteText || '').trim();
    if (!text) {
      store.remove(NOTE_PREFIX + this._id);
      this.setData({ noteSaved: false });
      toast('笔记已清除');
      return;
    }
    store.set(NOTE_PREFIX + this._id, {
      text: text,
      ci_id: this._id,
      updated_at: Date.now()
    });
    this.setData({ noteSaved: true });
    toast('已保存到本机');
  },

  goNotes() {
    wx.navigateTo({ url: '/pages/notes/notes' });
  }
});
