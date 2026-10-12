from __future__ import annotations

import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "hospeda.sqlite3"
XLSX_PATH = ROOT / "hospedaje.xlsx"
BACKUP_PATH = ROOT / "hospeda_respaldo.json"
HOST, PORT = "127.0.0.1", 8765
LOCK = threading.Lock()


def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)")
    return con


def read_state():
    with connect_db() as con:
        row = con.execute("SELECT data FROM app_state WHERE id=1").fetchone()
    return json.loads(row[0]) if row else None


def column_name(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell_xml(value, ref: str) -> str:
    if value is None:
        value = ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = escape(str(value))
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def sheet_xml(rows) -> str:
    row_xml = []
    for r_index, row in enumerate(rows, 1):
        cells = "".join(cell_xml(value, f"{column_name(c_index)}{r_index}") for c_index, value in enumerate(row, 1))
        row_xml.append(f'<row r="{r_index}">{cells}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>')


def build_workbook(state: dict) -> bytes:
    rooms = state.get("rooms", [])
    bookings = state.get("bookings", [])
    room_names = {r.get("id"): r.get("name", "") for r in rooms}
    sheets = [
        ("Respaldo de alquileres", [["Habitación", "Huésped", "DNI", "Celular", "Fecha de entrada",
                                     "Fecha de salida / próximo cobro", "Monto total (S/)"]]
         + [[room_names.get(b.get("roomId"), "Habitación eliminada"), b.get("guest", ""), b.get("dni", ""),
             b.get("phone", ""), b.get("start", ""), b.get("end", ""), b.get("amount", 0)] for b in bookings]),
    ]
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>' + ''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
                                      for i, (name, _) in enumerate(sheets, 1)) + '</sheets></workbook>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                               for i in range(1, len(sheets) + 1)) + '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                               for i in range(1, len(sheets) + 1)) + '</Relationships>')
    from io import BytesIO
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for i, (_, rows) in enumerate(sheets, 1):
            archive.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))
    return out.getvalue()


def save_state(state: dict) -> tuple[bool, str]:
    serialized = json.dumps(state, ensure_ascii=False)
    with LOCK:
        with connect_db() as con:
            con.execute("INSERT INTO app_state(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (serialized,))
        try:
            BACKUP_PATH.write_text(serialized, encoding="utf-8")
            temp_path = ROOT / "hospedaje.tmp.xlsx"
            temp_path.write_bytes(build_workbook(state))
            os.replace(temp_path, XLSX_PATH)
            return True, ""
        except OSError as exc:
            return False, str(exc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_bytes(self, status: int, payload: bytes, content_type: str, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status: int, value):
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_bytes(status, payload, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            self.send_json(200, {"data": read_state()})
        elif path in ("/", "/index.html"):
            self.send_bytes(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/hospedaje.xlsx" and XLSX_PATH.exists():
            self.send_bytes(200, XLSX_PATH.read_bytes(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            {"Content-Disposition": 'attachment; filename="hospedaje.xlsx"'})
        else:
            self.send_json(404, {"error": "No encontrado"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/data":
            self.send_json(404, {"error": "No encontrado"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 5_000_000:
                raise ValueError("Tamaño de solicitud no válido")
            state = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(state, dict) or not all(isinstance(state.get(k), list) for k in ("rooms", "bookings", "expenses")):
                raise ValueError("Los datos recibidos no tienen el formato esperado")
            excel_updated, message = save_state(state)
            self.send_json(200, {"saved": True, "excelUpdated": excel_updated, "message": message})
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Hospeda está activo en http://{HOST}:{PORT}")
    print(f"Los datos se guardan en: {DB_PATH}")
    print(f"El Excel se actualiza en: {XLSX_PATH}")
    server.serve_forever()
