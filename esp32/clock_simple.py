"""
SSD1306 时钟程序
- NTP 网络校时 (需配置 WiFi)
- 128x64 大字号时间显示
- 连接: VCC->3.3V, GND->GND, SDA->GPIO21, SCL->GPIO22
"""
import time
import network
import ntptime
from machine import Pin, SoftI2C
from ssd1306 import SSD1306

WIFI_SSID = "Xiaomi_1A5A"
WIFI_PASS = "zyishead"
TZ_OFFSET = 8

# 大号数字字模 (6x8 每字符)
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
}


def draw_digit(oled, digit, x, y, scale=2):
    pat = DIGITS.get(digit, DIGITS["0"])
    for row, byte_val in enumerate(pat):
        for col in range(8):
            if byte_val & (1 << (7 - col)):
                oled.fill_rect(x + col * scale, y + row * scale, scale, scale, 1)


def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(ssid, password)
    for _ in range(20):
        if wlan.isconnected():
            return True
        time.sleep(0.5)
    return False


def main():
    print("Initializing OLED...")
    time.sleep(0.5)
    i2c = SoftI2C(Pin(22), Pin(21), freq=100000)
    oled = SSD1306(128, 64, i2c)
    print("OLED ready")

    oled.text("Connecting...", 0, 0)
    oled.show()

    wifi_ok = connect_wifi(WIFI_SSID, WIFI_PASS)
    if wifi_ok:
        print("WiFi connected")
        oled.fill(0)
        oled.text("WiFi OK", 0, 0)
        oled.text("NTP sync...", 0, 16)
        oled.show()
        try:
            ntptime.settime()
            print("NTP synced")
            oled.text("Time synced!", 0, 32)
            oled.show()
            time.sleep(1)
        except Exception as e:
            print("NTP fail:", e)
            oled.text("NTP failed", 0, 32)
            oled.show()
            time.sleep(2)
    else:
        print("No WiFi, using uptime")
        oled.fill(0)
        oled.text("Offline mode", 0, 24)
        oled.show()
        time.sleep(2)

    if wifi_ok:
        start = time.time() + TZ_OFFSET * 3600
    else:
        start_ms = time.ticks_ms()

    last_ss = -1
    print("Clock running...")

    while True:
        if wifi_ok:
            t = time.localtime(time.time() + TZ_OFFSET * 3600)
            yy, mm, dd, hh, mi, ss = t[0], t[1], t[2], t[3], t[4], t[5]
        else:
            elapsed = time.ticks_diff(time.ticks_ms(), start_ms) // 1000
            hh = (elapsed // 3600) % 24
            mi = (elapsed // 60) % 60
            ss = elapsed % 60
            yy, mm, dd = 2025, 1, 1

        if ss == last_ss:
            time.sleep_ms(200)
            continue
        last_ss = ss

        oled.fill(0)

        # 大号时间: HHMM
        time_str = "{:02d}{:02d}".format(hh, mi)
        digit_w, gap, y = 14, 4, 10
        total_w = 4 * digit_w + gap
        sx = (128 - total_w) // 2

        draw_digit(oled, time_str[0], sx, y)
        draw_digit(oled, time_str[1], sx + digit_w, y)
        oled.fill_rect(sx + 2 * digit_w + 2, y + 6, 2, 2, 1)
        oled.fill_rect(sx + 2 * digit_w + 2, y + 16, 2, 2, 1)
        draw_digit(oled, time_str[2], sx + 2 * digit_w + 8, y)
        draw_digit(oled, time_str[3], sx + 3 * digit_w + 8, y)

        # 秒数
        oled.text("{:02d}".format(ss), 108, 0)

        # 日期
        date_str = "{:04d}-{:02d}-{:02d}".format(yy, mm, dd)
        oled.hline(0, 50, 128, 1)
        oled.text(date_str, (128 - len(date_str) * 8) // 2, 54)

        oled.show()
        time.sleep_ms(200)


main()
