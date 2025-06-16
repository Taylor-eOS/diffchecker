import tkinter as tk
from tkinter import ttk
import difflib

class DiffCheckerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Diff Checker")
        self.root.attributes("-zoomed", True)
        self.left_map = []
        self.right_map = []
        self.setup_widgets()
        self.root.mainloop()

    def setup_widgets(self):
        self.left_frame = ttk.Frame(self.root)
        self.right_frame = ttk.Frame(self.root)
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame.pack(side="right", fill="both", expand=True)
        self.left_text = tk.Text(self.left_frame, wrap="none")
        self.right_text = tk.Text(self.right_frame, wrap="none")
        self.left_scroll_y = ttk.Scrollbar(
            self.left_frame,
            orient="vertical",
            command=self._on_scroll_both_y)
        self.right_scroll_y = ttk.Scrollbar(
            self.right_frame,
            orient="vertical",
            command=self._on_scroll_both_y)
        self.left_scroll_x = ttk.Scrollbar(
            self.left_frame,
            orient="horizontal",
            command=self.left_text.xview)
        self.right_scroll_x = ttk.Scrollbar(
            self.right_frame,
            orient="horizontal",
            command=self.right_text.xview)
        self.left_text.configure(
            yscrollcommand=self.left_scroll_y.set,
            xscrollcommand=self.left_scroll_x.set)
        self.right_text.configure(
            yscrollcommand=self.right_scroll_y.set,
            xscrollcommand=self.right_scroll_x.set)
        self.left_scroll_y.pack(side="right", fill="y")
        self.left_scroll_x.pack(side="bottom", fill="x")
        self.left_text.pack(side="left", fill="both", expand=True)
        self.right_scroll_y.pack(side="right", fill="y")
        self.right_scroll_x.pack(side="bottom", fill="x")
        self.right_text.pack(side="left", fill="both", expand=True)
        for widget in (self.left_text, self.right_text):
            widget.bind("<Control-a>", self.select_all)
            widget.bind("<Control-A>", self.select_all)
            widget.bind("<Control-c>", self.copy_selection)
            widget.bind("<Control-C>", self.copy_selection)
            widget.bind("<Control-v>", self.default_paste)
            widget.bind("<Control-V>", self.default_paste)
        self.left_text.bind("<MouseWheel>", self._on_mousewheel)
        self.right_text.bind("<MouseWheel>", self._on_mousewheel)
        self.left_text.bind("<Button-4>", self._on_linux_scroll)
        self.left_text.bind("<Button-5>", self._on_linux_scroll)
        self.right_text.bind("<Button-4>", self._on_linux_scroll)
        self.right_text.bind("<Button-5>", self._on_linux_scroll)
        self.compare_button = ttk.Button(
            self.root,
            text="Compare",
            command=self.compare_texts)
        self.compare_button.place(relx=0.5, rely=0.01, anchor="n")
        for widget in (self.left_text, self.right_text):
            widget.bind("<Control-v>", self._paste_handler)
            widget.bind("<Control-V>", self._paste_handler)

    def select_all(self, event):
        widget = event.widget
        widget.focus_set()
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "1.0")
        return "break"

    def default_paste(self, event):
        event.widget.event_generate("<<Paste>>")
        return "break"

    def _paste_handler(self, event):
        w = event.widget
        try:
            txt = w.clipboard_get()
        except tk.TclError:
            return "break"
        # replace any selection
        if w.tag_ranges("sel"):
            w.delete("sel.first", "sel.last")
        w.insert("insert", txt)
        return "break"

    def copy_selection(self, event):
        widget = event.widget
        try:
            sel_start = widget.index("sel.first")
            sel_end = widget.index("sel.last")
        except tk.TclError:
            return "break"
        start_line = int(sel_start.split(".")[0])
        end_line = int(sel_end.split(".")[0])
        if widget is self.left_text:
            mapping = self.left_map
            original_lines = self.left_original_lines
        else:
            mapping = self.right_map
            original_lines = self.right_original_lines
        copied = []
        for aligned_idx in range(start_line - 1, end_line):
            orig_idx = mapping[aligned_idx]
            if orig_idx is not None:
                copied.append(original_lines[orig_idx])
        text_to_copy = "\n".join(copied)
        self.root.clipboard_clear()
        self.root.clipboard_append(text_to_copy)
        return "break"

    def _on_scroll_both_y(self, *args):
        self.left_text.yview(*args)
        self.right_text.yview(*args)
        self.left_scroll_y.set(*self.left_text.yview())
        self.right_scroll_y.set(*self.right_text.yview())

    def _on_mousewheel(self, event):
        move = -1 * (event.delta // 120)
        self.left_text.yview_scroll(move, "units")
        self.right_text.yview_scroll(move, "units")
        self.left_scroll_y.set(*self.left_text.yview())
        self.right_scroll_y.set(*self.right_text.yview())
        return "break"

    def _on_linux_scroll(self, event):
        move = -1 if event.num == 4 else 1
        self.left_text.yview_scroll(move, "units")
        self.right_text.yview_scroll(move, "units")
        self.left_scroll_y.set(*self.left_text.yview())
        self.right_scroll_y.set(*self.right_text.yview())
        return "break"

    def clear_highlights(self):
        for text in (self.left_text, self.right_text):
            for tag in text.tag_names():
                text.tag_delete(tag)

    def compare_texts(self):
        self.clear_highlights()
        self.left_original_lines = self.left_text.get("1.0", "end-1c").splitlines()
        self.right_original_lines = self.right_text.get("1.0", "end-1c").splitlines()
        aligned_left, aligned_right, aligned_norm_left, aligned_norm_right, left_map, right_map = self._align_lines()
        self.left_map, self.right_map = left_map, right_map
        self._render_lines(aligned_left, aligned_right)
        self._apply_highlighting(aligned_left, aligned_right, aligned_norm_left, aligned_norm_right)

    def _align_lines(self):
        left_norm = [l.replace(" ", "") for l in self.left_original_lines]
        right_norm = [l.replace(" ", "") for l in self.right_original_lines]
        matcher = difflib.SequenceMatcher(None, left_norm, right_norm)
        al, ar, anl, anr, lm, rm = [], [], [], [], [], []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    al.append(self.left_original_lines[i1 + k])
                    ar.append(self.right_original_lines[j1 + k])
                    norm = left_norm[i1 + k]
                    anl.append(norm); anr.append(norm)
                    lm.append(i1 + k); rm.append(j1 + k)
            else:
                left_seg = self.left_original_lines[i1:i2]
                right_seg = self.right_original_lines[j1:j2]
                ln_seg = left_norm[i1:i2]
                rn_seg = right_norm[j1:j2]
                m = max(len(left_seg), len(right_seg))
                for k in range(m):
                    if k < len(left_seg):
                        al.append(left_seg[k]); anl.append(ln_seg[k]); lm.append(i1 + k)
                    else:
                        al.append(""); anl.append(""); lm.append(None)
                    if k < len(right_seg):
                        ar.append(right_seg[k]); anr.append(rn_seg[k]); rm.append(j1 + k)
                    else:
                        ar.append(""); anr.append(""); rm.append(None)
        return al, ar, anl, anr, lm, rm

    def _render_lines(self, aligned_left, aligned_right):
        self.left_text.delete("1.0", "end"); self.right_text.delete("1.0", "end")
        for ln in aligned_left: self.left_text.insert("end", ln + "\n")
        for ln in aligned_right: self.right_text.insert("end", ln + "\n")

    def _apply_highlighting(self, aligned_left, aligned_right, aligned_norm_left, aligned_norm_right):
        for i, (l, r, nl, nr) in enumerate(zip(aligned_left, aligned_right, aligned_norm_left, aligned_norm_right)):
            if nl == nr: 
                continue
            ls, le = f"{i+1}.0", f"{i+1}.end"; rs, re = ls, le
            if not l:
                self.left_text.tag_add("left_gap", ls, le); self.right_text.tag_add("right_ins", rs, re)
            elif not r:
                self.left_text.tag_add("left_del", ls, le); self.right_text.tag_add("right_gap", rs, re)
            else:
                self.left_text.tag_add("left_diff", ls, le); self.right_text.tag_add("right_diff", rs, re)
        cfg = self.left_text.tag_config
        cfg("left_diff", background="#FFC0C0"); cfg("left_del", background="#FFD0D0"); cfg("left_gap", background="#F0F0F0")
        cfg = self.right_text.tag_config
        cfg("right_diff", background="#C0FFC0"); cfg("right_ins", background="#D0FFD0"); cfg("right_gap", background="#F0F0F0")

if __name__ == "__main__":
    DiffCheckerApp()

