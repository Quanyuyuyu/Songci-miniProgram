// 本地 storage key 清单（仅本机、不回传、不具凭证效力）
module.exports = {
  CHK_PHOTO: 'chk_photo',        // 拍照配词自检清单勾选状态
  CHK_FINAL: 'chk_final',        // 期末学术规范自检勾选状态
  NOTE_PREFIX: 'note_',          // 私人笔记：note_{ci_id}
  DATA_CACHE_PREFIX: 'cache_'    // 数据层离线缓存：cache_{type}_{key}
};
