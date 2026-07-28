const { getData } = require('../../services/data.js');
const { errorReason, toast } = require('../../utils/ui.js');

// 作品详情：完全在小程序内闭环预览
// 内容以 sections 数组呈现：{type:'h'|'p'|'quote'|'img', text|url}
// 图片类作品因 ima 图片链接带时效签名，无法持久写死，统一降级为「内容整理中」
Page({
  data: {
    loading: true,
    error: '',
    id: '',
    work: null
  },

  onLoad(options) {
    const id = options.id || '';
    this.setData({ id });
    if (!id) {
      this.setData({ loading: false, error: '缺少作品标识' });
      return;
    }
    getData('work', id)
      .then((work) => {
        this.setData({ loading: false, work });
      })
      .catch(() => {
        // 404 / 网络异常 → 视为「内容整理中」空态
        this.setData({
          loading: false,
          work: { title: '', form_tag: '', collecting: true }
        });
      });
  },

  onCopyLink() {
    const url = this.data.work && this.data.work.link;
    if (!url) return;
    wx.setClipboardData({
      data: url,
      success: () => toast('原文链接已复制，请在浏览器中打开'),
      fail: () => toast('链接复制失败')
    });
  },

  onBackHome() {
    wx.switchTab({ url: '/pages/archive/archive' });
  }
});
