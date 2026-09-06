// 题壁 · 留言展示页（只读）
//
// 数据流向：
//   学生落笔 → 微信官方意见反馈（open-type="feedback"）→ mp 后台「用户反馈」
//   教师选录 → 管理后台「题壁选录」→ saveContent 云函数 → 云数据库 content 集合 _id='board'
//   本页读取 → getData('board')（云端优先，回退包内兜底）
//
// 合规说明：学生提交的内容不进入本项目数据库，由微信平台承载；
// 公开展示的内容均由教师以编辑身份发布，规避个人主体 UGC 类目风险。
const { getData, refresh } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');
const { normalize, PEN_NAMES } = require('../../utils/board.js');
const { ENABLE_SELF_SUGGEST } = require('../../config.js');
const cloud = require('../../services/cloud.js');

Page({
  data: {
    loading: true,
    error: '',
    messages: [],
    // ===== 自建建议窗口（见 config.ENABLE_SELF_SUGGEST）=====
    selfSuggest: ENABLE_SELF_SUGGEST,
    showCompose: false,
    draft: '',
    draftLen: 0,
    anon: true,
    penName: '',
    submitting: false
  },

  onLoad() {
    this.loadBoard();
  },

  async loadBoard() {
    try {
      const raw = await getData('board');
      this.setData({ loading: false, error: '', messages: normalize(raw) });
    } catch (err) {
      this.setData({ loading: false, error: errorReason(err), messages: [] });
    }
  },

  async onPullDownRefresh() {
    const raw = await refresh('board');
    if (raw) {
      this.setData({ loading: false, error: '', messages: normalize(raw) });
    }
    wx.stopPullDownRefresh();
  },

  // ===== 自建建议窗口（ENABLE_SELF_SUGGEST=true 时启用）=====
  openCompose() {
    this.setData({ showCompose: true, draft: '', draftLen: 0, anon: true, penName: '', submitting: false });
  },
  closeCompose() {
    if (this.data.submitting) return;
    this.setData({ showCompose: false });
  },
  noop() {},
  onDraftInput(e) {
    const v = e.detail.value || '';
    this.setData({ draft: v, draftLen: v.length });
  },
  onAnonChange(e) {
    this.setData({ anon: !!e.detail.value });
  },
  onPenInput(e) {
    this.setData({ penName: e.detail.value || '' });
  },
  async submitSuggestion() {
    if (this.data.submitting) return;
    const content = (this.data.draft || '').trim();
    if (!content) {
      wx.showToast({ title: '写点什么再捎话吧', icon: 'none' });
      return;
    }
    let penName = (this.data.penName || '').trim();
    if (!this.data.anon && !penName) {
      penName = PEN_NAMES[Date.now() % PEN_NAMES.length];
    }
    this.setData({ submitting: true });
    try {
      const r = await cloud.submitSuggestion({
        content: content,
        anonymous: this.data.anon,
        penName: penName
      });
      if (r && r.code === 0) {
        wx.showToast({ title: '已收到你的建议', icon: 'success' });
        this.setData({ showCompose: false, draft: '', draftLen: 0, penName: '' });
      } else {
        wx.showToast({ title: (r && r.message) || '送达失败，请稍后再试', icon: 'none' });
      }
    } catch (err) {
      const msg = (err && err.errCode === 'NO_CLOUD')
        ? '当前为本地模式，建议暂无法送达'
        : '送达失败，请稍后再试';
      wx.showToast({ title: msg, icon: 'none' });
    }
    this.setData({ submitting: false });
  },

  onShareAppMessage() {
    return { title: '题壁 · 宋词导读', path: '/pages/board/board' };
  }
});
