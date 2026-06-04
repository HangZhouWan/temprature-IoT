const API = getApp().globalData.apiBase;

Page({
  data: {
    devices: [],
    filteredDevices: [],
    filter: "",
    counts: { online: 0, offline: 0, warning: 0 },
    statusText: { online: "在线", offline: "离线", warning: "异常" },
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
    wx.request({
      url: API + "/api/devices/status",
      success: (res) => {
        const devices = (res.data || []).map((d) => ({
          ...d,
          tempStr: d.temp != null ? d.temp.toFixed(1) + "°C" : "--",
          humStr: d.hum != null ? d.hum.toFixed(1) + "%" : "--",
        }));
        const counts = { online: 0, offline: 0, warning: 0 };
        devices.forEach((d) => {
          if (counts[d.status] !== undefined) counts[d.status]++;
        });
        this.setData({ devices, counts });
        this.applyFilter();
      },
      fail: (e) => {
        console.error("加载设备失败:", e);
        wx.showToast({ title: "加载失败，请检查网络", icon: "none" });
      },
    });
  },

  onFilter(e) {
    const status = e.currentTarget.dataset.status;
    this.setData({ filter: status === this.data.filter ? "" : status });
    this.applyFilter();
  },

  applyFilter() {
    const { devices, filter } = this.data;
    const filteredDevices = filter
      ? devices.filter((d) => d.status === filter)
      : devices;
    this.setData({ filteredDevices });
  },
});
