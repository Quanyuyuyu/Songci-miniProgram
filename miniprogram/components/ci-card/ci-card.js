Component({
  properties: {
    item: { type: Object, value: {} },   // {id,title,author,cipai,first_line,themes,level,lesson}
    showLesson: { type: Boolean, value: false }
  },
  methods: {
    onTap() {
      const id = this.data.item.id;
      if (id) wx.navigateTo({ url: '/pages/ci-detail/ci-detail?id=' + id });
    }
  }
});
