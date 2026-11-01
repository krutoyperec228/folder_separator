"""Tkinter GUI for Zipper."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .core import (
    CompressionMethod,
    GroupOptions,
    PackOptions,
    group_files,
    pack_archives,
    scan_files,
)
from .settings import load_settings, save_settings

APP_NAME = "Zipper GUI"


def _human(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _parse_extensions(raw: str) -> frozenset[str] | None:
    raw = raw.strip()
    if not raw:
        return None
    out: set[str] = set()
    for item in raw.split(","):
        item = item.strip().lower()
        if not item:
            continue
        out.add(item if item.startswith(".") else f".{item}")
    return frozenset(out) if out else None


class ZipperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("760x600")
        self.minsize(680, 560)

        self._cancel = threading.Event()
        self._worker: threading.Thread | None = None

        self.var_src = tk.StringVar()
        self.var_out = tk.StringVar()
        self.var_size = tk.StringVar(value="15")
        self.var_ext = tk.StringVar()
        self.var_prefix = tk.StringVar(value="archive")
        self.var_compress = tk.StringVar(value="deflate")
        self.var_recursive = tk.BooleanVar(value=True)

        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm_src = ttk.LabelFrame(self, text="Папка с исходными файлами")
        frm_src.pack(fill="x", **pad)
        ttk.Entry(frm_src, textvariable=self.var_src).pack(side="left", fill="x", expand=True, padx=6, pady=6)
        ttk.Button(frm_src, text="Обзор…", command=self._pick_src).pack(side="right", padx=6, pady=6)

        frm_out = ttk.LabelFrame(self, text="Папка для архивов")
        frm_out.pack(fill="x", **pad)
        ttk.Entry(frm_out, textvariable=self.var_out).pack(side="left", fill="x", expand=True, padx=6, pady=6)
        ttk.Button(frm_out, text="Обзор…", command=self._pick_out).pack(side="right", padx=6, pady=6)

        frm_opt = ttk.LabelFrame(self, text="Настройки")
        frm_opt.pack(fill="x", **pad)
        frm_opt.columnconfigure(3, weight=1)

        ttk.Label(frm_opt, text="Размер архива, МБ:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Spinbox(frm_opt, from_=0.1, to=100000, increment=0.5, textvariable=self.var_size, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(frm_opt, text="Префикс:").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(frm_opt, textvariable=self.var_prefix, width=20).grid(row=0, column=3, sticky="we", padx=6, pady=4)

        ttk.Label(frm_opt, text="Только расширения (через запятую):").grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Entry(frm_opt, textvariable=self.var_ext).grid(row=1, column=2, columnspan=2, sticky="we", padx=6, pady=4)

        ttk.Label(frm_opt, text="Сжатие:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(frm_opt, textvariable=self.var_compress, values=[m.value for m in CompressionMethod], state="readonly", width=12).grid(row=2, column=1, sticky="w", padx=6, pady=4)

        ttk.Checkbutton(frm_opt, text="Включая подпапки", variable=self.var_recursive).grid(row=2, column=2, columnspan=2, sticky="w", padx=6, pady=4)

        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", **pad)
        self.btn_start = ttk.Button(frm_btn, text="Старт", command=self._start)
        self.btn_start.pack(side="left", padx=6)
        self.btn_cancel = ttk.Button(frm_btn, text="Отмена", command=self._cancel_clicked, state="disabled")
        self.btn_cancel.pack(side="left", padx=6)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=14, pady=(0, 6))

        frm_log = ttk.LabelFrame(self, text="Журнал")
        frm_log.pack(fill="both", expand=True, **pad)
        self.txt = tk.Text(frm_log, height=14, wrap="word", state="disabled")
        self.txt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb = ttk.Scrollbar(frm_log, command=self.txt.yview)
        sb.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.txt.configure(yscrollcommand=sb.set)

        self.status = tk.StringVar(value="Готов")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    def _load(self) -> None:
        s = load_settings()
        self.var_src.set(str(s["src"]))
        self.var_out.set(str(s["out"]))
        self.var_size.set(str(s["size_mb"]))
        self.var_ext.set(str(s["extensions"]))
        self.var_prefix.set(str(s["prefix"]))
        self.var_compress.set(str(s["compression"]))
        self.var_recursive.set(bool(s["recursive"]))

    def _persist(self) -> None:
        save_settings({
            "src": self.var_src.get(),
            "out": self.var_out.get(),
            "size_mb": self.var_size.get(),
            "extensions": self.var_ext.get(),
            "prefix": self.var_prefix.get(),
            "compression": self.var_compress.get(),
            "recursive": self.var_recursive.get(),
        })

    def _pick_src(self) -> None:
        if d := filedialog.askdirectory(title="Выберите папку с файлами"):
            self.var_src.set(d)
            if not self.var_out.get():
                self.var_out.set(str(Path(d).parent / "archives"))

    def _pick_out(self) -> None:
        if d := filedialog.askdirectory(title="Выберите папку для архивов"):
            self.var_out.set(d)

    def _log(self, text: str) -> None:
        self.txt.configure(state="normal")
        self.txt.insert("end", text + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _start(self) -> None:
        src = Path(self.var_src.get().strip())
        out = Path(self.var_out.get().strip())

        if not src.is_dir():
            messagebox.showerror(APP_NAME, "Выберите существующую папку-источник.")
            return
        if not self.var_out.get().strip():
            messagebox.showerror(APP_NAME, "Выберите папку для сохранения архивов.")
            return
        try:
            size_mb = float(self.var_size.get().replace(",", "."))
            if size_mb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "Размер архива должен быть числом > 0.")
            return

        if out == src or out.is_relative_to(src):
            messagebox.showerror(APP_NAME, "Папка для архивов не должна находиться внутри исходной.")
            return

        self._persist()
        self._cancel.clear()
        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.progress.configure(value=0, maximum=100)
        self.status.set("Работаю…")

        group_opts = GroupOptions(
            max_bytes=int(size_mb * 1024 * 1024),
            extensions=_parse_extensions(self.var_ext.get()),
            recursive=self.var_recursive.get(),
        )
        pack_opts = PackOptions(compression=CompressionMethod(self.var_compress.get()))

        self._worker = threading.Thread(
            target=self._run,
            args=(src, out, group_opts, pack_opts, self.var_prefix.get().strip() or "archive"),
            daemon=True,
        )
        self._worker.start()

    def _cancel_clicked(self) -> None:
        self._cancel.set()
        self.status.set("Отмена…")

    def _run(self, src: Path, out: Path, group_opts: GroupOptions, pack_opts: PackOptions, prefix: str) -> None:
        try:
            self._job(src, out, group_opts, pack_opts, prefix)
        except Exception as exc:
            self._log(f"ОШИБКА: {exc}")
            self.status.set("Ошибка")
        finally:
            self.btn_start.configure(state="normal")
            self.btn_cancel.configure(state="disabled")

    def _job(self, src: Path, out: Path, group_opts: GroupOptions, pack_opts: PackOptions, prefix: str) -> None:
        self._log(f"Источник:   {src}")
        self._log(f"Приёмник:   {out}")
        self._log(f"Цель:       ~{group_opts.max_bytes / 1024 / 1024:.1f} МБ")
        self._log(f"Сжатие:     {pack_opts.compression.value}")
        self._log(f"Расширения: {', '.join(sorted(group_opts.extensions)) if group_opts.extensions else 'все'}")
        self._log(f"Подпапки:   {'да' if group_opts.recursive else 'нет'}")
        self._log("-" * 60)

        files = scan_files(src, group_opts)
        if not files:
            self._log("Не найдено файлов, подходящих под фильтр.")
            self.status.set("Готово (0 файлов)")
            return

        total = sum(f.stat().st_size for f in files)
        self._log(f"Найдено файлов: {len(files)} ({_human(total)})")

        groups = group_files(files, group_opts)
        self.progress.configure(maximum=len(groups), value=0)

        def on_progress(i: int, n: int, res: Any) -> None:
            self._log(f"[{i}/{n}] {res.path.name}: {len(res.files)} файл(ов), {_human(res.size_bytes)}")
            self.progress.configure(value=i)

        results = pack_archives(
            groups, src, out,
            prefix=prefix,
            pack_options=pack_opts,
            progress=on_progress,
            should_cancel=self._cancel.is_set,
        )

        self._log("-" * 60)
        if self._cancel.is_set():
            self._log(f"Отменено. Создано {len(results)} архив(ов).")
            self.status.set("Отменено")
        else:
            self._log(f"Готово. Создано {len(results)} архив(ов) в {out}")
            self.status.set(f"Готово: {len(results)} архив(ов)")


def main() -> None:
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, OSError):
            pass
    ZipperApp().mainloop()