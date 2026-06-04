"""DHT11 + I2C 诊断"""
import time
from machine import Pin, I2C

# --- I2C 扫描 ---
print("\n--- I2C Scan ---")
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
devs = i2c.scan()
print("I2C devices:", [hex(d) for d in devs])

# --- DHT 引脚测试 ---
DHT = 4
print("\n--- DHT11 GPIO{} 测试 ---".format(DHT))

# 浮空状态
p = Pin(DHT, Pin.IN)
time.sleep_ms(10)
print("浮空电平:", p.value())

# 上拉
p = Pin(DHT, Pin.IN, Pin.PULL_UP)
time.sleep_ms(10)
print("上拉电平:", p.value())

# 下拉 (输出低)
p = Pin(DHT, Pin.OUT)
p.value(0)
time.sleep_ms(1)
print("输出低后读回:", p.value())

# 输出高
p.value(1)
time.sleep_ms(1)
print("输出高后读回:", p.value())

# 模拟读 DHT：先拉低再释放，看 pin 会不会被传感器拉低
p = Pin(DHT, Pin.OUT)
p.value(0)
time.sleep_ms(20)
p = Pin(DHT, Pin.IN, Pin.PULL_UP)
print("\n20ms 低脉冲后释放...")
start = time.ticks_us()
for i in range(500):
    v = p.value()
    if v == 0:
        print("检测到低电平! 延时 {}us".format(time.ticks_diff(time.ticks_us(), start)))
        break
    time.sleep_us(1)
else:
    print("500us 内未检测到低电平 - 传感器无应答")

print("\n诊断完成")
