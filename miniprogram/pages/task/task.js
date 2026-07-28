const { getData } = require('../../services/data.js');
const { errorReason, copyText } = require('../../utils/ui.js');
const { CHK_PHOTO, CHK_FINAL } = require('../../utils/constants.js');

const TITLES = {
  photo: '拍照配词',
  discussion: '讨论课展示',
  final: '期末习作'
};

const ARCHIVE_CATEGORIES = {
  photo: 'photo',
  final: 'essay'
};

Page({
  data: {
    loading: true,
    error: '',
    type: '',
    title: '',
    photo: null,
    discussion: null,
    final: null,
    chkPhotoKey: CHK_PHOTO,
    chkFinalKey: CHK_FINAL
  },

  onLoad(options) {
    const type = options.type || 'photo';
    this.setData({ type: type, title: TITLES[type] || '任务' });
    wx.setNavigationBarTitle({ title: TITLES[type] || '任务' });

    getData('semester', '26spring').then((sem) => {
      const tasks = sem.tasks || {};
      this.setData({
        loading: false,
        photo: tasks.photo || null,
        discussion: sem.discussion || null,
        final: tasks.final || null
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  onCopyNaming() {
    const f = this.data.final;
    if (f && f.naming) copyText(f.naming, '命名格式已复制');
  },

  goArchive() {
    const type = this.data.type;
    getApp().globalData.archiveEntry = {
      category: ARCHIVE_CATEGORIES[type] || 'photo',
      returnUrl: '/pages/task/task?type=' + type,
      returnLabel: '返回' + (TITLES[type] || '任务')
    };
    wx.switchTab({ url: '/pages/archive/archive' });
  },

  goNotes() {
    wx.navigateTo({ url: '/pages/notes/notes' });
  }
});
