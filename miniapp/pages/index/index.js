const API = getApp().globalData.apiBase;

Page({
  data: {
    temp: "--",
    hum: "--",
    deviceCount: 0,
    updateTime: "",
    deviceList: [],
    currentDevice: "",
    hourOptions: ["1", "6", "24", "72", "168"],
    currentHours: "24",
    recentData: [],
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.timer = setInterval(() => this.loadData(), 60000);
  },

  onHide() {
    clearInterval(this.timer);
  },

  async loadData() {
    const { currentDevice, currentHours } = this.data;
    try {
      const [latest, devices, history] = await Promise.all([
        this.fetchLatest(),
        this.fetchDevices(),
        this.fetchHistory(currentDevice, currentHours),
      ]);

      const d = latest.find(
        (r) => !currentDevice || r.device_id === currentDevice
      ) || latest[0] || {};

      const deviceList = devices.map((d) => ({
        name: d.device_id,
        value: d.device_id,
      }));

      this.setData({
        temp: d.temp != null ? d.temp.toFixed(1) : "--",
        hum: d.hum != null ? d.hum.toFixed(1) : "--",
        deviceCount: devices.length,
        updateTime: new Date().toLocaleTimeString(),
        deviceList,
        recentData: history.slice(-20).reverse(),
      });

      this.drawChart(history);
    } catch (e) {
      console.error("加载失败:", e);
    }
  },

  fetchLatest() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + "/api/latest",
        success: (res) => resolve(res.data),
        fail: reject,
      });
    });
  },

  fetchDevices() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + "/api/devices",
        success: (res) => resolve(res.data),
        fail: reject,
      });
    });
  },

  fetchHistory(device, hours) {
    let url = API + "/api/history?hours=" + hours;
    if (device) url += "&device=" + device;
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        success: (res) => resolve(res.data),
        fail: reject,
      });
    });
  },

  onDeviceChange(e) {
    const item = this.data.deviceList[e.detail.value];
    this.setData({ currentDevice: item ? item.value : "" });
    this.loadData();
  },

  onHoursChange(e) {
    this.setData({ currentHours: this.data.hourOptions[e.detail.value] });
    this.loadData();
  },

  // Canvas 2D 绘制温湿度折线图
  drawChart(data) {
    const query = wx.createSelectorQuery();
    query
      .select("#chartCanvas")
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0]) return;
        const canvas = res[0].node;
        const ctx = canvas.getContext("2d");
        const dpr = wx.getSystemInfoSync().pixelRatio;
        const w = res[0].width;
        const h = res[0].height;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.scale(dpr, dpr);

        const pad = { top: 16, right: 20, bottom: 32, left: 48 };
        const pw = w - pad.left - pad.right;
        const ph = h - pad.top - pad.bottom;

        // 背景
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(0, 0, w, h);

        if (data.length < 2) {
          ctx.fillStyle = "#94a3b8";
          ctx.font = "14px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText("数据不足", w / 2, h / 2);
          return;
        }

        const temps = data.map((r) => r.temp);
        const hums = data.map((r) => r.hum);
        const allVals = [...temps, ...hums].filter((v) => v != null);
        if (allVals.length === 0) return;

        const minVal = Math.floor(Math.min(...allVals) - 1);
        const maxVal = Math.ceil(Math.max(...allVals) + 1);
        const range = maxVal - minVal || 1;

        const toX = (i) => pad.left + (i / (data.length - 1)) * pw;
        const toY = (v) => pad.top + ph - ((v - minVal) / range) * ph;

        // 网格
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= 4; i++) {
          const y = pad.top + (ph / 4) * i;
          ctx.beginPath();
          ctx.moveTo(pad.left, y);
          ctx.lineTo(w - pad.right, y);
          ctx.stroke();
          ctx.fillStyle = "#94a3b8";
          ctx.font = "10px sans-serif";
          ctx.textAlign = "right";
          ctx.fillText(
            (maxVal - (range / 4) * i).toFixed(0),
            pad.left - 8,
            y + 3
          );
        }

        // 湿度线
        this.drawLine(ctx, hums, toX, toY, "#60a5fa");
        // 温度线
        this.drawLine(ctx, temps, toX, toY, "#f87171");

        // X 轴标签
        if (data.length > 0) {
          ctx.fillStyle = "#94a3b8";
          ctx.font = "10px sans-serif";
          ctx.textAlign = "center";
          const step = Math.max(1, Math.floor(data.length / 4));
          for (let i = 0; i < data.length; i += step) {
            const t = data[i].created_at || "";
            const label = t.length > 16 ? t.slice(5, 16) : t;
            ctx.fillText(label, toX(i), h - 4);
          }
        }
      });
  },

  drawLine(ctx, values, toX, toY, color) {
    const pts = [];
    values.forEach((v, i) => {
      if (v != null) pts.push({ x: toX(i), y: toY(v) });
    });
    if (pts.length < 2) return;

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i].x, pts[i].y);
    }
    ctx.stroke();

    // 数据点
    ctx.fillStyle = color;
    pts.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  },
});
