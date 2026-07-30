// ============================================================
// 数据层唯一入口：getData(type, key)
// 全项目禁止在页面中直接 wx.request 或 require json 文件
// 调用链（USE_CLOUD=false 本地开发）：内存缓存 → inflight 并发去重 → wx.request
//         失败降级：storage 旧缓存 → 打包数据兜底 → reject
// 调用链（USE_CLOUD=true 云端模式）：内存缓存 → 云数据库 content 集合
//         → 包内兜底 → reject（不再请求本地 dev 服务）
// ============================================================
const { BASE_URL, DATA_VERSION, CACHE_TTL, USE_CLOUD } = require('../config.js');
const registry = require('./registry.js');
const fallback = require('./fallback.js');
const store = require('../utils/store.js');
const { DATA_CACHE_PREFIX } = require('../utils/constants.js');
const cloud = require('./cloud.js');

const memCache = {};    // { cacheKey: data }
const inflight = {};    // { cacheKey: Promise }
const BUNDLED_FIRST = {
  course: true,
  weeks: true,
  schedule: true,
  'ci-index': true,
  books: true,
  'semester__26spring': true
};

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

function isUsableData(type, data) {
  if (!data || typeof data !== 'object') return false;
  if (type === 'course') return !!(data.course && data.course.name);
  if (type === 'weeks') return Array.isArray(data.weeks) && data.weeks.length > 0;
  if (type === 'schedule') return Array.isArray(data.weeks) && data.weeks.length > 0;
  if (type === 'ci-index') return Array.isArray(data.list) && data.list.length > 0;
  if (type === 'semester') return !!(data.tasks && data.discussion);
  if (type === 'archive-index') return Array.isArray(data.terms) && data.terms.length > 0;
  if (type === 'archive') return Array.isArray(data.photo) && Array.isArray(data.essay);
  if (type === 'cipai') return Array.isArray(data.list) && data.list.length > 0;
  if (type === 'maps') return Array.isArray(data.timeline) && data.timeline.length > 0;
  if (type === 'ci-detail') return !!(data.id && data.title);
  return true;
}

function bundledFor(type, key) {
  return fallback[cacheKey(type, key)];
}

/**
 * 读取数据
 * @param {string} type  registry 中注册的类型
 * @param {string} [key] 详情类数据的标识（如 ci id、学期 id）
 * @returns {Promise<object>}
 * reject: {code:'EMPTY', reason} 数据不存在（页面应渲染空态）
 *         {code:'NETWORK'|'HTTP_xxx'} 网络错误且无缓存无兜底
 */
async function getData(type, key) {
  const ck = cacheKey(type, key);
  if (memCache[ck]) return memCache[ck];
  if (inflight[ck]) return inflight[ck];

  const url = resolveUrl(type, key);
  if (!url) {
    return Promise.reject({ code: 'EMPTY', reason: '数据类型未注册：' + type });
  }

  // ===== 云端覆盖层（USE_CLOUD=true 时生效）=====
  // 教师通过 saveContent 云函数发布的内容存于云数据库 content 集合，
  // _id 即 cacheKey（如 work__essay-2）。云端数据优先级高于本地打包，
  // 实现「改内容免重新提审」。
  if (USE_CLOUD) {
    try {
      const cdata = await cloud.readContent(ck);
      if (isUsableData(type, cdata)) {
        memCache[ck] = cdata;
        return cdata;
      }
    } catch (e) {
      console.warn('[cloud] readContent miss', ck, e);
    }
    // 云中无此文档 → 回退包内兜底（生产环境不再请求本地 dev 服务）
    const lf = bundledFor(type, key);
    if (isUsableData(type, lf)) {
      memCache[ck] = lf;
      return lf;
    }
    return Promise.reject({ code: 'EMPTY', reason: '暂未收录，陆续收录中' });
  }

  // ===== 本地开发模式（USE_CLOUD=false）：走 wx.request + 兜底 =====
  // 核心课程数据随小程序打包发布，优先使用本地完整副本。
  const localFallback = bundledFor(type, key);
  if (BUNDLED_FIRST[ck] && isUsableData(type, localFallback)) {
    memCache[ck] = localFallback;
    return Promise.resolve(localFallback);
  }

  const done = () => { delete inflight[ck]; };
  const p = requestJson(url)
    .then((data) => {
      if (!isUsableData(type, data)) throw { code: 'INVALID_DATA' };
      memCache[ck] = data;
      store.setCache(storageKey(type, key), data, CACHE_TTL, DATA_VERSION);
      done();
      return data;
    })
    .catch((err) => {
      // 降级 1：storage 旧缓存
      const cached = store.getCache(storageKey(type, key), DATA_VERSION);
      if (isUsableData(type, cached)) {
        memCache[ck] = cached;
        done();
        return cached;
      }
      // 降级 2：包内兜底数据
      if (isUsableData(type, localFallback)) {
        done();
        return localFallback;
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
