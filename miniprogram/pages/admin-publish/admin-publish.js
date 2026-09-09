// 一键发布全部作品到云端 content 集合（仅供管理员使用）
// 进入页面后会自动调 login 拿当前用户的 OPENID 并显示；
// 点击「一键发布全部」按钮后会并发批量调用 saveContent 云函数，
// 最终显示成功/失败条数。失败最常见原因：当前用户不在 ADMIN_OPENIDS 白名单中。
const works = require('../../services/works-bundled.js');
const cloud = require('../../services/cloud.js');
const { refresh } = require('../../services/data.js');

function todayISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

Page({
  data: {
    openid: '',
    worksCount: 0,
    // ===== 题壁选录 =====
    boardText: '',
    boardDate: '',
    boardAnonymous: true,
    boardPenName: '',
    boardPublishing: false,
    boardList: [],
    progressCur: 0,
    progressTotal: 0,
    progressText: '',
    publishing: false,
    finished: false,
    successCount: 0,
    failedCount: 0,
    failedSample: [],
    debugInfo: null,
    // ===== 建议收件箱 =====
    suggestions: [],
    suggestError: '',
    promoting: false
  },

  onLoad() {
    this.setData({ worksCount: Object.keys(works).length, boardDate: todayISO() });
    this.fetchOpenid();
    this.reloadBoard();
  },

  // 每次进入本页（含首次打开、以及从其他页面返回）都重新拉取建议收件箱，
  // 保证老师随时看到学生最新提交的留言。
  // 注意：此前本方法从未被调用，导致收件箱永远显示「暂无新建议」。
  onShow() {
    this.reloadSuggestions();
  },

  // ===== 题壁选录 =====
  async reloadBoard() {
    // refresh 会绕过内存缓存直连云端，保证看到的是最新已发布内容
    const raw = await refresh('board').catch(() => null);
    const messages = Array.isArray(raw && raw.messages) ? raw.messages : [];
    // 保护：本次拉到空、但上一次是有数据的，多半是云端读取异常（而非真的被清空）。
    // 此时保留旧列表并提示，避免老师误以为留言丢失而重复发布。
    if (messages.length === 0 && (this.data.boardList || []).length > 0) {
      wx.showToast({ title: '云端读取异常，显示上次结果', icon: 'none' });
      return;
    }
    this.setData({ boardList: messages });
  },

  onBoardInput(e) {
    this.setData({ boardText: e.detail.value || '' });
  },

  onBoardDate(e) {
    this.setData({ boardDate: e.detail.value || todayISO() });
  },

  onBoardAnon(e) {
    this.setData({ boardAnonymous: e.detail.value === '1' });
  },

  onBoardPen(e) {
    this.setData({ boardPenName: e.detail.value || '' });
  },

  async publishBoard() {
    if (this.data.boardPublishing) return;
    const content = (this.data.boardText || '').trim();
    if (!content) {
      wx.showToast({ title: '请先写下留言内容', icon: 'none' });
      return;
    }

    this.setData({ boardPublishing: true });
    const item = {
      id: 'b' + Date.now(),
      content: content,
      date: this.data.boardDate || todayISO(),
      anonymous: !!this.data.boardAnonymous,
      penName: this.data.boardAnonymous ? '' : (this.data.boardPenName || '').trim()
    };
    try {
      // 服务端追加：不再用 this.data.boardList.concat([item]) 整体覆盖写。
      // 客户端 boardList 可能读到包内空兜底 { messages: [] }，覆盖写会清空已有留言。
      const r = await cloud.appendBoardMessage(item);
      if (r && r.code === 0) {
        this.setData({ boardText: '', boardPenName: '' });
        await this.reloadBoard();
        wx.showToast({ title: '已题上此壁', icon: 'success' });
      } else {
        wx.showModal({
          title: '发布失败',
          content: (r && r.message) || '未知错误（403 表示当前 OPENID 不在 ADMIN_OPENIDS 白名单）',
          showCancel: false
        });
      }
    } catch (e) {
      wx.showModal({
        title: '发布失败',
        content: (e && e.errMsg) || String(e),
        showCancel: false
      });
    }
    this.setData({ boardPublishing: false });
  },

  async removeBoardItem(e) {
    const id = e.currentTarget.dataset.id;
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '撤下这条留言？',
        content: '撤下后学生端题壁页将不再显示',
        success: (r) => resolve(!!r.confirm),
        fail: () => resolve(false)
      });
    });
    if (!confirmed) return;

    try {
      // 服务端按 id 过滤后写回，同样避免本地列表为空时整体覆盖清空题壁。
      const r = await cloud.removeBoardMessage(id);
      if (r && r.code === 0) {
        await this.reloadBoard();
        wx.showToast({ title: '已撤下', icon: 'success' });
      } else {
        wx.showToast({ title: (r && r.message) || '操作失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  // ===== 建议收件箱（读取学生通过自建窗口直存的 suggestions）=====
  async reloadSuggestions() {
    try {
      const r = await cloud.listSuggestions();
      if (r && r.code === 0) {
        const list = (r.list || []).map((s) => ({
          _id: s._id,
          content: s.content,
          nameText: s.anonymous ? '佚名' : (s.penName || '自动雅号'),
          dateText: s.date || '',
          // ↓ 必须原样保留这三个原始字段：promoteSuggestion（题上此壁）依赖它们
          //   写回题壁。此前只映射了展示用的 nameText/dateText，导致署名(penName)、
          //   匿名标记(anonymous)、日期(date) 全部丢失，留言被写成另一种作者名。
          anonymous: !!s.anonymous,
          penName: s.penName || '',
          date: s.date || ''
        }));
        this.setData({ suggestions: list, suggestError: '' });
        return;
      }
      // 403 = 当前微信不在管理员白名单；其余为云端异常——都要显式提示，
      // 不能静默显示「暂无新建议」，否则无法区分「没数据」和「没权限」。
      this.setData({
        suggestions: [],
        suggestError: (r && r.message)
          ? ('读取失败：' + r.message)
          : '读取失败：云端未返回结果'
      });
    } catch (e) {
      this.setData({
        suggestions: [],
        suggestError: '读取失败：' + ((e && e.errMsg) || String(e))
      });
    }
  },

  async removeSuggestion(e) {
    const id = e.currentTarget.dataset.id;
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '删除这条建议？',
        content: '删除后不可恢复',
        success: (r) => resolve(!!r.confirm),
        fail: () => resolve(false)
      });
    });
    if (!confirmed) return;
    try {
      const r = await cloud.removeSuggestion(id);
      if (r && r.code === 0) {
        await this.reloadSuggestions();
        wx.showToast({ title: '已删除', icon: 'success' });
      } else {
        wx.showToast({ title: (r && r.message) || '删除失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '删除失败', icon: 'none' });
    }
  },

  async promoteSuggestion(e) {
    if (this.data.promoting) return;   // 防连点：避免并发两次覆盖写
    const id = e.currentTarget.dataset.id;
    const sg = (this.data.suggestions || []).find((s) => s._id === id);
    if (!sg) return;

    this.setData({ promoting: true });
    try {
      const item = {
        id: 'b' + Date.now(),
        content: sg.content,
        date: sg.date || todayISO(),
        anonymous: !!sg.anonymous,
        penName: sg.anonymous ? '' : (sg.penName || '')
      };
      // 服务端追加：由云函数读取题壁真实内容后追加再写回。
      // 不再由客户端拼 boardList 整体覆盖——客户端一旦读到「空兜底」就会清空已有留言。
      const r = await cloud.appendBoardMessage(item);
      if (r && r.code === 0) {
        await this.reloadBoard();
        await this.removeSuggestionById(id);
        wx.showToast({ title: '已题上此壁', icon: 'success' });
      } else {
        wx.showToast({ title: (r && r.message) || '发布失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '发布失败', icon: 'none' });
    }
    this.setData({ promoting: false });
  },

  async removeSuggestionById(id) {
    try {
      await cloud.removeSuggestion(id);
      await this.reloadSuggestions();
    } catch (e) { /* 忽略，promote 成功后列表已刷新 */ }
  },

  async fetchOpenid() {
    try {
      const r = await cloud.callFunction('login', {});
      // login 函数返回 { OPENID, APPID, UNIONID }
      const oid = r.OPENID || r.openid || '';
      this.setData({ openid: oid });
    } catch (e) {
      this.setData({ openid: '获取失败：' + (e && e.errMsg ? e.errMsg : String(e)) });
    }
  },

  copyOpenid() {
    if (!this.data.openid) return;
    wx.setClipboardData({
      data: this.data.openid,
      success: () => wx.showToast({ title: '已复制 OPENID', icon: 'none' })
    });
  },

  async startPublish() {
    if (this.data.publishing) return;
    const ids = Object.keys(works);
    if (ids.length === 0) {
      wx.showToast({ title: 'works-bundled 为空', icon: 'none' });
      return;
    }
    this.setData({
      publishing: true,
      finished: false,
      progressCur: 0,
      progressTotal: ids.length,
      progressText: '准备中…',
      successCount: 0,
      failedCount: 0,
      failedSample: []
    });

    const BATCH = 5;
    let success = 0;
    let failed = [];
    for (let i = 0; i < ids.length; i += BATCH) {
      const batch = ids.slice(i, i + BATCH);
      const results = await Promise.all(batch.map(async (id) => {
        try {
          const r = await cloud.callFunction('saveContent', { key: 'work__' + id, data: works[id] });
          if (r && r.code === 0) return { ok: true, id };
          return { ok: false, id, err: (r && r.message) || '未知返回', debug: r && r.debug };
        } catch (e) {
          return { ok: false, id, err: (e && e.errMsg) || String(e) };
        }
      }));
      for (const r of results) {
        if (r.ok) success += 1;
        else failed.push(r);
      }
      const done = Math.min(i + BATCH, ids.length);
      this.setData({
        progressCur: done,
        progressText: `已处理 ${done}/${ids.length}` + (failed.length ? `，失败 ${failed.length}` : '')
      });
    }

    const firstFail = failed[0];
    const failedSample = failed.slice(0, 3).map((f) => f.id + '（' + f.err + '）');
    const debugInfo = firstFail && firstFail.debug ? firstFail.debug : null;
    this.setData({
      publishing: false,
      finished: true,
      successCount: success,
      failedCount: failed.length,
      failedSample: failedSample,
      debugInfo: debugInfo
    });

    let hint = '';
    if (failed.length === 0) {
      hint = '全部作品已成功发到云端，可在小程序任意页面试读。';
    } else if (firstFail && /403|权限|OPENID/i.test(firstFail.err)) {
      if (debugInfo && debugInfo.yourOpenid) {
        hint = '云函数看到的 OPENID：\n' + debugInfo.yourOpenid + '\n\n云函数环境变量里的白名单：\n' + (debugInfo.configuredAdmins.join(' / ') || '(空)') + '\n\n两者必须完全一致（每个字符都不能差）。请复制上方「云函数看到的 OPENID」，覆盖环境变量里的值，再右键上传并部署 saveContent。';
      } else {
        hint = '请把上方 OPENID 复制给项目负责人加入白名单后再试。';
      }
    } else {
      hint = '失败原因见下。请检查网络/云函数状态后重试。';
    }
    wx.showModal({
      title: `发布完成：成功 ${success}，失败 ${failed.length}`,
      content: hint,
      showCancel: false,
      confirmText: '好的'
    });
  }
});