Component({
  properties: {
    emoji: { type: String, value: '📄' },
    title: { type: String, value: '' },
    summary: { type: String, value: '' },   // 是什么（一句话）
    points: { type: Array, value: [] },     // 关键要求（2-3 条）
    type: { type: String, value: '' }       // task 页 ?type= 参数
  },
  methods: {
    onTap() {
      this.triggerEvent('tapcard', { type: this.data.type });
    }
  }
});
