// 云函数 submitWork：学生投稿入口，写入 works_submissions 集合（status=pending）
// 说明：
//  - 云函数以管理端权限写入，不受集合权限规则限制，学生端可正常提交。
//  - 集合 works_submissions 权限建议设为「仅管理端可读写」，投稿对其他学生不可见。
//  - ⚠️ 个人主体小程序若暴露「投稿/表单收集」能力，审核可能以「涉及平台未允许内容」
//    驳回；此时请用「教师代录入」：学生把作品发给老师，老师用 saveContent 发布。
//  - 若未来升级为「企业/组织主体」，即可开放学生直投，本函数无需改动。
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  const { workId, title, formTag, term, sections, images } = event;

  if (!workId || !title) {
    return { code: 400, message: '作品信息不完整（缺少 workId 或 title）' };
  }

  try {
    const res = await db.collection('works_submissions').add({
      data: {
        workId,
        title,
        formTag: formTag || '',
        term: term || '',
        sections: sections || [],
        images: images || [],
        status: 'pending',
        _openid: OPENID,
        createdAt: db.serverDate()
      }
    });
    return { code: 0, message: '已提交，待审核', id: res._id };
  } catch (e) {
    return { code: 500, message: String(e) };
  }
};
