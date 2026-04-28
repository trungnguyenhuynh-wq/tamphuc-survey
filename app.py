"""
BVĐK Tâm Phúc – Hệ thống khảo sát hài lòng
Chạy được cả LOCAL lẫn CLOUD (Render.com)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Cho phép mọi origin trên Internet

# ── Đường dẫn database ────────────────────────────────────────────────────────
# Render.com dùng /tmp để ghi file (thư mục ghi được trên free tier)
# Local dùng cùng thư mục với app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join('/tmp', 'survey.db') if os.environ.get('RENDER') else os.path.join(BASE_DIR, 'survey.db')

# ── Khởi tạo database ─────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            gioitinh  TEXT,
            dienthoai TEXT,
            gopy      TEXT,
            ip_client TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✅ Database: {DB_PATH}")

init_db()

# ── Phục vụ giao diện HTML ────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

# ── API: Lưu khảo sát ─────────────────────────────────────────────────────────
@app.route('/save', methods=['POST'])
def save_survey():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Không có dữ liệu"}), 400

        for field in ['gioitinh', 'dienthoai', 'gopy']:
            if not data.get(field, '').strip():
                return jsonify({"status": "error", "message": f"Thiếu trường: {field}"}), 400

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO responses (timestamp, gioitinh, dienthoai, gopy, ip_client) VALUES (?, ?, ?, ?, ?)",
            (
                data.get('timestamp', datetime.now().strftime('%d/%m/%Y %H:%M:%S')),
                data['gioitinh'].strip(),
                data['dienthoai'].strip(),
                data['gopy'].strip(),
                request.remote_addr or 'unknown'
            )
        )
        conn.commit()
        new_id = c.lastrowid
        conn.close()

        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Lưu #{new_id} "
              f"| {data['gioitinh']} | SĐT: {data['dienthoai']} "
              f"| IP: {request.remote_addr}")
        return jsonify({"status": "success", "id": new_id})

    except Exception as e:
        print(f"❌ Lỗi /save: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ── API: Xem dữ liệu (dạng JSON) ─────────────────────────────────────────────
@app.route('/view', methods=['GET'])
def view_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM responses ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        data = [{"id": r[0], "timestamp": r[1], "gioitinh": r[2],
                 "dienthoai": r[3], "gopy": r[4]} for r in rows]
        return jsonify({"total": len(data), "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── API: Xem dữ liệu dạng bảng HTML đẹp ─────────────────────────────────────
@app.route('/admin', methods=['GET'])
def admin():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM responses ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        total = len(rows)

        rows_html = ""
        for r in rows:
            gopy_short = (r[4][:80] + '…') if len(r[4]) > 80 else r[4]
            rows_html += f"""
            <tr>
                <td>{r[0]}</td>
                <td>{r[1]}</td>
                <td><span class="badge">{r[2]}</span></td>
                <td><a href="tel:{r[3]}">{r[3]}</a></td>
                <td title="{r[4]}">{gopy_short}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dữ liệu khảo sát – BVĐK Tâm Phúc</title>
<style>
  body{{font-family:sans-serif;margin:0;padding:20px;background:#f0f9f5;color:#222}}
  h2{{color:#085041;margin-bottom:4px}}
  .meta{{color:#666;font-size:14px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  th{{background:#0F6E56;color:#fff;padding:12px 14px;text-align:left;font-size:14px}}
  td{{padding:11px 14px;border-bottom:1px solid #eee;font-size:14px;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#f6fdf9}}
  .badge{{background:#e0f4ed;color:#0F6E56;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}}
  a{{color:#0F6E56;text-decoration:none}}
  .total{{display:inline-block;background:#0F6E56;color:#fff;border-radius:8px;padding:6px 18px;font-weight:700;font-size:15px;margin-bottom:16px}}
  @media(max-width:600px){{td,th{{padding:8px 8px;font-size:12px}}}}
</style></head>
<body>
  <h2>📋 Dữ liệu khảo sát hài lòng – BVĐK Tâm Phúc</h2>
  <div class="meta">Quầy Viện Phí &nbsp;|&nbsp; Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
  <div class="total">Tổng: {total} phản hồi</div>
  <table>
    <tr><th>#</th><th>Thời gian</th><th>Giới tính</th><th>Điện thoại</th><th>Góp ý</th></tr>
    {rows_html if rows else '<tr><td colspan="5" style="text-align:center;color:#888;padding:30px">Chưa có dữ liệu</td></tr>'}
  </table>
</body></html>"""
    except Exception as e:
        return f"<h3>Lỗi: {e}</h3>", 500

# ── Health check ──────────────────────────────────────────────────────────────
@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "time": datetime.now().strftime('%H:%M:%S'),
                    "env": "render" if os.environ.get('RENDER') else "local"})

# ── Chạy ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_cloud = bool(os.environ.get('RENDER'))

    if not is_cloud:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        print("=" * 58)
        print("🚀  Server đang chạy – LOCAL MODE")
        print(f"   Máy này   : http://127.0.0.1:{port}")
        print(f"   Mạng LAN  : http://{local_ip}:{port}")
        print(f"   Xem data  : http://127.0.0.1:{port}/admin")
        print("=" * 58)

    app.run(host='0.0.0.0', port=port, debug=not is_cloud)
