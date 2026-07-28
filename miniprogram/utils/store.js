// wx.storage 轻封装：统一前缀、JSON 序列化、TTL
const { STORAGE_PREFIX } = require('../config.js');

function fullKey(key) {
  return STORAGE_PREFIX + key;
}

function set(key, value) {
  try {
    wx.setStorageSync(fullKey(key), value);
  } catch (e) { /* 存储满等异常静默降级 */ }
}

function get(key, defVal) {
  try {
    const v = wx.getStorageSync(fullKey(key));
    return (v === '' || v === undefined || v === null) ? defVal : v;
  } catch (e) {
    return defVal;
  }
}

function remove(key) {
  try { wx.removeStorageSync(fullKey(key)); } catch (e) {}
}

// 带 TTL 的缓存读写（供数据层使用）
function setCache(key, data, ttl, version) {
  set(key, { data: data, ts: Date.now(), ttl: ttl, version: version });
}

function getCache(key, version) {
  const rec = get(key, null);
  if (!rec || !rec.data) return null;
  if (version && rec.version !== version) return null;
  if (rec.ttl && Date.now() - rec.ts > rec.ttl) return null;
  return rec.data;
}

// 枚举前缀 key（供笔记汇总页使用）
function keysWithPrefix(prefix) {
  try {
    const info = wx.getStorageInfoSync();
    return (info.keys || []).filter(k => k.indexOf(fullKey(prefix)) === 0);
  } catch (e) {
    return [];
  }
}

function getByFullKey(k, defVal) {
  try {
    const v = wx.getStorageSync(k);
    return (v === '' || v === undefined || v === null) ? defVal : v;
  } catch (e) {
    return defVal;
  }
}

module.exports = { set, get, remove, setCache, getCache, keysWithPrefix, getByFullKey };
