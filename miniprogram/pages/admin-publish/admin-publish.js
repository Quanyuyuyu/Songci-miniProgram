// 一键发布全部作品到云端 content 集合（仅供管理员使用）
// 进入页面后会自动调 login 拿当前用户的 OPENID 并显示；
// 点击「一键发布全部」按钮后会并发批量调用 saveContent 云函数，
// 最终显示成功/失败条数。失败最常见原因：当前用户不在 ADMIN_OPENIDS 白名单中。
const works = require('../../services/works-bundled.js');
const cloud = require('../../services/cloud.js');

Page({
  data: {
    openid: '',
    worksCount: 0,
    progressCur: 0,
    progressTotal: 0,
    progressText: '',
    publishing: false,
    finished: false,
    successCount: 0,
    failedCount: 0,
    failedSample: [],
    debugInfo: null
  },

  onLoad() {
    this.setData({ worksCount: Object.keys(works).length });
    this.fetchOpenid();
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