"""
SSD1306 OLED 驱动 (I2C)
适用于 0.96 寸 128x64 显示屏
"""
import framebuf
import time

SET_CONTRAST = 0x81
SET_ENTIRE_ON = 0xA4
SET_NORM_INV = 0xA6
SET_DISP = 0xAE
SET_MEM_ADDR = 0x20
SET_COL_ADDR = 0x21
SET_PAGE_ADDR = 0x22
SET_DISP_START_LINE = 0x40
SET_SEG_REMAP = 0xA0
SET_MUX_RATIO = 0xA8
SET_COM_OUT_DIR = 0xC0
SET_DISP_OFFSET = 0xD3
SET_COM_PIN_CFG = 0xDA
SET_DISP_CLK_DIV = 0xD5
SET_PRECHARGE = 0xD9
SET_VCOM_DESEL = 0xDB
SET_CHARGE_PUMP = 0x8D


class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        i2c.scan()  # wake I2C bus
        time.sleep_ms(10)
        self._init_display()

    def _write_cmd(self, cmd):
        for _ in range(3):
            try:
                self.i2c.writeto(self.addr, bytes([0x80, cmd]))
                return
            except OSError:
                time.sleep_ms(1)

    def _write_data(self, buf):
        for _ in range(3):
            try:
                self.i2c.writeto(self.addr, b'\x40' + buf)
                return
            except OSError:
                time.sleep_ms(1)

    def _init_display(self):
        for cmd in (
            SET_DISP,
            SET_DISP_CLK_DIV, 0x80,
            SET_MUX_RATIO, self.height - 1,
            SET_DISP_OFFSET, 0x00,
            SET_DISP_START_LINE | 0x00,
            SET_CHARGE_PUMP, 0x14,
            SET_MEM_ADDR, 0x00,
            SET_SEG_REMAP | 0x01,
            SET_COM_OUT_DIR | 0x08,
            SET_COM_PIN_CFG, 0x12,
            SET_CONTRAST, 0xFF,
            SET_PRECHARGE, 0xF1,
            SET_VCOM_DESEL, 0x40,
            SET_ENTIRE_ON,
            SET_NORM_INV,
        ):
            self._write_cmd(cmd)
        time.sleep_ms(100)
        self._write_cmd(SET_DISP | 0x01)
        self.fill(0)
        self.show()

    def show(self):
        self._write_cmd(SET_COL_ADDR)
        self._write_cmd(0)
        self._write_cmd(self.width - 1)
        self._write_cmd(SET_PAGE_ADDR)
        self._write_cmd(0)
        self._write_cmd(self.pages - 1)
        for i in range(0, len(self.buffer), self.width):
            self._write_data(self.buffer[i:i + self.width])
