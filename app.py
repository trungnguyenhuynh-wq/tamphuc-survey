"""
Bệnh viện đa khoa Tâm Phúc – Công cụ tiếp nhận phản ánh, góp ý của khách hàng
Chạy được cả LOCAL lẫn CLOUD (Render.com)
"""

from flask import (Flask, request, jsonify, send_from_directory,
                   session, redirect, url_for, render_template_string)
from flask_cors import CORS
import sqlite3, os, requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ══════════════════════════════════════════════════════
#  ⚙ CẤU HÌNH – CHỈ SỬA PHẦN NÀY
# ══════════════════════════════════════════════════════
SECRET_KEY = "tamphuc@2026!xyz"   # ← Đổi thành chuỗi bí mật bất kỳ
ADMIN_PATH = "quantritamphuc"     # ← Đường dẫn bí mật (không dùng /admin)
ADMIN_USER = "tamphuc"            # ← Tên đăng nhập
ADMIN_PASS = "Abc@123456"         # ← Mật khẩu mạnh

app.secret_key = SECRET_KEY

# ── Đường dẫn database ───────────────────────────────
# Render.com: dùng /tmp (thư mục ghi được trên free tier)
# Local:      cùng thư mục với app.py
IS_CLOUD = bool(os.environ.get('RENDER'))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = '/tmp/survey.db' if IS_CLOUD else os.path.join(BASE_DIR, 'survey.db')

# ── Telegram (để trống nếu chưa dùng) ───────────────
TELEGRAM_TOKEN   = ""   # VD: "7123456789:AAGxxxxxxx"
TELEGRAM_CHAT_ID = ""   # VD: "-1001234567890"

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception as e:
        print(f"Telegram lỗi: {e}")

def now_vn():
    """Giờ Việt Nam: Render chạy UTC nên +7, local lấy giờ máy."""
    return (datetime.utcnow() + timedelta(hours=7)) if IS_CLOUD else datetime.now()

def logged_in():
    return session.get('logged_in') is True

# ── Khởi tạo database ────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
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

# ══════════════════════════════════════════════════════
#  ROUTES – GIAO DIỆN
# ══════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    blocked = ['app.py', 'wsgi.py', 'survey.db', '.env']
    if filename in blocked or filename.startswith('.'):
        return "Không tìm thấy.", 404
    return send_from_directory(BASE_DIR, filename)

# ══════════════════════════════════════════════════════
#  ROUTES – API
# ══════════════════════════════════════════════════════
@app.route('/save', methods=['POST'])
def save_survey():
    try:
        data = request.json or {}
        for field in ['gioitinh', 'dienthoai', 'gopy']:
            if not data.get(field, '').strip():
                return jsonify({"status": "error", "message": f"Thiếu: {field}"}), 400

        ts = data.get('timestamp') or now_vn().strftime('%d/%m/%Y %H:%M:%S')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO responses (timestamp, gioitinh, dienthoai, gopy, ip_client) VALUES (?,?,?,?,?)",
            (ts, data['gioitinh'].strip(), data['dienthoai'].strip(),
             data['gopy'].strip(), request.remote_addr or 'unknown')
        )
        conn.commit()
        rid = c.lastrowid
        conn.close()

        print(f"✅ [{now_vn().strftime('%H:%M:%S')}] #{rid} | "
              f"{data['gioitinh']} | SĐT: {data['dienthoai']} | IP: {request.remote_addr}")

        send_telegram(
            f"📋 <b>Góp ý mới – Quầy Viện Phí</b>\n"
            f"👤 {data['gioitinh']}  |  📞 {data['dienthoai']}\n"
            f"📝 {data['gopy']}\n🕐 {ts}"
        )
        return jsonify({"status": "success", "id": rid})

    except Exception as e:
        print(f"❌ Lỗi /save: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/view')
def view_data():
    """Xem toàn bộ dữ liệu dạng JSON (dùng để backup)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT * FROM responses ORDER BY id DESC").fetchall()
        conn.close()
        data = [{"id": r[0], "timestamp": r[1], "gioitinh": r[2],
                 "dienthoai": r[3], "gopy": r[4]} for r in rows]
        return jsonify({"total": len(data), "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "time": now_vn().strftime('%H:%M:%S'),
                    "env": "render" if IS_CLOUD else "local"})

# ══════════════════════════════════════════════════════
#  ROUTES – QUẢN TRỊ (bảo mật, đường dẫn bí mật)
# ══════════════════════════════════════════════════════

# Chặn /admin cũ – trả 404 như không tồn tại
@app.route('/admin')
@app.route('/admin/')
def block_admin():
    return "Không tìm thấy.", 404

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Đăng nhập quản trị</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:sans-serif;background:#f0f9f5;min-height:100vh;
       display:flex;align-items:center;justify-content:center}
  .box{background:#fff;padding:2.5rem 2rem;border-radius:16px;
       box-shadow:0 8px 32px rgba(10,110,86,.12);width:320px}
  .ico{font-size:42px;text-align:center;margin-bottom:1rem}
  h2{color:#085041;font-size:17px;margin-bottom:1.5rem;text-align:center}
  label{font-size:13px;font-weight:600;color:#085041;display:block;margin-bottom:5px}
  input{width:100%;padding:11px 14px;border:2px solid #d0d0d0;border-radius:8px;
        font-size:14px;margin-bottom:14px;outline:none;font-family:inherit}
  input:focus{border-color:#0F6E56;box-shadow:0 0 0 3px rgba(15,110,86,.1)}
  button{width:100%;padding:13px;background:#0F6E56;color:#fff;border:none;
         border-radius:8px;font-size:15px;font-weight:700;cursor:pointer}
  button:hover{background:#085041}
  .err{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;
       padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:14px}
</style></head><body>
<div class="box">
  <div class="ico">🔐</div>
  <h2>Quản trị khảo sát</h2>
  {% if error %}<div class="err">⚠ {{ error }}</div>{% endif %}
  <form method="POST">
    <label>Tên đăng nhập</label>
    <input type="text" name="username" autocomplete="off" required>
    <label>Mật khẩu</label>
    <input type="password" name="password" required>
    <button type="submit">Đăng nhập</button>
  </form>
</div>
</body></html>'''

@app.route(f'/{ADMIN_PATH}', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form.get('username') == ADMIN_USER and
                request.form.get('password') == ADMIN_PASS):
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template_string(LOGIN_HTML, error="Sai tên đăng nhập hoặc mật khẩu.")
    if logged_in():
        return redirect(url_for('admin_dashboard'))
    return render_template_string(LOGIN_HTML, error=None)

@app.route(f'/{ADMIN_PATH}/dashboard')
def admin_dashboard():
    if not logged_in():
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM responses ORDER BY id DESC").fetchall()
    conn.close()

    rows_html = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td>"
        f"<td><span class='badge'>{r[2]}</span></td>"
        f"<td><a href='tel:{r[3]}'>{r[3]}</a></td>"
        f"<td title='{r[4]}'>{r[4][:80]}{'…' if len(r[4]) > 80 else ''}</td></tr>"
        for r in rows
    )

    return f'''<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quản trị – BVĐK Tâm Phúc</title>
<style>
  body{{font-family:sans-serif;margin:0;padding:20px;background:#f0f9f5;color:#222}}
  .top{{display:flex;align-items:center;justify-content:space-between;
        margin-bottom:20px;flex-wrap:wrap;gap:10px}}
  h2{{color:#085041;margin:0;font-size:18px}}
  .meta{{color:#666;font-size:13px;margin-bottom:16px}}
  .logout{{background:#e74c3c;color:#fff;border:none;padding:8px 18px;
           border-radius:8px;font-size:13px;font-weight:600;
           text-decoration:none;cursor:pointer}}
  .logout:hover{{background:#c0392b}}
  table{{width:100%;border-collapse:collapse;background:#fff;
         border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  th{{background:#0F6E56;color:#fff;padding:12px 14px;text-align:left;font-size:14px}}
  td{{padding:11px 14px;border-bottom:1px solid #eee;font-size:14px;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#f6fdf9}}
  .badge{{background:#e0f4ed;color:#0F6E56;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:600}}
  a{{color:#0F6E56;text-decoration:none}}
  .total{{display:inline-block;background:#0F6E56;color:#fff;
          border-radius:8px;padding:6px 18px;font-weight:700;
          font-size:15px;margin-bottom:16px}}
  @media(max-width:600px){{td,th{{padding:8px;font-size:12px}}}}
</style></head><body>
<div class="top">
  <h2>📋 Phản ánh, góp ý – BVĐK Tâm Phúc</h2>
  <a class="logout" href="/{ADMIN_PATH}/logout">Đăng xuất</a>
</div>
<div class="meta">Cập nhật: {now_vn().strftime('%d/%m/%Y, %H:%M:%S')}</div>
<div class="total">Tổng: {len(rows)} góp ý</div>
<table>
  <tr><th>#</th><th>Thời gian gửi</th><th>Giới tính</th>
      <th>Số điện thoại</th><th>Nội dung góp ý</th></tr>
  {rows_html or '<tr><td colspan="5" style="text-align:center;color:#888;padding:30px">Chưa có dữ liệu</td></tr>'}
</table>
</body></html>'''

@app.route(f'/{ADMIN_PATH}/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ══════════════════════════════════════════════════════
#  CHẠY
# ══════════════════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    if not IS_CLOUD:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        print("=" * 58)
        print("🚀  Server LOCAL đang chạy")
        print(f"   Máy này      : http://127.0.0.1:{port}")
        print(f"   Mạng LAN     : http://{local_ip}:{port}")
        print(f"   🔐 Quản trị  : http://127.0.0.1:{port}/{ADMIN_PATH}")
        print("=" * 58)

    app.run(host='0.0.0.0', port=port, debug=not IS_CLOUD)
