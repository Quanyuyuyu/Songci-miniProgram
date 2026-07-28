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
      this.setData({
        loading: false,
        cards: [
          {
            emoji: '📖',
            title: '本周读哪首词？',
            type: 'intensive',
            summary: tasks.intensive ? tasks.intensive.what : '',
            points: [tasks.intensive ? tasks.intensive.rule_text : '']
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
            summary: sem.discussion ? sem.discussion.theme_title : '待教师公布',
            points: [
              (sem.discussion ? sem.discussion.group_rule : '') + ' · ' + (sem.discussion ? sem.discussion.duration : ''),
              '填分组表 → 交 PPT → 课堂展示'
            ]
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
    if (type === 'intensive') {
      wx.navigateTo({ url: '/pages/schedule/schedule' });
    } else if (type) {
      wx.navigateTo({ url: '/pages/task/task?type=' + type });
    } else {
      toast('暂未开放');
    }
  }
});
