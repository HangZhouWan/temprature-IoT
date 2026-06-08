"""
IoT 传感器数据后台
启动: python app.py --port 8080
"""

import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)

# ---------- 数据库 ----------
DB = "sensor.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                temp REAL,
                hum REAL,
                lat REAL,
                lng REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_time
            ON readings(device_id, created_at DESC)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temp_high REAL DEFAULT 50,
                temp_low REAL DEFAULT -20,
                hum_high REAL DEFAULT 90,
                hum_low REAL DEFAULT 10,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 确保有一条默认记录
        conn.execute("""
            INSERT OR IGNORE INTO thresholds (id) VALUES (1)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_names (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)


# ---------- API ----------
@app.route("/api/data", methods=["POST"])
def receive_data():
    """接收传感器数据"""
    data = request.get_json(force=True)
    db = get_db()
    db.execute(
        "INSERT INTO readings (device_id, temp, hum, lat, lng, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            data.get("id", "unknown"),
            data.get("temp"),
            data.get("hum"),
            data.get("lat"),
            data.get("lng"),
            data.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ),
    )
    db.commit()
    return jsonify({"ok": True}), 201


@app.route("/api/latest")
def latest():
    """各设备最新读数"""
    db = get_db()
    rows = db.execute("""
        SELECT r.* FROM readings r
        JOIN (SELECT device_id, MAX(created_at) AS ma
              FROM readings GROUP BY device_id) latest
        ON r.device_id = latest.device_id AND r.created_at = latest.ma
        ORDER BY r.created_at DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/history")
def history():
    """历史数据查询"""
    device = request.args.get("device", "")
    hours = int(request.args.get("hours", 24))
    since = datetime.now() - timedelta(hours=hours)
    db = get_db()
    if device:
        rows = db.execute(
            "SELECT * FROM readings WHERE device_id = ? AND created_at >= ? "
            "ORDER BY created_at ASC",
            (device, since.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM readings WHERE created_at >= ? "
            "ORDER BY created_at ASC",
            (since.strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/devices")
def devices():
    """已注册设备列表"""
    db = get_db()
    rows = db.execute(
        "SELECT device_id, COUNT(*) AS count, MAX(created_at) AS last_seen "
        "FROM readings GROUP BY device_id ORDER BY last_seen DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


def _get_thresholds():
    """读取阈值配置，无记录时返回默认值"""
    db = get_db()
    row = db.execute("SELECT * FROM thresholds WHERE id = 1").fetchone()
    if row:
        return dict(row)
    return {"temp_high": 50, "temp_low": -20, "hum_high": 90, "hum_low": 10}


@app.route("/api/thresholds", methods=["GET", "POST"])
def thresholds():
    """获取或更新预警阈值"""
    db = get_db()
    if request.method == "GET":
        return jsonify(_get_thresholds())

    data = request.get_json(force=True)
    fields = {}
    for k in ("temp_high", "temp_low", "hum_high", "hum_low"):
        if k in data:
            fields[k] = data[k]
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [1]
        db.execute(
            f"UPDATE thresholds SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            vals,
        )
        db.commit()
    return jsonify(_get_thresholds())


@app.route("/api/device-names")
def device_names():
    """获取所有设备自定义名称"""
    db = get_db()
    rows = db.execute("SELECT device_id, name FROM device_names").fetchall()
    return jsonify({r["device_id"]: r["name"] for r in rows})


@app.route("/api/device-name", methods=["POST"])
def set_device_name():
    """设置单个设备名称"""
    data = request.get_json(force=True)
    device_id = data.get("device_id", "").strip()
    name = data.get("name", "").strip()
    if not device_id or not name:
        return jsonify({"ok": False, "error": "device_id and name required"}), 400
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO device_names (device_id, name) VALUES (?, ?)",
        (device_id, name),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/devices/status")
def devices_status():
    """设备状态列表（含在线/离线/异常判定）"""
    timeout = int(request.args.get("timeout", 10))
    cutoff = datetime.now() - timedelta(minutes=timeout)
    th = _get_thresholds()
    db = get_db()

    rows = db.execute("""
        SELECT r.device_id, r.temp, r.hum, r.lat, r.lng,
               r.created_at AS last_seen,
               (SELECT COUNT(*) FROM readings WHERE device_id = r.device_id) AS total
        FROM readings r
        JOIN (SELECT device_id, MAX(created_at) AS ma
              FROM readings GROUP BY device_id) latest
        ON r.device_id = latest.device_id AND r.created_at = latest.ma
        ORDER BY r.created_at DESC
    """).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        last = datetime.strptime(d["last_seen"], "%Y-%m-%d %H:%M:%S")
        if last < cutoff:
            d["status"] = "offline"
        elif d["temp"] is not None and (d["temp"] > th["temp_high"] or d["temp"] < th["temp_low"]):
            d["status"] = "warning"
        elif d["hum"] is not None and (d["hum"] > th["hum_high"] or d["hum"] < th["hum_low"]):
            d["status"] = "warning"
        else:
            d["status"] = "online"
        result.append(d)

    return jsonify(result)


# ---------- 页面 ----------
@app.route("/")
def dashboard():
    db = get_db()
    devs = db.execute(
        "SELECT device_id, MAX(created_at) AS last_seen "
        "FROM readings GROUP BY device_id ORDER BY last_seen DESC"
    ).fetchall()
    return render_template("index.html", devices=[dict(d) for d in devs])


# ---------- 启动 ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    init_db()
    print(f"\n  后台已启动: http://{args.host}:{args.port}")
    print(f"  API: POST http://{args.host}:{args.port}/api/data\n")
    app.run(host=args.host, port=args.port, debug=False)
