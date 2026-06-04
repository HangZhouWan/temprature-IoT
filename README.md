# IoT 传感器监控系统

ESP32 + Flask + 微信小程序 的温湿度实时监控方案。

## 目录结构

```
hardware/
├── esp32/             # ESP32 MicroPython 固件
├── server/            # Flask 后台服务
├── miniapp/           # 微信小程序
├── dev.sh             # ESP32 开发辅助脚本
└── pyproject.toml
```

## 1. ESP32 固件 (esp32/)

### 硬件连接

| 外设   | ESP32 引脚 |
|--------|-----------|
| OLED SDA | GPIO21 |
| OLED SCL | GPIO22 |
| OLED VCC | 5V (VIN) |
| OLED GND | GND |
| AHT20 SDA | GPIO19 |
| AHT20 SCL | GPIO18 |
| AHT20 VCC | 3.3V |
| AHT20 GND | GND |

### 部署

1. 烧录 MicroPython 固件到 ESP32
2. 修改 `esp32/main.py` 中的 WiFi 配置和服务器地址：

```python
WIFI_SSID = "你的WiFi名"
WIFI_PASS = "你的WiFi密码"
UPLOAD_URL = "http://你的服务器IP:8080/api/data"
```

3. 推送文件到 ESP32：

```bash
./dev.sh push esp32/main.py
./dev.sh push esp32/ssd1306.py
```

4. 重启 ESP32，`main.py` 会自动运行。

### 功能

- NTP 网络校时，大字号显示 HH:MM:SS 和日期
- AHT20 温湿度采集，屏幕底部轮播显示
- 每 5 分钟自动上传温湿度数据到后台，开机即刻上报一次
- 设备 ID 基于 MAC 地址生成

## 2. Flask 后台 (server/)

### 启动

```bash
cd server
pip install -r requirements.txt
python app.py --port 8080
```

### API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/data` | POST | 接收传感器数据 |
| `/api/latest` | GET | 各设备最新读数 |
| `/api/history` | GET | 历史数据查询 `?device=xxx&hours=24` |
| `/api/devices` | GET | 已注册设备列表 |
| `/api/devices/status` | GET | 设备状态列表（含在线/离线/异常判定） |

### 状态判定规则

- **在线** — 最近 10 分钟内有数据上报，温湿度正常
- **离线** — 超过 10 分钟未上报数据
- **异常** — 温度超过 50°C 或低于 -20°C，湿度超过 90% 或低于 10%

### Web 面板

浏览器访问 `http://服务器IP:8080` 可查看仪表盘，包含统计卡片、Chart.js 图表和最新数据表。

## 3. 微信小程序 (miniapp/)

### 导入

1. 打开微信开发者工具
2. 导入项目，选择 `miniapp/` 目录
3. 修改 `app.js` 中的 `apiBase` 为你的后台地址
4. 开发时勾选 "不校验合法域名"

### 页面

- **数据面板** — 最新数据概览，Canvas 2D 折线图
- **设备监控** — 设备列表，支持按在线/离线/异常状态筛选，显示温湿度和告警信息

## 数据上报格式

```json
{
  "id": "esp32_3076f5f47334",
  "temp": 26.1,
  "hum": 72.5,
  "lat": 39.9042,
  "lng": 116.4074,
  "time": "2026-06-04 15:30:00"
}
```
# temprature-IoT
