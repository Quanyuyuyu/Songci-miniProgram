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

function getAdminOpenids() {
  const raw = process.env.ADMIN_OPENIDS || '';
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
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
  // ===== 删除模式（event.delete === true）=====
  // 用于把已发布到云端的整篇文档移除（作品下架）。云端文档优先级高于包内兜底，
  // 作品从包内删除后必须同步下架云端，否则小程序仍会显示旧内容。
  // 放在 data 校验之前，因为删除不需要 data；文档不存在时也视为「已下架」返回成功。
  if (event.delete === true) {
    try {
      await db.collection('content').doc(key).remove();
      return { code: 0, message: 'ok', key, deleted: true };
    } catch (e) {
      const msg = String(e);
      if (msg.indexOf('-502005') >= 0 || /not exist|does not exist/i.test(msg)) {
        return { code: 0, message: 'ok（云端本无此文档）', key, deleted: false };
      }
      return { code: 500, message: msg };
    }
  }

  if (!data || typeof data !== 'object') {
    return { code: 400, message: 'data 缺失或格式错误' };
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
