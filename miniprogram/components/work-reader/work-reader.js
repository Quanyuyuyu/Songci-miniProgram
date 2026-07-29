Component({
  properties: {
    loading: { type: Boolean, value: true },
    error: { type: String, value: '' },
    work: { type: Object, value: null }
  },

  methods: {
    onPreviewImage(event) {
      const current = event.currentTarget.dataset.src;
      const work = this.data.work || {};
      const urls = work.image_urls || [];
      if (current && urls.length) wx.previewImage({ current, urls });
    },

    onSourceTap() {
      this.triggerEvent('source');
    }
  }
});
