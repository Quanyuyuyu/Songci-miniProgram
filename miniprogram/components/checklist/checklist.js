// 可勾选自检清单：勾选状态仅存本机（不具凭证效力）
const store = require('../../utils/store.js');

Component({
  properties: {
    items: { type: Array, value: [] },  // ["两张自己拍摄的照片", ...]
    storeKey: { type: String, value: '' }
  },
  data: { checked: [] },
  observers: {
    'items, storeKey': function (items, storeKey) {
      if (storeKey) {
        const saved = store.get(storeKey, []);
        this.setData({ checked: Array.isArray(saved) ? saved : [] });
      }
    }
  },
  methods: {
    onToggle(e) {
      const idx = e.currentTarget.dataset.index;
      const checked = this.data.checked.slice();
      const pos = checked.indexOf(idx);
      if (pos >= 0) checked.splice(pos, 1); else checked.push(idx);
      this.setData({ checked });
      if (this.data.storeKey) store.set(this.data.storeKey, checked);
    }
  }
});
