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
 * 下架云端文档（整篇移除）。
 * 作品从包内删除后，若之前已发布到云端，必须同步下架，否则云端旧数据会盖住包内内容。
 * cacheKey 即 content 集合的 _id，例如 'work__photo-23'。
 */
function deleteContent(cacheKey) {
  return callFunction('saveContent', { key: cacheKey, delete: true });
}

module.exports = {
  isCloud: () => !!(USE_CLOUD && wx.cloud),
  readContent,
  callFunction,
  uploadFile,
  getTempFileURL,
  deleteContent
};
