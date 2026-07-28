const { getData } = require('../../services/data.js');
const { errorReason, toast } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    cards: []
  },

  onLoad() {
    getData('semester', '26spring').then((sem) => {
      const tasks = sem.tasks || {};
      const discussion = sem.discussion || {};
      const currentTheme = (discussion.themes || [])[0] || {};
      this.setData({
        loading: false,
        cards: [
          {
            emoji: '📖',
            title: '全学期阅读词目',
            type: 'reading',
            summary: '按教学周查看全部阅读篇目，每首均提供原文、简注与导读。',
            points: ['实际授课进度以当学期课堂安排为准']
          },
          {
            emoji: '📷',
            title: '拍照配词',
            type: 'photo',
            summary: tasks.photo ? tasks.photo.what : '',
            points: ['两张照片 + 两段各约 300 字', '交之前可逐项自检']
          },
          {
            emoji: '🎤',
            title: '讨论课展示',
            type: 'discussion',
            summary: currentTheme.status === 'known'
              ? currentTheme.title
              : (currentTheme.display || '新学期') + '主题尚未发布',
            points: currentTheme.status === 'known'
              ? [currentTheme.group_rule + ' · ' + currentTheme.duration, '填分组表 → 交 PPT → 课堂展示']
              : ['具体安排以课程群通知为准']
          },
          {
            emoji: '✍️',
            title: '期末习作',
            type: 'final',
            summary: tasks.final ? tasks.final.what : '',
            points: [tasks.final ? tasks.final.min_words_note : '', tasks.final ? tasks.final.late_penalty : '']
          }
        ]
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  onCardTap(e) {
    const type = e.detail.type;
    if (type === 'reading') {
      wx.navigateTo({ url: '/pages/schedule/schedule' });
    } else if (type) {
      wx.navigateTo({ url: '/pages/task/task?type=' + type });
    } else {
      toast('暂未开放');
    }
  }
});
