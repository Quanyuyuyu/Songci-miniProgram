// 云函数 login：返回调用者身份（OPENID 等）
// 用途：获取教师/管理端的 OPENID，用于配置 saveContent 的白名单 ADMIN_OPENIDS
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

exports.main = async (event, context) => {
  const { OPENID, APPID, UNIONID } = cloud.getWXContext();
  return {
    openid: OPENID,
    appid: APPID,
    unionid: UNIONID || ''
  };
};
