// ============================================================
// 云开发封装层：数据库读取 / 云函数调用 / 云存储上传与临时链接
// 仅当 config.USE_CLOUD === true 且基础库支持 wx.cloud 时生效
// ============================================================
const { USE_CLOUD, CLOUD_ENV } = require('../config.js');

function db() {
  if (!USE_CLOUD || !wx.cloud) return null;
  return wx.cloud.database();
}

/**
 * 读取云数据库 content 集合中的单一文档。
 * 约定：文档 _id 即 cacheKey（如 'work__essay-2'），文档结构 { _id, data, updatedAt }
 * 返回 data 字段（即页面所需的业务对象），不存在 / 无权限时返回 null。
 */
function readContent(cacheKey) {
  const database = db();
  if (!database) return Promise.resolve(null);
  return database.collection('content').doc(cacheKey).get()
    .then((res) => {
      if (res && res.data && res.data.data) return res.data.data;
      return null;
    })
    .catch((err) => {
      // -502005 = 文档不存在；其余视为无云数据，回退本地
      if (err && err.errCode === -502005) return null;
      console.warn('[cloud] readContent fail', cacheKey, err);
      return null;
    });
}

/** 调用云函数，返回 res.result */
function callFunction(name, data) {
  if (!USE_CLOUD || !wx.cloud) return Promise.reject({ code: 'NO_CLOUD' });
  return new Promise((resolve, reject) => {
    wx.cloud.callFunction({ name, data: data || {} })
      .then((res) => resolve(res.result))
      .catch((err) => reject(err));
  });
}

/** 上传文件到云存储，返回 { fileID } */
function uploadFile(cloudPath, filePath) {
  if (!USE_CLOUD || !wx.cloud) return Promise.reject({ code: 'NO_CLOUD' });
  return wx.cloud.uploadFile({ cloudPath, filePath });
}

/** 云存储 fileID → 临时 https 链接（用于分享 / 在 <image> 外使用） */
function getTempFileURL(fileID) {
  if (!USE_CLOUD || !wx.cloud) return Promise.reject({ code: 'NO_CLOUD' });
  return wx.cloud.getTempFileURL({ fileList: [fileID] })
    .then((res) => {
      const f = (res.fileList || [])[0];
      return f && f.tempFileURL ? f.tempFileURL : '';
    });
}

/**
 * 追加一条题壁留言。
 * 走云函数的 append 模式（服务端读-追加-写回），
 * 避免客户端用「空兜底列表」整体覆盖写回导致已有留言被清空。
 */
function appendBoardMessage(item) {
  return callFunction('saveContent', { key: 'board', append: true, data: { messages: [item] } });
}

/**
 * 撤下一条题壁留言。
 * 同样走服务端（云函数读-过滤-写回），避免客户端本地列表为空时整体覆盖清空题壁。
 */
function removeBoardMessage(id) {
  return callFunction('saveContent', { key: 'board', remove: true, removeId: id });
}

/** 提交建议（自建窗口）：写入云库 suggestions 集合 */
function submitSuggestion(payload) {
  return callFunction('suggestion', { action: 'submit', data: payload });
}

/** 读取建议收件箱（仅管理端） */
function listSuggestions() {
  return callFunction('suggestion', { action: 'list' });
}

/** 删除一条建议（仅管理端） */
function removeSuggestion(id) {
  return callFunction('suggestion', { action: 'remove', id });
}

module.exports = {
  isCloud: () => !!(USE_CLOUD && wx.cloud),
  readContent,
  callFunction,
  uploadFile,
  getTempFileURL,
  appendBoardMessage,
  removeBoardMessage,
  submitSuggestion,
  listSuggestions,
  removeSuggestion
};
