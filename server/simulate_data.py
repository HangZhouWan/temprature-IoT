"""模拟 10 个传感器最近 12 小时的数据"""
import requests
import random
import math
from datetime import datetime, timedelta

API = "http://localhost:8080/api/data"

# 10 个传感器，各有不同的温度和湿度基线
# 有的正常、有的偏热、有的偏冷、有的偏湿
# 中心坐标: 北京 (39.9042, 116.4074)，各传感器散布在周围
BASE_LAT, BASE_LNG = 39.9042, 116.4074
sensors = [
    {"id": "传感器-A01", "base_temp": 24.5, "base_hum": 52, "label": "大棚-1",  "lat": BASE_LAT + 0.008,  "lng": BASE_LNG + 0.005},
    {"id": "传感器-A02", "base_temp": 25.0, "base_hum": 48, "label": "大棚-2",  "lat": BASE_LAT + 0.010,  "lng": BASE_LNG - 0.002},
    {"id": "传感器-A03", "base_temp": 26.2, "base_hum": 55, "label": "大棚-3",  "lat": BASE_LAT + 0.005,  "lng": BASE_LNG + 0.010},
    {"id": "传感器-B01", "base_temp": 33.5, "base_hum": 42, "label": "大棚-4",  "lat": BASE_LAT + 0.015,  "lng": BASE_LNG + 0.008},   # 偏高
    {"id": "传感器-B02", "base_temp": 35.0, "base_hum": 38, "label": "种植区-A", "lat": BASE_LAT - 0.003,  "lng": BASE_LNG + 0.015},   # 偏高
    {"id": "传感器-C01", "base_temp": 4.2,  "base_hum": 65, "label": "冷库-1",   "lat": BASE_LAT - 0.010,  "lng": BASE_LNG - 0.005},   # 偏低
    {"id": "传感器-C02", "base_temp": 3.0,  "base_hum": 70, "label": "冷库-2",   "lat": BASE_LAT - 0.008,  "lng": BASE_LNG - 0.010},   # 偏低
    {"id": "传感器-D01", "base_temp": 23.0, "base_hum": 88, "label": "育苗棚",    "lat": BASE_LAT + 0.020,  "lng": BASE_LNG - 0.008},   # 高湿
    {"id": "传感器-D02", "base_temp": 24.0, "base_hum": 15, "label": "仓库",      "lat": BASE_LAT - 0.015,  "lng": BASE_LNG + 0.003},   # 低湿
    {"id": "传感器-E01", "base_temp": 25.5, "base_hum": 50, "label": "办公室",    "lat": BASE_LAT + 0.003,  "lng": BASE_LNG - 0.012},   # 正常
]

# 先设置阈值，让部分传感器触发告警
requests.post("http://localhost:8080/api/thresholds", json={
    "temp_high": 30, "temp_low": 8,
    "hum_high": 80, "hum_low": 20
})
print("阈值已设置: 温度 8°C~30°C, 湿度 20%~80%")

# 设置自定义名称
for s in sensors:
    requests.post("http://localhost:8080/api/device-name", json={
        "device_id": s["id"], "name": s["label"]
    })
print("设备名称已设置")

# 生成过去 12 小时的数据，每 5-15 分钟一条
now = datetime.now()
total = 0

for sensor in sensors:
    # 每个传感器最后上报时间不同，E01 设为 15 分钟前（离线）
    if sensor["label"] == "走廊":
        minutes_ago = 15
        points = 5  # E01 只模拟少量数据
        print(f"\n{sensor['id']} ({sensor['label']}): 模拟离线 - 最后上报 15 分钟前")
    else:
        minutes_ago = random.randint(0, 2)
        points = 60
        hours_back = 12

    for i in range(points):
        t = now - timedelta(minutes=(points - 1 - i) / (points - 1) * (hours_back * 60) + minutes_ago)
        # 添加 ±2°C 的随机波动和正弦周期变化
        wave = math.sin(i / points * 2 * math.pi) * 1.5
        temp = sensor["base_temp"] + wave + random.uniform(-0.5, 0.5)
        hum = sensor["base_hum"] + wave * 2 + random.uniform(-2, 2)
        hum = max(5, min(95, hum))

        payload = {
            "id": sensor["id"],
            "temp": round(temp, 1),
            "hum": round(hum, 1),
            "lat": sensor["lat"] + random.uniform(-0.0003, 0.0003),
            "lng": sensor["lng"] + random.uniform(-0.0003, 0.0003),
            "time": t.strftime("%Y-%m-%d %H:%M:%S"),
        }
        requests.post(API, json=payload)
        total += 1

print(f"\n完成! 共插入 {total} 条数据")

# 验证
print("\n=== 设备状态 ===")
resp = requests.get("http://localhost:8080/api/devices/status").json()
for d in resp:
    status_mark = {
        "online": "✓",
        "offline": "✗",
        "warning": "⚠",
    }.get(d["status"], "?")
    print(f"  {status_mark} {d['device_id']}: {d.get('temp', '--')}°C / {d.get('hum', '--')}% [{d['status']}] {d['last_seen']}")
