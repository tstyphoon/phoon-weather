"""功能的註冊處。

新增功能只要在 categories/ 或 handlers/ 新增一個檔案，用下面的裝飾器登記，
核心不需要任何修改。啟動時 load_plugins() 會自動載入所有檔案。
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "tests" / "samples"
RESERVED_CATEGORY = "non_weather"


class RegistryError(Exception):
    """功能宣告有誤。啟動時就會失敗，不等到執行時才出錯。"""


@dataclass
class Field:
    name: str
    type: type  # float / int / str
    label: str = ""
    min: float | None = None
    max: float | None = None
    choices: list[str] | None = None
    required: bool = True
    desc: str = ""  # 給模型看的說明


@dataclass
class Category:
    name: str
    title: str
    icon: str
    description: str
    headline: str
    fields: list[Field]
    footer_notes: list[str] = field(default_factory=list)
    extra: Callable[[dict], dict] | None = None  # 需要額外運算時才有
    extra_labels: dict[str, str] = field(default_factory=dict)
    analyze: bool = True  # False：分類那一步就夠了（例如非天氣）


@dataclass
class Command:
    name: str
    description: str
    usage: str
    func: Callable
    ephemeral: bool = False


@dataclass
class TextIntent:
    name: str
    func: Callable
    keywords: tuple[str, ...] | None = None  # None：預設處理者


CATEGORIES: dict[str, Category] = {}
COMMANDS: dict[str, Command] = {}
TEXT_INTENTS: dict[str, TextIntent] = {}


def category(*, name, title, icon, description, headline, fields,
             footer_notes=None, extra_labels=None, analyze=True):
    """宣告一種圖片類別。被裝飾的函式（可有可無）用來做額外運算：
    接收驗證過的資料 dict，回傳要追加的欄位 dict。"""

    def deco(func=None):
        extra = None if (func is None or _is_empty(func)) else func
        if name in CATEGORIES:
            raise RegistryError(f"類別名稱重複：{name}")
        CATEGORIES[name] = Category(
            name=name, title=title, icon=icon, description=description,
            headline=headline, fields=list(fields),
            footer_notes=list(footer_notes or []), extra=extra,
            extra_labels=dict(extra_labels or {}), analyze=analyze,
        )
        return func

    return deco


def _is_empty(func) -> bool:
    """函式內容只有 `...` 或 pass，就當作沒有額外運算。"""
    return func.__code__.co_code == (lambda: None).__code__.co_code


def command(name: str, *, description: str = "", usage: str | None = None, ephemeral: bool = False):
    """宣告一個 / 指令。函式簽名：func(ctx, arg) -> str，arg 的型別可寫 str / int / float。"""

    def deco(func):
        if name in COMMANDS:
            raise RegistryError(f"指令名稱重複：{name}")
        COMMANDS[name] = Command(name, description or (func.__doc__ or "").strip(),
                                 usage or f"/{name}", func, ephemeral)
        return func

    return deco


def text_intent(name: str, *, keywords: tuple[str, ...] | None = None):
    """宣告一個 @bot 文字功能。keywords 為 None 的是預設處理者（最多一個）。"""

    def deco(func):
        if name in TEXT_INTENTS:
            raise RegistryError(f"文字功能名稱重複：{name}")
        if keywords is None and any(t.keywords is None for t in TEXT_INTENTS.values()):
            raise RegistryError("只能有一個預設的文字功能")
        TEXT_INTENTS[name] = TextIntent(name, func, keywords)
        return func

    return deco


def load_plugins(packages: tuple[str, ...] = ("categories", "handlers")) -> None:
    """載入 categories/ 與 handlers/ 底下所有模組，並檢查宣告。"""
    for pkg_name in packages:
        pkg = importlib.import_module(pkg_name)
        for mod in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg_name}.{mod.name}")
    validate_all()


def validate_all(require_samples: bool = True) -> None:
    if RESERVED_CATEGORY not in CATEGORIES:
        raise RegistryError(f"缺少必要的類別：{RESERVED_CATEGORY}")
    for cat in CATEGORIES.values():
        names = [f.name for f in cat.fields]
        if len(set(names)) != len(names):
            raise RegistryError(f"類別 {cat.name} 的欄位名稱重複")
        known = set(names) | set(cat.extra_labels)
        try:
            cat.headline.format_map(_Any(known))
        except KeyError as e:
            raise RegistryError(f"類別 {cat.name} 的 headline 引用了不存在的欄位：{e}") from None
        for f in cat.fields:
            if f.type not in (float, int, str):
                raise RegistryError(f"類別 {cat.name} 欄位 {f.name} 的型別只能是 float / int / str")
        if require_samples and not (SAMPLES_DIR / f"{cat.name}.json").exists():
            raise RegistryError(f"類別 {cat.name} 沒有測試樣本：tests/samples/{cat.name}.json")
    for cmd in COMMANDS.values():
        if not inspect.iscoroutinefunction(cmd.func) and not callable(cmd.func):
            raise RegistryError(f"指令 {cmd.name} 不是可呼叫的函式")


class _Any(dict):
    """只允許已宣告的欄位名稱出現在 headline。"""

    def __init__(self, known):
        super().__init__()
        self.known = known

    def __missing__(self, key):
        if key in self.known:
            return ""
        raise KeyError(key)


def coerce_arg(func: Callable, arg: str) -> tuple[bool, Any]:
    """依 handler 第二個參數的型別註解轉換使用者輸入。失敗回傳 (False, None)。"""
    params = list(inspect.signature(func).parameters.values())[1:]
    if not params:
        return True, None
    ann = params[0].annotation
    arg = arg.strip()
    if not arg:
        if params[0].default is not inspect.Parameter.empty:
            return True, params[0].default
        return (ann in (str, inspect.Parameter.empty)), ""
    try:
        if ann is float:
            return True, float(arg)
        if ann is int:
            return True, int(arg)
    except ValueError:
        return False, None
    return True, arg
