const { getData } = require('../../services/data.js');
const { errorReason } = require('../../utils/ui.js');

Page({
  data: {
    loading: true,
    error: '',
    course: null,
    grade: [],
    effortList: [],
    rules: null,
    weeks: [],
    periods: [],
    weeksNotice: '',
    disclaimer: ''
  },

  onLoad() {
    Promise.all([
      getData('course'),
      getData('weeks')
    ]).then(([course, weeks]) => {
      this.setData({
        loading: false,
        course: course.course,
        grade: course.grade || [],
        effortList: course.effort_list || [],
        rules: course.rules || null,
        disclaimer: course.disclaimer || '',
        weeks: weeks.weeks || [],
        periods: weeks.periods || [],
        weeksNotice: weeks.notice || ''
      });
    }).catch((err) => {
      this.setData({ loading: false, error: errorReason(err) });
    });
  },

  gradeBarStyle(percent) {
    return 'width:' + percent + '%;';
  },

  onShareAppMessage() {
    return { title: '宋词导读·课程助手', path: '/pages/overview/overview' };
  }
});
