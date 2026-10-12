import queue
import re
import shutil
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "文件归类整理器"
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


@dataclass
class FileItem:
    source: Path
    group: str


class OrganizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1080x720")
        self.minsize(900, 620)
        self.configure(bg="#f4f6f8")

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.separator_var = tk.StringVar(value="-")
        self.index_var = tk.StringVar(value="2")
        self.regex_var = tk.StringVar()
        self.extensions_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.keep_empty_var = tk.BooleanVar(value=False)
        self.conflict_var = tk.StringVar(value="skip")
        self.status_var = tk.StringVar(value="请选择源文件夹，然后点击“扫描预览”")
        self.summary_var = tk.StringVar(value="尚未扫描")

        self.items = []
        self.groups = {}
        self.last_manifest = []
        self.last_used_overwrite = False
        self.log_queue = queue.Queue()
        self.busy = False

        self._configure_style()
        self._build_ui()
        self.after(120, self._drain_log_queue)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f6f8", foreground="#263238", font=("Microsoft YaHei UI", 10))
        style.configure("Card.TLabel", background="#ffffff")
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#17212b", font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("Hint.TLabel", background="#f4f6f8", foreground="#60717d", font=("Microsoft YaHei UI", 9))
        style.configure("Section.TLabel", background="#ffffff", foreground="#1f303b", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))

    def _build_ui(self):
        outer = ttk.Frame(self, padding=(24, 18, 24, 20))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="按文件名中的共同信息自动分组到文件夹，先预览再执行，整理过程可撤销。", style="Hint.TLabel").pack(anchor="w", pady=(5, 0))

        columns = ttk.Frame(outer)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=0, minsize=350)
        columns.columnconfigure(1, weight=1)
        columns.rowconfigure(0, weight=1)

        self._build_settings(columns).grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_preview(columns).grid(row=0, column=1, sticky="nsew")

        status = ttk.Frame(outer)
        status.pack(fill="x", pady=(12, 0))
        ttk.Label(status, textvariable=self.status_var, style="Hint.TLabel").pack(side="left")
        ttk.Label(status, textvariable=self.summary_var, style="Hint.TLabel").pack(side="right")

    def _build_settings(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="1 选择文件位置", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(card, text="源文件夹").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(card, textvariable=self.source_var).grid(row=1, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(card, text="浏览", command=self._choose_source).grid(row=1, column=2, pady=5)

        ttk.Label(card, text="目标文件夹").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(card, textvariable=self.destination_var).grid(row=2, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(card, text="浏览", command=self._choose_destination).grid(row=2, column=2, pady=5)

        ttk.Separator(card).grid(row=3, column=0, columnspan=3, sticky="ew", pady=16)
        ttk.Label(card, text="2 设置分类规则", style="Section.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(card, text="分隔符").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(card, textvariable=self.separator_var, width=10).grid(row=5, column=1, sticky="w", padx=8, pady=5)
        ttk.Label(card, text="例如 - 或 _", style="Hint.TLabel").grid(row=5, column=2, sticky="w")

        ttk.Label(card, text="取第几段").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Spinbox(card, from_=1, to=99, textvariable=self.index_var, width=8).grid(row=6, column=1, sticky="w", padx=8, pady=5)
        ttk.Label(card, text="从左往右，示例取第 2 段", style="Hint.TLabel").grid(row=6, column=2, sticky="w")

        ttk.Label(card, text="正则规则").grid(row=7, column=0, sticky="w", pady=5)
        ttk.Entry(card, textvariable=self.regex_var).grid(row=7, column=1, columnspan=2, sticky="ew", padx=8, pady=5)
        ttk.Label(card, text="可选；使用第 1 个捕获组作为文件夹名", style="Hint.TLabel").grid(row=8, column=1, columnspan=2, sticky="w", padx=8)

        ttk.Label(card, text="扩展名过滤").grid(row=9, column=0, sticky="w", pady=(13, 5))
        ttk.Entry(card, textvariable=self.extensions_var).grid(row=9, column=1, columnspan=2, sticky="ew", padx=8, pady=(13, 5))
        ttk.Label(card, text="可填 jpg,png,pdf；留空表示全部", style="Hint.TLabel").grid(row=10, column=1, columnspan=2, sticky="w", padx=8)

        ttk.Separator(card).grid(row=11, column=0, columnspan=3, sticky="ew", pady=16)
        ttk.Label(card, text="3 处理选项", style="Section.TLabel").grid(row=12, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Checkbutton(card, text="包含子文件夹中的文件", variable=self.recursive_var).grid(row=13, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(card, text="将无法匹配的文件归入“未匹配”", variable=self.keep_empty_var).grid(row=14, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(card, text="重名文件").grid(row=15, column=0, sticky="w", pady=(8, 5))
        conflict = ttk.Combobox(card, textvariable=self.conflict_var, state="readonly", width=18,
                                values=("skip", "rename", "overwrite"))
        conflict.grid(row=15, column=1, sticky="w", padx=8, pady=(8, 5))
        conflict.configure(values=("跳过（推荐）", "自动改名", "覆盖已有文件"))
        conflict.current(0)

        ttk.Label(card, text="提示：目标文件夹可以与源文件夹相同，程序只会处理扫描时发现的文件。", style="Hint.TLabel", wraplength=305).grid(row=16, column=0, columnspan=3, sticky="w", pady=(12, 0))
        return card

    def _build_preview(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)
        ttk.Label(card, text="预览分组", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text="扫描后检查每个文件夹将包含哪些文件，再执行整理。", style="Card.TLabel", foreground="#60717d").grid(row=1, column=0, sticky="w", pady=(5, 12))

        tree_frame = ttk.Frame(card, style="Card.TFrame")
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, columns=("type", "count", "path"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="分组 / 文件")
        self.tree.heading("type", text="状态")
        self.tree.heading("count", text="数量")
        self.tree.heading("path", text="来源路径")
        self.tree.column("#0", width=260, anchor="w")
        self.tree.column("type", width=100, anchor="center")
        self.tree.column("count", width=70, anchor="center")
        self.tree.column("path", width=360, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="扫描预览", style="Accent.TButton", command=self.scan).pack(side="left")
        ttk.Button(buttons, text="开始整理", command=self.organize).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="撤销上次整理", command=self.undo_last).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="清空预览", command=self.clear_preview).pack(side="right")
        return card

    def _choose_source(self):
        path = filedialog.askdirectory(title="选择源文件夹")
        if path:
            self.source_var.set(path)
            if not self.destination_var.get():
                self.destination_var.set(path)

    def _choose_destination(self):
        path = filedialog.askdirectory(title="选择目标文件夹")
        if path:
            self.destination_var.set(path)

    def _read_options(self):
        source_text = self.source_var.get().strip()
        destination_text = self.destination_var.get().strip() or source_text
        if not source_text:
            raise ValueError("请先选择源文件夹")
        source = Path(source_text).expanduser()
        destination = Path(destination_text).expanduser()
        if not source.is_dir():
            raise ValueError("源文件夹不存在或不可访问")
        if not destination.exists():
            destination.mkdir(parents=True, exist_ok=True)
        try:
            index = int(self.index_var.get())
            if index < 1:
                raise ValueError
        except ValueError:
            raise ValueError("“取第几段”必须是大于 0 的整数")
        extensions = set()
        for value in self.extensions_var.get().split(","):
            value = value.strip().lower().lstrip(".")
            if value:
                extensions.add(value)
        return source, destination, index, extensions

    @staticmethod
    def _iter_files(source, recursive):
        iterator = source.rglob("*") if recursive else source.iterdir()
        for path in iterator:
            if not path.is_file():
                continue
            if path.name.startswith("~$"):
                continue
            yield path

    @staticmethod
    def _extract_group(path, index, separator, pattern):
        stem = path.stem
        if pattern:
            try:
                match = re.search(pattern, stem)
            except re.error as exc:
                raise ValueError(f"正则规则无效：{exc}")
            if not match:
                return ""
            if match.lastindex:
                return match.group(1).strip()
            return match.group(0).strip()
        if not separator:
            raise ValueError("分隔符不能为空；或改用正则规则")
        parts = stem.split(separator)
        return parts[index - 1].strip() if len(parts) >= index else ""

    def _scan_config(self):
        source, destination, index, extensions = self._read_options()
        pattern = self.regex_var.get().strip()
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"正则规则无效：{exc}") from exc
        return {
            "source": source,
            "destination": destination,
            "index": index,
            "extensions": extensions,
            "recursive": self.recursive_var.get(),
            "include_unmatched": self.keep_empty_var.get(),
            "separator": self.separator_var.get(),
            "pattern": pattern,
        }

    @staticmethod
    def _safe_group_name(group):
        name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", group).strip(" .") or "未命名"
        if name.upper() in WINDOWS_RESERVED_NAMES:
            name = f"_{name}"
        return name

    def _scan_files(self, config):
        source = config["source"]
        destination = config["destination"]
        groups = {}
        unmatched = []
        for path in self._iter_files(source, config["recursive"]):
            if config["extensions"] and path.suffix.lower().lstrip(".") not in config["extensions"]:
                continue
            group = self._extract_group(path, config["index"], config["separator"], config["pattern"])
            if not group:
                unmatched.append(path)
                if not config["include_unmatched"]:
                    continue
                group = "未匹配"
            # Prevent path traversal and invalid Windows folder names.
            group = self._safe_group_name(group)
            try:
                if path.parent.resolve() == (destination / group).resolve():
                    continue
            except OSError:
                pass
            groups.setdefault(group, []).append(FileItem(path, group))
        return source, destination, groups, unmatched

    def scan(self):
        if self.busy:
            return
        try:
            config = self._scan_config()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.busy = True
        self.status_var.set("正在扫描，请稍候…")
        self.summary_var.set("扫描中")
        threading.Thread(target=self._scan_worker, args=(config,), daemon=True).start()

    def _scan_worker(self, config):
        try:
            source, destination, groups, unmatched = self._scan_files(config)
            self.log_queue.put(("scan_ok", (source, destination, groups, unmatched)))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))

    def _populate_preview(self, groups, destination):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for group in sorted(groups, key=str.casefold):
            files = groups[group]
            target = destination / group
            state = "已存在" if target.exists() else "将创建"
            parent = self.tree.insert("", "end", text=group, values=(state, len(files), str(target)), open=False)
            for item in sorted(files, key=lambda x: x.source.name.casefold()):
                self.tree.insert(parent, "end", text=item.source.name, values=("文件", "", str(item.source)))

    def organize(self):
        if self.busy:
            return
        if not self.groups:
            messagebox.showinfo(APP_TITLE, "请先扫描预览，确认分组后再开始整理。")
            return
        total = sum(len(files) for files in self.groups.values())
        overwrite_warning = "\n\n注意：覆盖掉的原文件无法通过撤销恢复。" if self.conflict_var.get() == "覆盖已有文件" else ""
        if not messagebox.askyesno(APP_TITLE, f"将整理 {total} 个文件到 {len(self.groups)} 个文件夹，是否继续？{overwrite_warning}"):
            return
        self.busy = True
        self.status_var.set("正在整理文件，请稍候…")
        destination = Path(self.destination_var.get().strip() or self.source_var.get().strip()).expanduser()
        conflict_label = self.conflict_var.get()
        self.last_used_overwrite = conflict_label == "覆盖已有文件"
        groups = {name: list(files) for name, files in self.groups.items()}
        threading.Thread(target=self._organize_worker, args=(destination, conflict_label, groups), daemon=True).start()

    def _organize_worker(self, destination, conflict_label, groups):
        manifest = []
        moved = skipped = failed = 0
        try:
            for group in sorted(groups, key=str.casefold):
                target_dir = destination / group
                target_dir.mkdir(parents=True, exist_ok=True)
                for item in groups[group]:
                    target = target_dir / item.source.name
                    try:
                        if item.source.resolve() == target.resolve():
                            skipped += 1
                            continue
                        if target.exists():
                            if conflict_label == "覆盖已有文件":
                                target.unlink()
                            elif conflict_label == "自动改名":
                                target = self._unique_path(target)
                            else:
                                skipped += 1
                                continue
                        shutil.move(str(item.source), str(target))
                        manifest.append({"source": str(item.source), "target": str(target)})
                        moved += 1
                    except OSError:
                        failed += 1
            self.last_manifest = manifest
            self.log_queue.put(("organize_ok", (moved, skipped, failed)))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))

    @staticmethod
    def _unique_path(path):
        counter = 1
        while True:
            candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def undo_last(self):
        if self.busy:
            return
        if not self.last_manifest:
            messagebox.showinfo(APP_TITLE, "没有可撤销的整理记录。")
            return
        if not messagebox.askyesno(APP_TITLE, f"将尝试还原 {len(self.last_manifest)} 个文件，是否继续？"):
            return
        restored = failed = 0
        for record in reversed(self.last_manifest):
            source = Path(record["source"])
            target = Path(record["target"])
            try:
                if target.exists() and not source.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target), str(source))
                    restored += 1
            except OSError:
                failed += 1
        self.last_manifest = []
        self.last_used_overwrite = False
        messagebox.showinfo(APP_TITLE, f"撤销完成：还原 {restored} 个文件" + (f"，失败 {failed} 个。" if failed else "。"))
        self.scan()

    def clear_preview(self):
        self.groups = {}
        self.items = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_var.set("请选择源文件夹，然后点击“扫描预览”")
        self.summary_var.set("尚未扫描")

    def _drain_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                self.busy = False
                if kind == "error":
                    messagebox.showerror(APP_TITLE, payload)
                    self.status_var.set("操作失败")
                    self.summary_var.set("请检查设置")
                elif kind == "scan_ok":
                    source, destination, groups, unmatched = payload
                    self.groups = groups
                    self._populate_preview(groups, destination)
                    count = sum(len(files) for files in groups.values())
                    self.status_var.set("扫描完成，可检查预览并开始整理")
                    unmatched_text = f"，未匹配 {len(unmatched)} 个" if unmatched else ""
                    self.summary_var.set(f"{len(groups)} 个分组，{count} 个文件{unmatched_text}")
                elif kind == "organize_ok":
                    moved, skipped, failed = payload
                    self.status_var.set("整理完成")
                    self.summary_var.set(f"已移动 {moved} 个，跳过 {skipped} 个，失败 {failed} 个")
                    undo_text = "已移动文件可撤销；被覆盖的原文件无法恢复。" if self.last_used_overwrite else "如需恢复，可点击“撤销上次整理”。"
                    messagebox.showinfo(APP_TITLE, f"整理完成！\n\n已移动：{moved} 个\n跳过：{skipped} 个\n失败：{failed} 个\n\n{undo_text}")
                    self.scan()
        except queue.Empty:
            pass
        self.after(120, self._drain_log_queue)


if __name__ == "__main__":
    app = OrganizerApp()
    app.mainloop()
