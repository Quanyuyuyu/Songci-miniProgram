// 云函数 saveContent：管理端发布/更新内容到云数据库 content 集合
// 权限：仅 ADMIN_OPENIDS 白名单内的 OPENID 可调用（在云函数「配置 → 环境变量」设置）
// 调用示例（教师代录入）：
//   wx.cloud.callFunction({
//     name: 'saveContent',
//     data: { key: 'work__essay-2', data: { title:'...', term:'26Spring', form_tag:'文字', collecting:false, sections:[...] } }
//   })
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

// 内置管理员（写在代码里、随 git 走；即使环境变量被重置也不会丢）
const CODE_ADMINS = [
  'oU8V53cfJjLTL7NodQJhVKADgSgM',  // 开发者本人
  'oU8V53RRDZUJ_6ITB5k6bFo1-vfM'   // 老师
];

function getAdminOpenids() {
  const raw = process.env.ADMIN_OPENIDS || '';
  const fromEnv = raw.split(',').map((s) => s.trim()).filter(Boolean);
  // 环境变量 + 代码内置，合并去重
  const set = {};
  fromEnv.concat(CODE_ADMINS).forEach((oid) => { set[oid] = true; });
  return Object.keys(set);
}

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  const admins = getAdminOpenids();
  if (!admins.includes(OPENID)) {
    return {
      code: 403,
      message: '无发布权限（OPENID 不在 ADMIN_OPENIDS）',
      debug: {
        yourOpenid: OPENID,
        configuredAdmins: admins,
        hint: '把 yourOpenid 那整串（不含空格）完整填到 ADMIN_OPENIDS 后，再右键上传并部署 saveContent 云函数'
      }
    };
  }

  const { key, data } = event;
  // key 即 cacheKey，限制字符集防止注入/越权写其他集合
  if (!key || typeof key !== 'string' || !/^[A-Za-z0-9_:-]{1,64}$/.test(key)) {
    return { code: 400, message: 'key 非法' };
  }
  if (!data || typeof data !== 'object') {
    return { code: 400, message: 'data 缺失或格式错误' };
  }

  // ===== 追加模式（event.append === true）=====
  // 由云函数「读现有 → 追加 → 写回」，供题壁留言追加使用。
  // 必要性：客户端 board 读取失败时会回退到包内空兜底 { messages: [] }（且空数组被
  // 判定为可用），此时若由客户端做 concat 再整体覆盖写回，会把已有留言全部清空。
  // 改由服务端读取真实文档后追加，彻底避免该数据丢失风险。
  if (event.append === true) {
    try {
      const existing = await db.collection('content').doc(key).get().catch(() => null);
      const curPayload = existing && existing.data && existing.data.data;
      const cur = curPayload && Array.isArray(curPayload.messages) ? curPayload.messages : [];
      const add = Array.isArray(data.messages) ? data.messages : [];
      const next = cur.concat(add);
      await db.collection('content').doc(key).set({
        data: { data: { messages: next }, updatedAt: db.serverDate() }
      });
      return { code: 0, message: 'ok', key, count: next.length };
    } catch (e) {
      return { code: 500, message: String(e) };
    }
  }

  // ===== 撤下模式（event.remove === true）=====
  // 由云函数「读现有 → 按 id 过滤 → 写回」，供题壁撤下单条留言使用。
  // 与追加模式同理：不让客户端拿本地列表整体覆盖写，避免读到空兜底时清空题壁。
  if (event.remove === true) {
    const removeId = event.removeId;
    if (!removeId || typeof removeId !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(removeId)) {
      return { code: 400, message: 'removeId 缺失或非法' };
    }
    try {
      const existing = await db.collection('content').doc(key).get().catch(() => null);
      const curPayload = existing && existing.data && existing.data.data;
      const cur = curPayload && Array.isArray(curPayload.messages) ? curPayload.messages : [];
      const next = cur.filter((m) => m && m.id !== removeId);
      if (next.length === cur.length) {
        return { code: 404, message: '未找到该条留言（可能已被撤下或列表非最新）' };
      }
      await db.collection('content').doc(key).set({
        data: { data: { messages: next }, updatedAt: db.serverDate() }
      });
      return { code: 0, message: 'ok', key, count: next.length };
    } catch (e) {
      return { code: 500, message: String(e) };
    }
  }

  try {
    await db.collection('content').doc(key).set({
      data: { data, updatedAt: db.serverDate() }
    });
    return { code: 0, message: 'ok', key };
  } catch (e) {
    return { code: 500, message: String(e) };
  }
};
