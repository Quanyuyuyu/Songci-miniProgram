// ============================================================
// 数据层唯一入口：getData(type, key)
// 全项目禁止在页面中直接 wx.request 或 require json 文件
// 调用链：内存缓存 → inflight 并发去重 → wx.request
//         失败降级：storage 旧缓存 → fallback 内联兜底 → reject
// ============================================================
const { BASE_URL, DATA_VERSION, CACHE_TTL } = require('../config.js');
const registry = require('./registry.js');
const fallback = require('./fallback.js');
const store = require('../utils/store.js');
const { DATA_CACHE_PREFIX } = require('../utils/constants.js');

const memCache = {};    // { cacheKey: data }
const inflight = {};    // { cacheKey: Promise }

function cacheKey(type, key) {
  return key ? `${type}__${key}` : type;
}

function storageKey(type, key) {
  return DATA_CACHE_PREFIX + (key ? `${type}_${key}` : type);
}

function resolveUrl(type, key) {
  const fn = registry[type];
  if (!fn) return null;
  return BASE_URL + fn(key);
}

function requestJson(url) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: url,
      method: 'GET',
      dataType: 'json',
      timeout: 8000,
      success: (res) => {
        if (res.statusCode === 200 && res.data && typeof res.data === 'object') {
          resolve(res.data);
        } else {
          reject({ code: 'HTTP_' + res.statusCode });
        }
      },
      fail: () => reject({ code: 'NETWORK' })
    });
  });
}

/**
 * 读取数据
 * @param {string} type  registry 中注册的类型
 * @param {string} [key] 详情类数据的标识（如 ci id、学期 id）
 * @returns {Promise<object>} 远端 JSON 对象
 * reject: {code:'EMPTY', reason} 数据不存在（页面应渲染空态）
 *         {code:'NETWORK'|'HTTP_xxx'} 网络错误且无缓存无兜底
 */
function getData(type, key) {
  const ck = cacheKey(type, key);
  if (memCache[ck]) return Promise.resolve(memCache[ck]);
  if (inflight[ck]) return inflight[ck];

  const url = resolveUrl(type, key);
  if (!url) {
    return Promise.reject({ code: 'EMPTY', reason: '数据类型未注册：' + type });
  }

  const done = () => { delete inflight[ck]; };
  const p = requestJson(url)
    .then((data) => {
      memCache[ck] = data;
      store.setCache(storageKey(type, key), data, CACHE_TTL, DATA_VERSION);
      done();
      return data;
    })
    .catch((err) => {
      // 降级 1：storage 旧缓存
      const cached = store.getCache(storageKey(type, key), DATA_VERSION);
      if (cached) {
        memCache[ck] = cached;
        done();
        return cached;
      }
      // 降级 2：内联兜底（仅 course / weeks）
      if (!key && fallback[type]) {
        done();
        return fallback[type];
      }
      done();
      // 降级 3：404 视为「未收录」空态，其余为网络错误
      if (err && err.code === 'HTTP_404') {
        throw { code: 'EMPTY', reason: '暂未收录，陆续收录中' };
      }
      throw { code: (err && err.code) || 'NETWORK' };
    });

  inflight[ck] = p;
  return p;
}

/** 后台静默刷新（忽略缓存直接拉取，失败不打扰） */
function refresh(type, key) {
  const ck = cacheKey(type, key);
  delete memCache[ck];
  return getData(type, key).catch(() => null);
}

module.exports = { getData, refresh };
