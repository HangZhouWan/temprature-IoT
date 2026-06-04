"""
SSD1306 WiFi 时钟 + AHT20 温湿度 + 数据上传
连接: OLED: VCC->5V, GND->GND, SDA->GPIO21, SCL->GPIO22
      AHT20: VCC->3.3V, GND->GND, SDA->GPIO19, SCL->GPIO18
"""
import time
import network
import ntptime
import urequests
import ujson
from machine import Pin, I2C
from ssd1306 import SSD1306

# ---------- 配置 ----------
WIFI_SSID = "vivo X200 Pro"
WIFI_PASS = "12345678"
TZ_OFFSET = 8

# 模拟坐标 (按实际位置修改)
LAT = 39.9042
LNG = 116.4074

# 上传地址 (修改为你的后台 URL)
UPLOAD_URL = "http://124.222.115.199:8080/api/data"
UPLOAD_INTERVAL = 300  # 5 分钟

AHT20_ADDR = 0x38

# ---------- 字体 ----------
DIGITS = {
    "0": [0x3E, 0x7F, 0x41, 0x41, 0x7F, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x7F, 0x40, 0x00],
    "2": [0x62, 0x73, 0x59, 0x49, 0x4F, 0x46],
    "3": [0x22, 0x63, 0x49, 0x49, 0x7F, 0x36],
    "4": [0x18, 0x1C, 0x16, 0x13, 0x7F, 0x7F],
    "5": [0x27, 0x67, 0x45, 0x45, 0x7D, 0x39],
    "6": [0x3E, 0x7F, 0x49, 0x49, 0x79, 0x30],
    "7": [0x01, 0x01, 0x71, 0x7D, 0x07, 0x03],
    "8": [0x36, 0x7F, 0x49, 0x49, 0x7F, 0x36],
    "9": [0x06, 0x4F, 0x49, 0x49, 0x7F, 0x3E],
    ":": [0x00, 0x00, 0x36, 0x36, 0x00, 0x00],
}

SCALE = 2
CW = 6 * SCALE
CH = 8 * SCALE

temp = 0
hum = 0
aht_ok = False
aht_i2c = None
device_id = ""
last_upload = 0
wlan = None


def draw_char(oled, ch, x, y):
    pat = DIGITS.get(ch, DIGITS["0"])
    for col in range(6):
        v = pat[col]
        for row in range(8):
            if v & (1 << row):
                oled.fill_rect(x + col * SCALE, y + row * SCALE, SCALE, SCALE, 1)


def draw_clock(oled, hh, mi, ss):
    s = "{:02d}:{:02d}:{:02d}".format(hh, mi, ss)
    tw = 8 * CW
    sx = (128 - tw) // 2
    y = (64 - CH) // 2
    for i, ch in enumerate(s):
        draw_char(oled, ch, sx + i * CW, y)


def init_aht():
    global aht_ok
    if aht_i2c is None:
        return
    aht_i2c.writeto(AHT20_ADDR, b'')
    time.sleep_ms(1)
    buf = aht_i2c.readfrom(AHT20_ADDR, 1)
    if buf[0] & 0x08 == 0:
        print("AHT20 calibrating...")
        aht_i2c.writeto(AHT20_ADDR, bytes([0xE1, 0x08, 0x00]))
        time.sleep_ms(20)
    aht_ok = True
    print("AHT20 ready")


def read_aht():
    global temp, hum, aht_ok
    if aht_i2c is None:
        return
    try:
        aht_i2c.writeto(AHT20_ADDR, bytes([0xAC, 0x33, 0x00]))
        time.sleep_ms(80)
        data = aht_i2c.readfrom(AHT20_ADDR, 7)
        raw_h = (data[1] << 12) | (data[2] << 4) | (data[3] >> 4)
        raw_t = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        hum = raw_h * 100 / 1048576
        temp = raw_t * 200 / 1048576 - 50
        aht_ok = True
    except Exception as e:
        aht_ok = False
        print("AHT20 err:", e)


def upload_data():
    global last_upload
    if not wlan.isconnected() or not aht_ok:
        return

    now = time.time()
    if now - last_upload < UPLOAD_INTERVAL:
        return

    t = time.localtime(now + TZ_OFFSET * 3600)
    payload = {
        "id": device_id,
        "temp": round(temp, 1),
        "hum": round(hum, 1),
        "lat": LAT,
        "lng": LNG,
        "time": "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        ),
    }

    try:
        print("Uploading:", payload)
        r = urequests.post(UPLOAD_URL, json=payload, timeout=5)
        print("Upload OK:", r.status_code)
        r.close()
        last_upload = now
    except Exception as e:
        print("Upload err:", e)


# ---------- 初始化 ----------
time.sleep(1)

# 设备 ID (MAC 地址)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac = wlan.config("mac")
device_id = "esp32_" + "".join("{:02x}".format(b) for b in mac)
print("Device ID:", device_id)
wlan.active(False)

# OLED
i2c_oled = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
oled = SSD1306(128, 64, i2c_oled)

# AHT20
print("\n--- AHT20 I2C Scan ---")
try:
    aht_i2c = I2C(1, scl=Pin(18), sda=Pin(19), freq=100000)
    devs = aht_i2c.scan()
    print("AHT20 bus:", [hex(d) for d in devs])
    if AHT20_ADDR in devs:
        init_aht()
    else:
        print("AHT20 not found!")
except Exception as e:
    print("AHT20 bus error:", e)
    aht_i2c = None

oled.fill(0)
oled.text("WiFi Connecting...", 4, 28)
oled.show()

# WiFi
wlan.active(False)
time.sleep(0.5)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)

for _ in range(40):
    if wlan.isconnected():
        break
    time.sleep(0.5)

# NTP
ntp_ok = False
if wlan.isconnected():
    oled.fill(0)
    oled.text("WiFi OK", 4, 20)
    oled.text("NTP syncing...", 4, 36)
    oled.show()
    ntptime.timeout = 3
    for host in ("ntp.aliyun.com", "cn.ntp.org.cn", "pool.ntp.org"):
        try:
            ntptime.host = host
            ntptime.settime()
            ntp_ok = True
            break
        except Exception as e:
            print("NTP %s fail: %s" % (host, e))

if not ntp_ok:
    oled.fill(0)
    oled.text("Offline mode", 4, 28)
    oled.show()
    time.sleep(2)

# 开机立即上报一次
if wlan.isconnected():
    read_aht()
    upload_data()

# ---------- 主循环 ----------
start_ms = time.ticks_ms()
ticks = 0

while True:
    if ntp_ok:
        t = time.localtime(time.time() + TZ_OFFSET * 3600)
        hh, mi, ss = t[3], t[4], t[5]
        yy, mm, dd = t[0], t[1], t[2]
    else:
        elapsed = time.ticks_diff(time.ticks_ms(), start_ms) // 1000
        hh = (elapsed // 3600) % 24
        mi = (elapsed // 60) % 60
        ss = elapsed % 60
        yy, mm, dd = 2025, 1, 1

    # 每 2 秒读 AHT20
    if ticks % 10 == 0:
        read_aht()

    # 每 5 分钟上传
    if ticks % 1500 == 0:
        upload_data()

    ticks += 1

    oled.fill(0)
    date_str = "{:04d}-{:02d}-{:02d}".format(yy, mm, dd)
    oled.text(date_str, (128 - len(date_str) * 8) // 2, 2)
    draw_clock(oled, hh, mi, ss)
    info = "T:{:.0f}C  H:{:.0f}%".format(temp, hum)
    oled.text(info, (128 - len(info) * 8) // 2, 50)
    oled.show()
    time.sleep_ms(200)
