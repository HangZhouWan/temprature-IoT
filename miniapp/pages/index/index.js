const API = getApp().globalData.apiBase;

Page({
  data: {
    mode: "list", // list | map
    thresholds: {},
    allDevices: [],
    alerts: [],
    counts: { highTemp: 0, lowTemp: 0, highHum: 0, lowHum: 0, offline: 0 },
    markers: [],
    centerLat: 39.9042,
    centerLng: 116.4074,
  },

  onLoad() {
    this.refresh();
  },

  onShow() {
    this.timer = setInterval(() => this.refresh(), 30000);
  },

  onHide() {
    clearInterval(this.timer);
  },

  refresh() {
    Promise.all([this.fetchStatus(), this.fetchThresholds(), this.fetchNames()]).then(
      ([devices, thresholds, names]) => {
        const formatted = devices.map((d) => ({
          ...d,
          displayName: names[d.device_id] || d.device_id,
          tempStr: d.temp != null ? d.temp.toFixed(1) + "°C" : "--",
          humStr: d.hum != null ? d.hum.toFixed(1) + "%" : "--",
        }));
        this.setData({ thresholds, allDevices: formatted });
        this.buildAlerts(formatted, thresholds);
        this.buildMarkers(formatted);
      }
    );
  },

  fetchStatus() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + "/api/devices/status",
        success: (res) => resolve(res.data || []),
        fail: reject,
      });
    });
  },

  fetchThresholds() {
    return new Promise((resolve) => {
      wx.request({
        url: API + "/api/thresholds",
        success: (res) => resolve(res.data || {}),
        fail: () => resolve({}),
      });
    });
  },

  fetchNames() {
    return new Promise((resolve) => {
      wx.request({
        url: API + "/api/device-names",
        success: (res) => resolve(res.data || {}),
        fail: () => resolve({}),
      });
    });
  },

  buildAlerts(devices, thresholds) {
    const counts = { highTemp: 0, lowTemp: 0, highHum: 0, lowHum: 0, offline: 0 };
    const alerts = [];

    devices.forEach((d) => {
      if (d.status === "offline") {
        counts.offline++;
        alerts.push({ ...d, alertType: "offline", alertLabel: "离线", alertClass: "offline" });
        return;
      }
      if (d.status === "warning") {
        if (d.temp != null && thresholds.temp_high != null && d.temp > thresholds.temp_high) {
          counts.highTemp++;
          alerts.push({ ...d, alertType: "highTemp", alertLabel: "温度偏高", alertClass: "high" });
        } else if (d.temp != null && thresholds.temp_low != null && d.temp < thresholds.temp_low) {
          counts.lowTemp++;
          alerts.push({ ...d, alertType: "lowTemp", alertLabel: "温度偏低", alertClass: "low" });
        } else if (d.hum != null && thresholds.hum_high != null && d.hum > thresholds.hum_high) {
          counts.highHum++;
          alerts.push({ ...d, alertType: "highHum", alertLabel: "湿度过高", alertClass: "high" });
        } else if (d.hum != null && thresholds.hum_low != null && d.hum < thresholds.hum_low) {
          counts.lowHum++;
          alerts.push({ ...d, alertType: "lowHum", alertLabel: "湿度过低", alertClass: "low" });
        }
      }
    });

    this.setData({ alerts, counts });
  },

  buildMarkers(devices) {
    const markers = [];
    const defaultLat = 39.9042;
    const defaultLng = 116.4074;
    let sumLat = 0, sumLng = 0, cnt = 0;

    devices.forEach((d, idx) => {
      // 没有坐标时散布在默认中心周围
      const lat = (d.lat != null) ? d.lat : defaultLat + (idx * 0.003 - 0.012);
      const lng = (d.lng != null) ? d.lng : defaultLng + (idx * 0.004 - 0.015);
      sumLat += lat;
      sumLng += lng;
      cnt++;

      const tempStr = d.temp != null ? d.temp.toFixed(1) + "°C" : "--";
      const humStr = d.hum != null ? d.hum.toFixed(1) + "%" : "--";
      const statusColor = d.status === "warning" ? "#ef4444" : d.status === "offline" ? "#94a3b8" : "#22c55e";

      markers.push({
        id: idx,
        latitude: lat,
        longitude: lng,
        callout: {
          content: (d.displayName || d.device_id) + "\n" + tempStr + "  " + humStr,
          fontSize: 12,
          borderRadius: 8,
          padding: 8,
          display: "BYCLICK",
          bgColor: d.status === "warning" ? "#fff7ed" : d.status === "offline" ? "#f1f5f9" : "#f0fdf4",
        },
        label: {
          content: d.temp != null ? d.temp.toFixed(1) + "°" : "?",
          fontSize: 11,
          color: "#ffffff",
          bgColor: statusColor,
          borderRadius: 10,
          padding: 4,
          anchorX: 0,
          anchorY: -25,
        },
      });
    });

    if (cnt > 0) {
      this.setData({
        markers,
        centerLat: sumLat / cnt,
        centerLng: sumLng / cnt,
      });
    } else {
      this.setData({ markers: [] });
    }
  },

  switchMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode });
  },

  moveToMyLocation() {
    wx.getLocation({
      type: "gcj02",
      success: (res) => {
        this.setData({
          centerLat: res.latitude,
          centerLng: res.longitude,
        });
      },
      fail: () => {
        wx.showToast({ title: "获取位置失败", icon: "none" });
      },
    });
  },

  onMarkerTap(e) {
    const marker = this.data.markers[e.detail.markerId];
    if (marker) {
      const device = this.data.allDevices[marker.id];
      if (device) {
        wx.navigateTo({ url: "/pages/detail/detail?device_id=" + device.device_id });
      }
    }
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: "/pages/detail/detail?device_id=" + id });
  },

  goSettings() {
    wx.navigateTo({ url: "/pages/settings/settings" });
  },
});
