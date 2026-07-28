Component({
  properties: {
    items: { type: Array, value: [] },   // 里程碑步骤（只有顺序，没有日期）
    note: { type: String, value: '' }    // 底部说明
  }
});
