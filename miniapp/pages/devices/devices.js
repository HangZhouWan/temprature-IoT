const API = getApp().globalData.apiBase;

Page({
  data: {
    devices: [],
  },

  onLoad() {
    this.loadDevices();
  },

  onShow() {
    this.timer = setInterval(() => this.loadDevices(), 30000);
  },

  onHide() {
    clearInterval(this.timer);
  },

  loadDevices() {
    Promise.all([
      new Promise((resolve, reject) => {
        wx.request({
          url: API + "/api/devices/status",
          success: (res) => resolve(res.data || []),
          fail: reject,
        });
      }),
      new Promise((resolve) => {
        wx.request({
          url: API + "/api/device-names",
          success: (res) => resolve(res.data || {}),
          fail: () => resolve({}),
        });
      }),
    ]).then(([list, names]) => {
      const devices = list.map((d) => Object.assign({}, d, {
        displayName: names[d.device_id] || d.device_id,
        tempStr: d.temp != null ? d.temp.toFixed(1) + "°C" : "--",
        humStr: d.hum != null ? d.hum.toFixed(1) + "%" : "--",
      }));
      devices.sort(function(a, b) {
        if (a.is_new !== b.is_new) return a.is_new ? -1 : 1;
        return (b.last_seen || "").localeCompare(a.last_seen || "");
      });
      this.setData({ devices });
    }).catch(() => {
      wx.showToast({ title: "加载失败", icon: "none" });
    });
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: "/pages/detail/detail?device_id=" + id });
  },
});
