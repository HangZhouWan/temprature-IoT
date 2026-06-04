#!/bin/bash
# ESP32 MicroPython 开发脚本
# 使用前确保 PATH 包含: export PATH="$HOME/Library/Python/3.9/bin:$PATH"

PORT="/dev/cu.usbserial-0001"
MPREMOTE="mpremote connect $PORT"
ESPTOOL="esptool.py --port $PORT"

case "${1:-help}" in
    repl)
        $MPREMOTE repl
        ;;
    run)
        $MPREMOTE run "${2:-main.py}"
        ;;
    push)
        $MPREMOTE fs cp "$2" ":${2##*/}"
        ;;
    ls)
        $MPREMOTE fs ls
        ;;
    flash-firmware)
        echo "擦除并烧录固件..."
        $ESPTOOL erase_flash
        $ESPTOOL --chip esp32 write_flash -z 0x1000 "${2:-firmware.bin}"
        ;;
    info)
        $ESPTOOL flash_id
        ;;
    reset)
        $MPREMOTE soft-reset
        ;;
    *)
        echo "用法: $0 {repl|run|push|ls|flash-firmware|info|reset}"
        ;;
esac
