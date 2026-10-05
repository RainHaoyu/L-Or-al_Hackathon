"""数据域：致敏原库 / IgE 材料库 / 香水库 / 香调规则 / QRA2 配置 的加载、匹配与热更新。

支持 admin 接口在运行期重载 seed（后台数据升级无需重新部署）。
匹配策略：精确（INCI/CAS/中文名/别名）→ 归一化 → difflib 模糊（阈值 0.82）。
"""
from __future__ import annotations

import difflib
import json
import re
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

FUZZY_THRESHOLD = 0.82

ALIASES: dict[str, str] = {
    "lilial": "Butylphenyl Methylpropional",
    "lyral": "Hydroxycitronellal",
    "hicc": "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde",
    "新铃兰醛": "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde",
    "limonene": "d-Limonene",
    "methyl heptine carbonate": "Methyl-2-octynoate(Methyl heptine carbonate)",
    "oakmoss": "Oakmoss extract",
    "treemoss": "Treemoss extract",
    "cinnamaldehyde": "Cinnamal",
    "铃兰醛": "Butylphenyl Methylpropional",
    "羟基香兰醛": "Hydroxycitronellal",
    # v2 香水库 INCI 拼写对齐
    "alpha-isomethyl ionone": "α-Isomethyl ionone",
    "benzyl salicylate": "Benzyl salicylate",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).lower()
    for h in "\u2010\u2011\u2012\u2013\u2014\u2212":
        s = s.replace(h, "-")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff-]", "", s)


class IngredientRepository:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._lock = threading.RLock()
        self.allergens: list[dict] = []
        self.ige_materials: list[dict] = []
        self.perfumes: list[dict] = []
        self.families: dict = {}
        self.config: dict = {}
        self.last_reload_at = ""
        self._allergen_index: dict[str, dict] = {}
        self._ige_index: dict[str, dict] = {}
        self._perfume_index: dict[str, dict] = {}
        self._barcode_index: dict[str, dict] = {}

    # —— 加载 / 热更新 ——
    def load(self) -> None:
        with self._lock:
            self.allergens = self._read("allergens.json")["items"]
            self.ige_materials = self._read("ige_materials.json")["items"]
            # v2 数据键为 perfumes；兼容早期 products 键
            self.perfumes = self._read("perfumes.json").get("perfumes") \
                or self._read("perfumes.json")["products"]
            self.families = {k: v for k, v in self._read("families.json").items() if not k.startswith("$")}
            self.config = self._read("config.json")
            self._rebuild_indexes()
            self.last_reload_at = datetime.now(timezone.utc).isoformat()

    def reload_allergens(self, items: list[dict]) -> int:
        """admin 热更新：替换致敏原库并重建索引。"""
        with self._lock:
            self.allergens = items
            self._rebuild_indexes()
            self.last_reload_at = datetime.now(timezone.utc).isoformat()
            return len(items)

    def _read(self, name: str):
        return json.loads((self.data_dir / name).read_text(encoding="utf-8"))

    def _rebuild_indexes(self) -> None:
        self._allergen_index = {}
        for a in self.allergens:
            for key in filter(None, (_norm(a.get("inci", "")), _norm(a.get("name_zh", "")),
                                    a.get("cas", ""), _norm(a.get("inci_raw", "")))):
                self._allergen_index.setdefault(key, a)
        for k, v in ALIASES.items():
            hit = self._allergen_index.get(_norm(v))
            if hit is not None:
                self._allergen_index.setdefault(_norm(k), hit)
        self._ige_index = {_norm(m.get("inci") or m.get("name_zh", "")): m for m in self.ige_materials}
        self._ige_index.update({_norm(m.get("name_zh", "")): m for m in self.ige_materials})
        self._perfume_index = {}
        self._barcode_index = {}
        for p in self.perfumes:
            self._perfume_index[p["id"]] = p
            if p.get("barcode"):
                self._barcode_index[re.sub(r"\D", "", p["barcode"])] = p

    # —— 匹配 ——
    def find_allergen(self, name: str) -> dict | None:
        key = _norm(name)
        if not key:
            return None
        with self._lock:
            if key in self._allergen_index:
                return self._allergen_index[key]
            candidates = [*(a.get("inci", "") for a in self.allergens),
                          *(a.get("name_zh", "") for a in self.allergens),
                          *ALIASES.keys()]
            close = difflib.get_close_matches(name.lower().strip(), [c.lower() for c in candidates], n=1,
                                              cutoff=FUZZY_THRESHOLD)
            if close:
                return self._allergen_index.get(_norm(close[0]))
            # 中英文子串包含（如"含柠檬烯提取物"）
            for a in self.allergens:
                if len(key) >= 3 and (key in _norm(a.get("inci", "")) or key in _norm(a.get("name_zh", ""))):
                    return a
            return None

    def find_ige(self, name: str) -> dict | None:
        with self._lock:
            return self._ige_index.get(_norm(name))

    def find_perfume(self, *, product_id: str | None = None, barcode: str | None = None,
                     query: str | None = None) -> dict | None:
        with self._lock:
            if product_id and product_id in self._perfume_index:
                return self._perfume_index[product_id]
            if barcode:
                digits = re.sub(r"\D", "", barcode)
                if digits and digits in self._barcode_index:
                    return self._barcode_index[digits]
            if query:
                hits = self.search_products(query, limit=1)
                if hits:
                    return self._perfume_index[hits[0]["id"]]
            return None

    def search_products(self, q: str, limit: int = 8) -> list[dict]:
        key = _norm(q)
        with self._lock:
            scored: list[tuple[float, dict]] = []
            for p in self.perfumes:
                hay = _norm(f"{p.get('brand', '')} {p.get('name', '')} {p.get('id', '')}")
                if key and key in hay:
                    scored.append((3.0, p))
                    continue
                ratio = difflib.SequenceMatcher(None, key, hay).ratio() if key else 0.0
                if ratio >= FUZZY_THRESHOLD:
                    scored.append((ratio, p))
            scored.sort(key=lambda x: -x[0])
            return [p for _, p in scored[:limit]]

    def search_allergens(self, q: str, limit: int = 10) -> list[dict]:
        key = _norm(q)
        if not key:
            with self._lock:
                return list(self.allergens[:limit])
        with self._lock:
            hits = [a for a in self.allergens
                    if key in _norm(a.get("inci", "")) or key in _norm(a.get("name_zh", ""))]
            if not hits:
                hits = [a for a in self.allergens
                        if difflib.SequenceMatcher(None, key, _norm(a.get("inci", ""))).ratio() >= FUZZY_THRESHOLD]
            return hits[:limit]

    def stats(self) -> dict:
        with self._lock:
            return {
                "allergens": len(self.allergens),
                "ige_materials": len(self.ige_materials),
                "perfumes": len(self.perfumes),
                "families": len(self.families),
                "config_version": self.config.get("engine_version", ""),
                "last_reload_at": self.last_reload_at,
            }


_repo: IngredientRepository | None = None


def init_repository(data_dir: Path) -> IngredientRepository:
    global _repo
    _repo = IngredientRepository(data_dir)
    _repo.load()
    return _repo


def get_repository() -> IngredientRepository:
    if _repo is None:
        raise RuntimeError("repository 未初始化（应在 app lifespan 中调用 init_repository）")
    return _repo
