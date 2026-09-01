# -*- coding: utf-8 -*-
"""
Study AI -- a teaching-first, fully local knowledge framework.

Builder side starts with ONLY common Chinese characters + symbols (zero knowledge).
A developer chats to teach it; it records, extracts and summarizes knowledge.
`build study` packages all history into a .study file the client can load.
Pure local heuristics, zero external dependencies, all CLI output in English.

Study AI —— 一个「教学式」的纯本地知识框架。
构建端从「只有中文常用字 + 符号」的空壳起步，开发者对话灌知识，
它自动记录、抽取、总结；`build study` 把全部历史打包成 .study；
客户端加载 .study 检索使用。纯本地启发式，无外部依赖，CLI 全英文输出。
"""

import sys
import os
import json
import gzip
import struct
import hashlib
import time
import string
from collections import Counter
from typing import List, Dict, Any, Optional, Set

VERSION = "1.0.0"
STUDY_MAGIC = b"STUDYAI\x01"
SUPPORTED_STUDY_VERSION = 1

# ---------------------------------------------------------------- ANSI theme
# Dark theme: bright colors on dark background.
# Light theme: darker, readable colors on white background.
_THEME = {
    "dark": {
        "prompt": "\033[96m",   # cyan
        "info": "\033[94m",     # blue
        "ok": "\033[92m",       # green
        "warn": "\033[93m",     # yellow
        "hint": "\033[90m",     # gray
        "reset": "\033[0m",
    },
    "light": {
        "prompt": "\033[34m",   # blue
        "info": "\033[30m",     # black
        "ok": "\033[32m",       # green
        "warn": "\033[33m",     # orange/brown
        "hint": "\033[90m",     # gray
        "reset": "\033[0m",
    },
}


def _color(theme: str, text: str, kind: str) -> str:
    pal = _THEME.get(theme, _THEME["dark"])
    return pal.get(kind, "") + text + pal["reset"]


def _t(theme: str, msg: str, kind: str = "info") -> str:
    return _color(theme, msg, kind)


# ---------------------------------------------------------------- base vocab
_CJK_PUNCT = "，。！？；：、„“”‘’（）《》【】〈〉「」『』—…·～@#%&*+=<>|/\\"
_ASCII_SYMBOLS = string.digits + string.ascii_letters + string.punctuation + " \t\n"
SYMBOLS = _ASCII_SYMBOLS + _CJK_PUNCT

_BASE_CHARS_CACHE: Optional[str] = None


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF)


def base_chinese_chars() -> str:
    """Return GB2312 level-1 (一级) Chinese characters -- the canonical 常用字 set.

    Decoded deterministically from GB2312 lead rows 0xB0..0xD7, so we never have
    to hand-type thousands of characters (no typo risk)."""
    chars: List[str] = []
    for lead in range(0xB0, 0xD8):           # GB2312 rows covering level-1 hanzi
        for trail in range(0xA1, 0xFF):
            try:
                ch = bytes([lead, trail]).decode("gb2312")
            except Exception:
                continue
            if _is_cjk(ch):
                chars.append(ch)
    return "".join(chars)


def base_vocab() -> str:
    global _BASE_CHARS_CACHE
    if _BASE_CHARS_CACHE is None:
        _BASE_CHARS_CACHE = base_chinese_chars() + SYMBOLS
    return _BASE_CHARS_CACHE


def vocab_hash() -> str:
    return hashlib.sha256(base_vocab().encode("utf-8")).hexdigest()


def vocab_coverage(text: str) -> float:
    v = base_vocab()
    if not text:
        return 0.0
    known = sum(1 for c in text if c in v)
    return known / len(text)


# ---------------------------------------------------------------- knowledge
def cjk_bigrams(text: str) -> Set[str]:
    chars = [c for c in text if _is_cjk(c)]
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def _split_sentences(text: str) -> List[str]:
    out: List[str] = []
    buf: List[str] = []
    for ch in text:
        buf.append(ch)
        if ch in "。！？!?；;\n":
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _keyword_density(s: str) -> float:
    bg = cjk_bigrams(s)
    return len(bg) / max(1, len(s))


class KnowledgeEntry:
    """A single extracted knowledge unit: raw text + sentences + bigrams + summary."""

    def __init__(self, eid: int, raw: str):
        self.id = eid
        self.raw = raw
        self.sentences = _split_sentences(raw)
        self.bigrams = cjk_bigrams(raw)
        self.summary = self._make_summary()

    def _make_summary(self) -> str:
        if not self.sentences:
            return self.raw.strip()[:200]
        scored = sorted(self.sentences, key=_keyword_density, reverse=True)
        top_n = max(1, min(5, (len(scored) // 3) or 1))
        return " ".join(scored[:top_n])

    def top_keywords(self, n: int = 8) -> List[str]:
        c = Counter(self.bigrams)
        return [b for b, _ in c.most_common(n)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw": self.raw,
            "sentences": self.sentences,
            "bigrams": sorted(self.bigrams),
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeEntry":
        e = cls.__new__(cls)
        e.id = d["id"]
        e.raw = d["raw"]
        e.sentences = d.get("sentences") or _split_sentences(d["raw"])
        e.bigrams = set(d.get("bigrams") or cjk_bigrams(d["raw"]))
        e.summary = d.get("summary") or ""
        if not e.summary:
            e.summary = e._make_summary()
        return e


# ---------------------------------------------------------------- study model
class Study:
    def __init__(self, name: str):
        self.name = name
        self.created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.builder = VERSION
        self.base_chars = len(base_chinese_chars())
        self.vocab_hash = vocab_hash()
        self.knowledge: List[KnowledgeEntry] = []
        self.history: List[Dict[str, Any]] = []

    def add_turn(self, role: str, text: str) -> None:
        self.history.append({
            "role": role,
            "text": text,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def add_knowledge(self, raw: str) -> KnowledgeEntry:
        e = KnowledgeEntry(len(self.knowledge), raw)
        self.knowledge.append(e)
        return e

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "version": SUPPORTED_STUDY_VERSION,
            "name": self.name,
            "created": self.created,
            "builder": self.builder,
            "base_chars": self.base_chars,
            "vocab_hash": self.vocab_hash,
            "knowledge": [e.to_dict() for e in self.knowledge],
            "history": self.history,
        }
        payload["checksum"] = _checksum(payload)
        return payload

    @classmethod
    def from_payload(cls, p: Dict[str, Any]) -> "Study":
        if p.get("checksum") != _checksum(p):
            raise ValueError("checksum mismatch: .study file may be corrupted")
        if p.get("version", 0) > SUPPORTED_STUDY_VERSION:
            raise ValueError("unsupported .study version: %s" % p.get("version"))
        s = cls.__new__(cls)
        s.name = p["name"]
        s.created = p.get("created", "")
        s.builder = p.get("builder", "?")
        s.base_chars = p.get("base_chars", 0)
        s.vocab_hash = p.get("vocab_hash", "")
        s.history = p.get("history", [])
        s.knowledge = [KnowledgeEntry.from_dict(d) for d in p.get("knowledge", [])]
        return s


def _checksum(payload: Dict[str, Any]) -> str:
    cp = dict(payload)
    cp.pop("checksum", None)
    raw = json.dumps(cp, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_study(path: str, study: Study) -> None:
    payload = study.to_payload()
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    comp = gzip.compress(data, 9)
    with open(path, "wb") as f:
        f.write(STUDY_MAGIC)
        f.write(struct.pack("<I", len(comp)))
        f.write(comp)


def read_study(path: str) -> Study:
    if not os.path.exists(path):
        raise FileNotFoundError("study file not found: %s" % path)
    with open(path, "rb") as f:
        magic = f.read(len(STUDY_MAGIC))
        if magic != STUDY_MAGIC:
            raise ValueError("not a valid .study file (bad magic header)")
        (clen,) = struct.unpack("<I", f.read(4))
        comp = f.read(clen)
        if len(comp) != clen:
            raise ValueError("truncated .study file (length mismatch)")
        data = gzip.decompress(comp)
    payload = json.loads(data.decode("utf-8"))
    return Study.from_payload(payload)


# ---------------------------------------------------------------- retrieval
def retrieve(study: Study, query: str, top_k: int = 3) -> List[KnowledgeEntry]:
    q = cjk_bigrams(query)
    if not q:
        return []
    scored = []
    for e in study.knowledge:
        overlap = len(q & e.bigrams)
        if overlap > 0:
            scored.append((overlap, e))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    return [e for _, e in scored[:top_k]]


# ---------------------------------------------------------------- prompts
def _prompt(theme: str, role: str = "builder") -> str:
    if role == "client":
        return _color(theme, "StudyAI:client> ", "prompt")
    return _color(theme, "StudyAI:builder> ", "prompt")


def _print_summary(study: Study, theme: str) -> None:
    if not study.knowledge:
        print(_t(theme, "No knowledge learned yet.", "hint"))
        return
    all_bg: Counter = Counter()
    for e in study.knowledge:
        all_bg.update(e.bigrams)
    print(_t(theme, "Current knowledge summary (%d units):" % len(study.knowledge), "info"))
    for kw, _ in all_bg.most_common(12):
        print(_color(theme, "  - " + kw, "ok"))
    print(_t(theme, "Vocab coverage of learned text: %.1f%%" %
               (100.0 * vocab_coverage(" ".join(e.raw for e in study.knowledge))), "hint"))


# ---------------------------------------------------------------- builder REPL
def run_builder(name: str, output: Optional[str], theme: str, resume: Optional[str]) -> None:
    if resume:
        study = read_study(resume)
        print(_t(theme, "Resumed study '%s' with %d knowledge unit(s)." %
                 (study.name, len(study.knowledge)), "info"))
    else:
        study = Study(name)
        print(_t(theme, "StudyAI builder started. It knows %d base characters and ZERO knowledge." %
                 study.base_chars, "info"))
    print(_t(theme, "Teach it by typing. Commands: 'build study', 'status', 'summary', 'exit'.", "hint"))

    while True:
        try:
            line = input(_prompt(theme, "builder"))
        except EOFError:
            print()
            break
        if not line.strip():
            continue
        cmd = line.strip().lower()
        if cmd in ("exit", "quit"):
            break
        if cmd == "status":
            cov = 0.0
            if study.knowledge:
                cov = 100.0 * vocab_coverage(" ".join(e.raw for e in study.knowledge))
            print(_t(theme, "Turns: %d | Knowledge units: %d | Vocab: %d chars | Coverage: %.1f%%"
                     % (len(study.history), len(study.knowledge), study.base_chars, cov), "info"))
            continue
        if cmd == "summary":
            _print_summary(study, theme)
            continue
        if cmd == "build study":
            path = output or (study.name + ".study")
            write_study(path, study)
            print(_t(theme, "Built .study -> %s (%d unit(s), %d turn(s))"
                     % (path, len(study.knowledge), len(study.history)), "ok"))
            cont = input(_t(theme, "Continue teaching? (y/n) ", "hint")).strip().lower()
            if cont in ("n", "no", "q"):
                break
            continue
        # Normal teaching turn: record + learn + summarize.
        study.add_turn("developer", line)
        e = study.add_knowledge(line)
        study.add_turn("studyai", "[learned unit #%d]" % e.id)
        kw = ", ".join(e.top_keywords(6)) or "-"
        print(_t(theme, "Recorded. Extracted %d sentence(s). Key terms: %s"
                 % (len(e.sentences), kw), "ok"))

    if study.knowledge and not output:
        print(_t(theme, "Tip: run 'build study' next time to export a .study file.", "hint"))


# ---------------------------------------------------------------- client REPL
def run_client(path: str, theme: str) -> None:
    study = read_study(path)
    print(_t(theme, "StudyAI client loaded '%s' (%d knowledge unit(s), built %s by v%s)."
             % (study.name, len(study.knowledge), study.created, study.builder), "info"))
    if study.vocab_hash and study.vocab_hash != vocab_hash():
        print(_t(theme, "Warning: base vocabulary differs from this client version; retrieval may vary.", "warn"))

    while True:
        try:
            q = input(_prompt(theme, "client"))
        except EOFError:
            print()
            break
        if not q.strip():
            continue
        cmd = q.strip().lower()
        if cmd in ("exit", "quit"):
            break
        if cmd == "info":
            print(_t(theme, "Name: %s | Units: %d | Built: %s | Builder: %s"
                     % (study.name, len(study.knowledge), study.created, study.builder), "info"))
            continue
        if cmd == "list":
            if not study.knowledge:
                print(_t(theme, "No knowledge units.", "hint"))
            for e in study.knowledge:
                print(_t(theme, "#%d  %s" % (e.id, e.summary[:60]), "info"))
            continue
        hits = retrieve(study, q)
        if not hits:
            print(_t(theme, "No relevant knowledge found in this .study file.", "warn"))
            continue
        for e in hits:
            print(_t(theme, "[Match #%d] %s" % (e.id, e.summary), "ok"))
            print("    " + e.raw)


# ---------------------------------------------------------------- CLI entry
def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="studyai",
        description="Study AI -- a teaching-first, fully local knowledge framework",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("builder", help="build a .study knowledge file")
    b.add_argument("--name", default="my-study", help="study name (default: my-study)")
    b.add_argument("--output", "-o", default=None, help="output .study path for 'build study'")
    b.add_argument("--resume", default=None, help="resume an existing .study file")
    b.add_argument("--theme", choices=["dark", "light"], default="dark", help="UI theme")

    c = sub.add_parser("client", help="use a .study knowledge file")
    c.add_argument("--file", "-f", required=True, help="path to a .study file")
    c.add_argument("--theme", choices=["dark", "light"], default="dark", help="UI theme")

    args = p.parse_args(argv)
    if args.cmd == "builder":
        run_builder(args.name, args.output, args.theme, args.resume)
    else:
        run_client(args.file, args.theme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
