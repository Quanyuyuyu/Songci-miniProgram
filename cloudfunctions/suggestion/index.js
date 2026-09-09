// 云函数 suggestion：处理「建议留言窗口」的提交与教师端读取
//   action = 'submit' → 任意用户可调用，写入 suggestions 集合（不校验身份，仅做内容安全）
//   action = 'list'   → 仅 ADMIN_OPENIDS 可调用，返回建议列表
//   action = 'remove' → 仅 ADMIN_OPENIDS 可调用，按 _id 删除
//
// ⚠️ 合规提示：个人主体下「自建内容收集（评价/建议）」属社交-笔记未开放类目，提审有被驳风险。
//    若审核被驳，把 config.ENABLE_SELF_SUGGEST 改为 false 即可回退为微信官方反馈通道。
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

const PEN_NAMES = [
  '鹧鸪天', '踏莎行', '浣溪沙', '临江仙', '蝶恋花', '水调歌头',
  '念奴娇', '如梦令', '卜算子', '青玉案', '一剪梅', '满庭芳',
  '声声慢', '扬州慢'
];

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

function isAdmin() {
  const { OPENID } = cloud.getWXContext();
  return getAdminOpenids().includes(OPENID);
}

function todayISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

exports.main = async (event) => {
  const { action, data, id } = event;

  // ===== 学生端提交（任意用户可调）=====
  if (action === 'submit') {
    const content = (data && data.content ? String(data.content) : '').trim();
    if (!content) return { code: 400, message: '内容不能为空' };
    if (content.length > 300) return { code: 400, message: '内容过长（上限 300 字）' };

    const anonymous = !!(data && data.anonymous);
    let penName = (data && data.penName ? String(data.penName).trim() : '');
    if (!anonymous && !penName) {
      // 未填雅号则按时间稳定分配一个词牌名
      penName = PEN_NAMES[Date.now() % PEN_NAMES.length];
    }

    // 内容安全校验：命中违规（errCode 87014）才拦截；接口异常不阻断正常提交
    try {
      const res = await cloud.security.msgSecCheck({ content, version: 2 });
      if (res && res.errCode === 87014) {
        return { code: 400, message: '内容包含敏感信息，请修改后重试' };
      }
    } catch (e) {
      if (e && e.errCode === 87014) {
        return { code: 400, message: '内容包含敏感信息，请修改后重试' };
      }
      console.warn('[suggestion] msgSecCheck skipped:', e && e.errCode);
    }

    try {
      const result = await db.collection('suggestions').add({
        data: {
          content,
          anonymous,
          penName: anonymous ? '' : penName,
          date: todayISO(),
          status: 'pending',
          createTime: db.serverDate()
        }
      });
      return { code: 0, message: 'ok', id: result._id };
    } catch (e) {
      return { code: 500, message: String(e) };
    }
  }

  // ===== 以下动作仅管理端 =====
  if (action === 'list' || action === 'remove') {
    if (!isAdmin()) {
      return { code: 403, message: '无权限（不在 ADMIN_OPENIDS）' };
    }
    if (action === 'list') {
      try {
        const res = await db.collection('suggestions')
          .orderBy('createTime', 'desc')
          .limit(200)
          .get();
        return { code: 0, list: res.data || [] };
      } catch (e) {
        return { code: 500, message: String(e) };
      }
    }
    if (action === 'remove') {
      if (!id) return { code: 400, message: 'id 缺失' };
      try {
        await db.collection('suggestions').doc(id).remove();
        return { code: 0, message: 'ok' };
      } catch (e) {
        return { code: 500, message: String(e) };
      }
    }
  }

  return { code: 400, message: '未知 action' };
};
