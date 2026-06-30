import hashlib
import html
import json
import os
import re
import sqlite3
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib import parse, request

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "ch5_translator_deepseek_config.json"
CACHE_PATH = APP_DIR / "ch5_translation_cache.sqlite3"

DEFAULT_CONFIG = {
    "dialogue_file": "",
    "poll_interval_ms": 120,
    "provider": "google_free",
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "api_key": "",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-v4-flash",
    },
    "google": {
        "base_url": "https://translation.googleapis.com/language/translate/v2",
        "api_key": "",
        "api_key_env": "GOOGLE_TRANSLATE_API_KEY",
        "target": "zh-CN",
        "source": "en",
        "model": "nmt",
    },
    "google_free": {
        "base_url": "https://translate.googleapis.com/translate_a/single",
        "target": "zh-CN",
        "source": "en",
        "client": "gtx",
    },
    "microsoft": {
        "endpoint": "https://api.cognitive.microsofttranslator.com/translate",
        "api_key": "",
        "api_key_env": "MICROSOFT_TRANSLATOR_KEY",
        "region": "",
        "target": "zh-Hans",
        "source": "en",
    },
    "bing_free": {
        "auth_url": "https://edge.microsoft.com/translate/auth",
        "endpoint": "https://api.cognitive.microsofttranslator.com/translate",
        "target": "zh-Hans",
        "source": "en",
    },
}

CONTROL_RE = re.compile(r"(\\[A-Za-z][A-Za-z0-9]?|\\[A-Z][0-9]?|\^[0-9]+|[%/])")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_CONFIG))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update(config)
    for section in ("deepseek", "google", "google_free", "microsoft", "bing_free"):
        merged[section] = {**DEFAULT_CONFIG[section], **config.get(section, {})}
    return merged


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def candidate_dialogue_files() -> list[Path]:
    bases = [
        Path(r"C:\Software\Steam\steamapps\common\DELTARUNE\chapter5_windows"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "DELTARUNE",
        Path(os.environ.get("LOCALAPPDATA", "")) / "deltarune",
        Path(os.environ.get("APPDATA", "")) / "DELTARUNE",
    ]
    return [base / "ch5_translation_dialogue.txt" for base in bases if (base / "ch5_translation_dialogue.txt").exists()]


def clean_game_text(text: str) -> str:
    text = re.sub(r"^\d+:\s*", "", text.strip())
    text = CONTROL_RE.sub("", text)
    text = text.replace("&", "\n").replace("#", " / ")
    text = text.replace("~1", "{1}").replace("~2", "{2}")
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_dialogue(raw: str) -> list[str]:
    lines = []
    for line in raw.splitlines():
        cleaned = clean_game_text(line)
        if not cleaned or cleaned in {"x", "%%"}:
            continue
        if len(cleaned) <= 2 and not any(ch.isalpha() for ch in cleaned):
            continue
        lines.append(cleaned)
    return lines


class TranslationCache:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS translations (hash TEXT PRIMARY KEY, source TEXT NOT NULL, target TEXT NOT NULL)"
        )
        self.conn.commit()

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> str | None:
        row = self.conn.execute("SELECT target FROM translations WHERE hash = ?", (self.key(text),)).fetchone()
        return row[0] if row else None

    def set(self, text: str, target: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO translations (hash, source, target) VALUES (?, ?, ?)",
            (self.key(text), text, target),
        )
        self.conn.commit()

    def delete(self, text: str) -> None:
        self.conn.execute("DELETE FROM translations WHERE hash = ?", (self.key(text),))
        self.conn.commit()


class Translator:
    PROVIDER_LABELS = {
        "deepseek": "DeepSeek",
        "google": "Google",
        "google_free": "Google Free",
        "microsoft": "Microsoft",
        "bing_free": "Bing Free",
    }

    def __init__(self, config: dict, cache: TranslationCache):
        self.config = config
        self.cache = cache

    def translate_block(self, lines: list[str], force: bool = False) -> tuple[str, str, str]:
        source = "\n".join(lines).strip()
        if not source:
            return "", "", "Waiting for dialogue..."
        provider = self.provider_id()
        namespace = self.cache_namespace(provider)
        cache_key = namespace + "\n" + source
        if force:
            self.cache.delete(cache_key)
        else:
            cached = self.cache.get(cache_key)
            if cached:
                return source, cached, f"{self.provider_label(provider)} cache hit"
        target = self._translate(provider, source)
        if target != source and not target.startswith("未检测到"):
            self.cache.set(cache_key, target)
        action = "retranslated" if force else "translated"
        return source, target, f"{self.provider_label(provider)} {action}"

    def provider_id(self) -> str:
        provider = self.config.get("provider", "deepseek")
        return provider if provider in self.PROVIDER_LABELS else "google_free"

    def provider_label(self, provider: str | None = None) -> str:
        return self.PROVIDER_LABELS.get(provider or self.provider_id(), "DeepSeek")

    def cache_namespace(self, provider: str) -> str:
        if provider == "deepseek":
            cfg = self.config["deepseek"]
            return f"deepseek:{cfg['model']}"
        if provider == "google":
            cfg = self.config["google"]
            return f"google:{cfg['target']}:{cfg.get('model', 'nmt')}"
        if provider == "google_free":
            cfg = self.config["google_free"]
            return f"google_free:{cfg['target']}:{cfg.get('client', 'gtx')}"
        if provider == "bing_free":
            cfg = self.config["bing_free"]
            return f"bing_free:{cfg['target']}"
        cfg = self.config["microsoft"]
        return f"microsoft:{cfg['target']}"

    def _translate(self, provider: str, source: str) -> str:
        if provider == "google":
            return self._translate_google(source)
        if provider == "google_free":
            return self._translate_google_free(source)
        if provider == "microsoft":
            return self._translate_microsoft(source)
        if provider == "bing_free":
            return self._translate_bing_free(source)
        return self._translate_deepseek(source)

    def _translate_deepseek(self, source: str) -> str:
        cfg = self.config["deepseek"]
        api_key = cfg.get("api_key") or os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            return "未检测到 DeepSeek API Key，请在配置文件填写 deepseek.api_key 或设置 DEEPSEEK_API_KEY。\n\n" + source
        payload = {
            "model": cfg["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "Translate Deltarune dialogue into vivid, natural Simplified Chinese. Preserve line breaks, names, jokes, tone, and placeholders like {1}. Output only Chinese translation.",
                },
                {"role": "user", "content": source},
            ],
            "temperature": 0.2,
        }
        req = request.Request(
            cfg["base_url"],
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()

    def _translate_google(self, source: str) -> str:
        cfg = self.config["google"]
        api_key = cfg.get("api_key") or os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            return "未检测到 Google Translate API Key，请在配置文件填写 google.api_key 或设置 GOOGLE_TRANSLATE_API_KEY。\n\n" + source
        params = {
            "key": api_key,
            "q": source,
            "target": cfg.get("target", "zh-CN"),
            "format": "text",
            "model": cfg.get("model", "nmt"),
        }
        if cfg.get("source"):
            params["source"] = cfg["source"]
        data = parse.urlencode(params).encode("utf-8")
        req = request.Request(
            cfg["base_url"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            method="POST",
        )
        with request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        translations = body.get("data", {}).get("translations", [])
        if not translations:
            return source
        return html.unescape(translations[0].get("translatedText", "")).strip()

    def _translate_google_free(self, source: str) -> str:
        cfg = self.config["google_free"]
        params = {
            "client": cfg.get("client", "gtx"),
            "sl": cfg.get("source", "en"),
            "tl": cfg.get("target", "zh-CN"),
            "dt": "t",
            "q": source,
        }
        url = cfg["base_url"] + "?" + parse.urlencode(params)
        req = request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"},
            method="GET",
        )
        with request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        chunks = []
        for part in body[0] if body else []:
            if part and part[0]:
                chunks.append(part[0])
        return html.unescape("".join(chunks)).strip() or source
    def _translate_microsoft(self, source: str) -> str:
        cfg = self.config["microsoft"]
        api_key = cfg.get("api_key") or os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            return "未检测到 Microsoft Translator Key，请在配置文件填写 microsoft.api_key 或设置 MICROSOFT_TRANSLATOR_KEY。\n\n" + source
        query = {"api-version": "3.0", "to": cfg.get("target", "zh-Hans")}
        if cfg.get("source"):
            query["from"] = cfg["source"]
        url = cfg["endpoint"] + "?" + parse.urlencode(query)
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json; charset=UTF-8",
        }
        if cfg.get("region"):
            headers["Ocp-Apim-Subscription-Region"] = cfg["region"]
        payload = [{"Text": source}]
        req = request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        translations = body[0].get("translations", []) if body else []
        if not translations:
            return source
        return translations[0].get("text", "").strip()

    def _translate_bing_free(self, source: str) -> str:
        cfg = self.config["bing_free"]
        auth_req = request.Request(
            cfg["auth_url"],
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/plain,*/*"},
            method="GET",
        )
        with request.urlopen(auth_req, timeout=15) as resp:
            token = resp.read().decode("utf-8").strip()
        if not token:
            return "Bing Free 获取临时 token 失败，可能被限流或需要浏览器验证。\n\n" + source
        query = {"api-version": "3.0", "to": cfg.get("target", "zh-Hans")}
        if cfg.get("source"):
            query["from"] = cfg["source"]
        url = cfg["endpoint"] + "?" + parse.urlencode(query)
        payload = [{"Text": source}]
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "Mozilla/5.0",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        translations = body[0].get("translations", []) if body else []
        if not translations:
            return source
        return translations[0].get("text", "").strip()

class SidecarApp:
    def __init__(self):
        self.config = load_config()
        self.cache = TranslationCache(CACHE_PATH)
        self.translator = Translator(self.config, self.cache)
        self.dialogue_path = self._initial_dialogue_path()
        self.last_raw = None
        self.last_source = None
        self.current_lines = []
        self.pending_thread = None
        self.translation_generation = 0

        self.root = tk.Tk()
        self.root.title("Deltarune CH5 Live Translator")
        self.root.geometry("1240x720+60+60")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0c0d0f")

        self.status = tk.StringVar(value="Starting...")
        self.provider_var = tk.StringVar(value=self.config.get("provider", "google_free"))
        self.path_var = tk.StringVar(value=str(self.dialogue_path) if self.dialogue_path else "No dialogue file selected")
        self._build_ui()
        self.root.after(100, self.poll)

    def _initial_dialogue_path(self) -> Path | None:
        configured = self.config.get("dialogue_file", "")
        if configured and Path(configured).exists():
            return Path(configured)
        found = candidate_dialogue_files()
        if found:
            self.config["dialogue_file"] = str(found[0])
            save_config(self.config)
            return found[0]
        return None

    def _build_ui(self) -> None:
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        top = tk.Frame(self.root, bg="#0c0d0f")
        top.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top, text="DELTARUNE CH5 TRANSLATOR", bg="#0c0d0f", fg="#f2c46d", font=("Cascadia Mono", 12, "bold")).pack(side="left")
        provider_menu = tk.OptionMenu(top, self.provider_var, "google_free", "bing_free", "google", "microsoft", command=self.change_provider)
        provider_menu.configure(bg="#22262d", fg="#e8edf2", activebackground="#303741", activeforeground="#ffffff", relief="flat", highlightthickness=0)
        provider_menu.pack(side="left", padx=(16, 0))
        tk.Button(top, text="Reload", command=self.reload_config, bg="#22262d", fg="#e8edf2", relief="flat", padx=12).pack(side="right", padx=(8, 0))
        tk.Button(top, text="重新翻译", command=self.retranslate_current, bg="#2f5f50", fg="#f2fff8", relief="flat", padx=12).pack(side="right", padx=(8, 0))
        tk.Button(top, text="Select File", command=self.choose_file, bg="#f2c46d", fg="#111318", relief="flat", padx=12).pack(side="right")

        path_row = tk.Frame(self.root, bg="#0c0d0f")
        path_row.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(path_row, textvariable=self.path_var, bg="#0c0d0f", fg="#7f8b99", anchor="w", wraplength=900).pack(fill="x")

        body = tk.Frame(self.root, bg="#0c0d0f")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1, uniform="panes")
        body.grid_columnconfigure(1, weight=1, uniform="panes")
        body.grid_rowconfigure(0, weight=1)
        left = self._make_panel(body, "ORIGINAL", "#9cb8ff")
        right = self._make_panel(body, "中文译文", "#79d6ad")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.source_text = self._make_text(left, "#151820", "#dbe5f4", ("Cascadia Mono", 12))
        self.target_text = self._make_text(right, "#121a17", "#f2fff8", ("Microsoft YaHei UI", 14))

        bottom = tk.Frame(self.root, bg="#0c0d0f")
        bottom.pack(fill="x", padx=14, pady=(0, 14))
        tk.Label(bottom, textvariable=self.status, bg="#0c0d0f", fg="#9aa6b2", anchor="w").pack(side="left", fill="x", expand=True)

    def _make_panel(self, parent: tk.Frame, label: str, color: str) -> tk.Frame:
        frame = tk.Frame(parent, bg="#0f1116", highlightbackground="#2a3038", highlightthickness=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        tk.Label(frame, text=label, bg="#0f1116", fg=color, font=("Cascadia Mono", 10, "bold"), anchor="w", padx=12, pady=8).pack(fill="x")
        return frame

    def _make_text(self, parent: tk.Frame, bg: str, fg: str, font: tuple) -> tk.Text:
        text = tk.Text(parent, wrap="word", width=1, height=1, bg=bg, fg=fg, insertbackground=fg, relief="flat", padx=16, pady=16, font=font, spacing1=2, spacing3=8)
        text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        text.configure(state="disabled")
        return text

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(title="Select ch5_translation_dialogue.txt", filetypes=[("Dialogue bridge", "ch5_translation_dialogue.txt"), ("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.dialogue_path = Path(path)
            self.config["dialogue_file"] = path
            save_config(self.config)
            self.path_var.set(path)
            self.last_raw = None

    def change_provider(self, provider: str) -> None:
        self.config["provider"] = provider
        save_config(self.config)
        self.translator = Translator(self.config, self.cache)
        self.translation_generation += 1
        label = self.translator.provider_label(provider)
        self.status.set(f"Provider: {label}")
        if self.current_lines:
            generation = self.translation_generation
            self.update_target(f"切换到 {label}，翻译中...", f"Translating with {label}...")
            self.start_translation(list(self.current_lines), generation)

    def reload_config(self) -> None:
        self.config = load_config()
        self.provider_var.set(self.config.get("provider", "google_free"))
        self.translator = Translator(self.config, self.cache)
        self.status.set("Config reloaded")

    def poll(self) -> None:
        try:
            if not self.dialogue_path or not self.dialogue_path.exists():
                found = candidate_dialogue_files()
                if found:
                    self.dialogue_path = found[0]
                    self.path_var.set(str(found[0]))
                else:
                    self.status.set("Waiting for ch5_translation_dialogue.txt")
                    self.root.after(self.config["poll_interval_ms"], self.poll)
                    return
            raw = self.dialogue_path.read_text(encoding="utf-8", errors="replace")
            if raw != self.last_raw:
                self.last_raw = raw
                lines = parse_dialogue(raw)
                source = "\n".join(lines)
                if source != self.last_source:
                    self.last_source = source
                    self.current_lines = lines
                    self.translation_generation += 1
                    generation = self.translation_generation
                    self.update_source(source, "Translating...")
                    self.update_target("翻译中...")
                    self.start_translation(lines, generation)
        except Exception as exc:
            self.status.set(f"Read error: {exc}")
        self.root.after(self.config["poll_interval_ms"], self.poll)

    def start_translation(self, lines: list[str], generation: int, force: bool = False) -> None:
        def work():
            try:
                _source, translated, status = self.translator.translate_block(lines, force=force)
                self.root.after(0, lambda: self.update_translation_result(generation, translated, status))
            except Exception as exc:
                fallback = "\n".join(lines)
                self.root.after(0, lambda: self.update_translation_result(generation, fallback, f"Translate error: {exc}"))

        self.pending_thread = threading.Thread(target=work, daemon=True)
        self.pending_thread.start()

    def retranslate_current(self) -> None:
        if not self.current_lines:
            self.status.set("No current text to retranslate")
            return
        self.translation_generation += 1
        generation = self.translation_generation
        self.update_target("重新翻译中...", "Retranslating...")
        self.start_translation(list(self.current_lines), generation, force=True)

    def set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def update_source(self, source: str, status: str | None = None) -> None:
        self.set_text(self.source_text, source)
        if status is not None:
            self.status.set(status)

    def update_target(self, target: str, status: str | None = None) -> None:
        self.set_text(self.target_text, target)
        if status is not None:
            self.status.set(status)

    def update_translation_result(self, generation: int, target: str, status: str) -> None:
        if generation != self.translation_generation:
            return
        self.update_target(target, status)

    def update_text(self, source: str, target: str, status: str) -> None:
        self.update_source(source)
        self.update_target(target, status)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    try:
        SidecarApp().run()
    except Exception as exc:
        messagebox.showerror("Deltarune CH5 Translator", str(exc))

