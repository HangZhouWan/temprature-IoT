const API = getApp().globalData.apiBase;

Page({
  data: {
    temp_high: "",
    temp_low: "",
    hum_high: "",
    hum_low: "",
  },

  onLoad() {
    this.loadThresholds();
  },

  loadThresholds() {
    wx.request({
      url: API + "/api/thresholds",
      success: (res) => {
        const d = res.data || {};
        this.setData({
          temp_high: String(d.temp_high ?? ""),
          temp_low: String(d.temp_low ?? ""),
          hum_high: String(d.hum_high ?? ""),
          hum_low: String(d.hum_low ?? ""),
        });
      },
    });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value });
  },

  save() {
    const { temp_high, temp_low, hum_high, hum_low } = this.data;
    const body = {};
    body.temp_high = parseFloat(temp_high);
    body.temp_low = parseFloat(temp_low);
    body.hum_high = parseFloat(hum_high);
    body.hum_low = parseFloat(hum_low);

    if (isNaN(body.temp_high) || isNaN(body.temp_low) || isNaN(body.hum_high) || isNaN(body.hum_low)) {
      wx.showToast({ title: "请填写完整数值", icon: "none" });
      return;
    }

    wx.request({
      url: API + "/api/thresholds",
      method: "POST",
      header: { "content-type": "application/json" },
      data: body,
      success: () => {
        wx.showToast({ title: "保存成功", icon: "success" });
        setTimeout(() => wx.navigateBack(), 1200);
      },
      fail: () => {
        wx.showToast({ title: "保存失败", icon: "none" });
      },
    });
  },
});
