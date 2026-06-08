const API = getApp().globalData.apiBase;

Page({
  data: {
    deviceId: "",
    displayName: "",
    temp: "--",
    hum: "--",
    updateTime: "",
    history: [],
    hasData: false,
    editing: false,
    editName: "",
  },

  onLoad(options) {
    this.setData({ deviceId: options.device_id || "" });
    this.loadData();
  },

  onShow() {
    this.timer = setInterval(() => this.loadData(), 30000);
  },

  onHide() {
    clearInterval(this.timer);
  },

  onUnload() {
    clearInterval(this.timer);
  },

  loadData() {
    const { deviceId } = this.data;
    if (!deviceId) return;

    Promise.all([
      this.fetchLatest(),
      this.fetchHistory(),
      this.fetchName(),
    ]).then(([latest, history, name]) => {
      const d = latest[0] || {};
      this.setData({
        displayName: name || deviceId,
        temp: d.temp != null ? d.temp.toFixed(1) : "--",
        hum: d.hum != null ? d.hum.toFixed(1) : "--",
        updateTime: d.created_at || new Date().toLocaleTimeString(),
        history,
        hasData: history.length > 0,
      });
      this.drawChart(history);
    });
  },

  fetchLatest() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + "/api/latest",
        success: (res) => {
          const filtered = (res.data || []).filter(
            (r) => r.device_id === this.data.deviceId
          );
          resolve(filtered.length ? filtered : res.data || []);
        },
        fail: reject,
      });
    });
  },

  fetchHistory() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + "/api/history?device=" + this.data.deviceId + "&hours=12",
        success: (res) => resolve(res.data || []),
        fail: reject,
      });
    });
  },

  fetchName() {
    return new Promise((resolve) => {
      wx.request({
        url: API + "/api/device-names",
        success: (res) => {
          const names = res.data || {};
          resolve(names[this.data.deviceId] || "");
        },
        fail: () => resolve(""),
      });
    });
  },

  startEdit() {
    this.setData({
      editing: true,
      editName: this.data.displayName,
    });
  },

  onEditInput(e) {
    this.setData({ editName: e.detail.value });
  },

  cancelEdit() {
    this.setData({ editing: false });
  },

  saveName() {
    const name = this.data.editName.trim();
    if (!name) {
      wx.showToast({ title: "名称不能为空", icon: "none" });
      return;
    }
    wx.request({
      url: API + "/api/device-name",
      method: "POST",
      header: { "content-type": "application/json" },
      data: { device_id: this.data.deviceId, name },
      success: () => {
        this.setData({ displayName: name, editing: false });
        wx.showToast({ title: "已保存", icon: "success" });
      },
      fail: () => {
        wx.showToast({ title: "保存失败", icon: "none" });
      },
    });
  },

  drawChart(data) {
    const query = wx.createSelectorQuery();
    query
      .select("#detailChart")
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

        this.drawLine(ctx, hums, toX, toY, "#60a5fa");
        this.drawLine(ctx, temps, toX, toY, "#f87171");

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

    ctx.fillStyle = color;
    pts.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  },
});
