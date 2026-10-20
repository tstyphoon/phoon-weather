"""SQLite 紀錄與圖片檔。所有查詢都帶 user_id（分人），並且一律使用參數化查詢。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  id          INTEGER PRIMARY KEY,
  created_at  TEXT NOT NULL,
  user_id     TEXT NOT NULL,
  user_name   TEXT NOT NULL,
  kind        TEXT NOT NULL,
  city        TEXT,
  data        TEXT NOT NULL,
  note        TEXT,
  image_path  TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_user_time ON records(user_id, created_at);
CREATE TABLE IF NOT EXISTS user_settings (
  user_id TEXT PRIMARY KEY,
  city    TEXT
);
"""


def now_local() -> datetime:
    """以這台電腦的本地時間為準。"""
    return datetime.now()


class Store:
    def __init__(self, db_path: Path, images_dir: Path):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ---- 圖片檔 ----
    def save_image(self, filename: str, content: bytes) -> Path:
        """存圖片。同名時加 -2、-3，絕不覆蓋舊檔。回傳實際存放的路徑。"""
        base = self.images_dir
        stem, suffix = Path(filename).stem, Path(filename).suffix
        candidate, n = base / filename, 1
        while True:
            try:
                with open(candidate, "xb") as f:  # x：檔案已存在就失敗
                    f.write(content)
                return candidate
            except FileExistsError:
                n += 1
                candidate = base / f"{stem}-{n}{suffix}"

    def delete_image(self, path: str | None) -> None:
        if not path:
            return
        p = Path(path).resolve()
        if self.images_dir.resolve() in p.parents and p.is_file():  # 只刪 images/ 底下的
            p.unlink()

    # ---- 紀錄 ----
    def add_record(self, *, user_id, user_name, kind, data: dict, city=None, note=None,
                   image_path=None, created_at: datetime | None = None) -> int:
        created = (created_at or now_local()).strftime("%Y-%m-%d %H:%M:%S")
        cur = self.db.execute(
            "INSERT INTO records(created_at,user_id,user_name,kind,city,data,note,image_path)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (created, str(user_id), user_name, kind, city,
             json.dumps(data, ensure_ascii=False), note, str(image_path) if image_path else None))
        self.db.commit()
        return cur.lastrowid

    def recent(self, user_id, limit: int = 5) -> list[sqlite3.Row]:
        """最近的天氣紀錄（不含非天氣）。"""
        return self.db.execute(
            "SELECT * FROM records WHERE user_id=? AND kind!='non_weather'"
            " ORDER BY id DESC LIMIT ?", (str(user_id), limit)).fetchall()

    def today_counts(self, user_id, day: datetime | None = None) -> dict[str, int]:
        prefix = (day or now_local()).strftime("%Y-%m-%d") + "%"
        rows = self.db.execute(
            "SELECT kind, COUNT(*) n FROM records WHERE user_id=? AND created_at LIKE ?"
            " AND kind!='non_weather' GROUP BY kind", (str(user_id), prefix)).fetchall()
        return {r["kind"]: r["n"] for r in rows}

    def today_count(self, user_id, day: datetime | None = None) -> int:
        return sum(self.today_counts(user_id, day).values())

    def delete_record(self, user_id, record_id: int) -> bool:
        """只能刪自己的。成功時連圖片一起刪。"""
        row = self.db.execute("SELECT image_path FROM records WHERE id=? AND user_id=?",
                              (record_id, str(user_id))).fetchone()
        if row is None:
            return False
        self.db.execute("DELETE FROM records WHERE id=? AND user_id=?", (record_id, str(user_id)))
        self.db.commit()
        self.delete_image(row["image_path"])
        return True

    def recent_wind(self, user_id, limit: int = 20) -> list[dict]:
        """有風速的紀錄（新到舊），給風速比較用。"""
        out = []
        rows = self.db.execute(
            "SELECT created_at, city, data FROM records WHERE user_id=? AND kind!='non_weather'"
            " ORDER BY id DESC LIMIT ?", (str(user_id), limit)).fetchall()
        for r in rows:
            data = json.loads(r["data"])
            if isinstance(data.get("wind_speed"), (int, float)):
                out.append({"created_at": r["created_at"], "city": r["city"] or data.get("location"),
                            "wind_speed": float(data["wind_speed"])})
        return out

    # ---- 使用者設定 ----
    def get_city(self, user_id) -> str | None:
        row = self.db.execute("SELECT city FROM user_settings WHERE user_id=?",
                              (str(user_id),)).fetchone()
        return row["city"] if row else None

    def set_city(self, user_id, city: str) -> None:
        self.db.execute("INSERT INTO user_settings(user_id,city) VALUES(?,?)"
                        " ON CONFLICT(user_id) DO UPDATE SET city=excluded.city",
                        (str(user_id), city))
        self.db.commit()

    def close(self) -> None:
        self.db.close()
