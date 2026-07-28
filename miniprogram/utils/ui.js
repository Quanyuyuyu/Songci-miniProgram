// UI 辅助：错误文案、toast、复制
function errorReason(err) {
  if (!err) return '网络异常，请稍后重试';
  if (err.code === 'EMPTY') return err.reason || '暂未收录，陆续收录中';
  if (err.code === 'OFFLINE_CACHE') return '当前为离线缓存内容';
  return '网络异常，请检查本地数据服务是否已启动';
}

function toast(title) {
  wx.showToast({ title: title, icon: 'none', duration: 1800 });
}

function copyText(text, tip) {
  wx.setClipboardData({
    data: text,
    success: () => toast(tip || '已复制')
  });
}

module.exports = { errorReason, toast, copyText };
