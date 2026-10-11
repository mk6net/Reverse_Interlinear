#!/usr/bin/env python3
"""
interlinear.py - word-by-word Strong's numbers for any Bible verse, KJV first.

Everything is read from local files (no network). On first run the script builds
an SQLite index (about 1-2 minutes); later lookups are instant.

Run  `interlinear.py -h`  for full usage.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import textwrap
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

INDEX_VERSION = "4"

# --------------------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------------------
# (osis, display name, STEPBible codes, USFM code, extra user aliases)
BOOKS = [
    ("Gen", "Genesis", ["Gen"], "GEN", ["gn", "ge"]),
    ("Exod", "Exodus", ["Exo"], "EXO", ["ex", "exo"]),
    ("Lev", "Leviticus", ["Lev"], "LEV", ["lv", "le"]),
    ("Num", "Numbers", ["Num"], "NUM", ["nm", "nu"]),
    ("Deut", "Deuteronomy", ["Deu"], "DEU", ["dt", "de"]),
    ("Josh", "Joshua", ["Jos"], "JOS", ["jsh", "jos"]),
    ("Judg", "Judges", ["Jdg"], "JDG", ["jg", "jdgs"]),
    ("Ruth", "Ruth", ["Rut"], "RUT", ["rth", "ru"]),
    ("1Sam", "1 Samuel", ["1Sa"], "1SA", ["1sm", "1s"]),
    ("2Sam", "2 Samuel", ["2Sa"], "2SA", ["2sm", "2s"]),
    ("1Kgs", "1 Kings", ["1Ki"], "1KI", ["1kg", "1kgs", "1k"]),
    ("2Kgs", "2 Kings", ["2Ki"], "2KI", ["2kg", "2kgs", "2k"]),
    ("1Chr", "1 Chronicles", ["1Ch"], "1CH", ["1chron"]),
    ("2Chr", "2 Chronicles", ["2Ch"], "2CH", ["2chron"]),
    ("Ezra", "Ezra", ["Ezr"], "EZR", []),
    ("Neh", "Nehemiah", ["Neh"], "NEH", ["ne"]),
    ("Esth", "Esther", ["Est"], "EST", ["es"]),
    ("Job", "Job", ["Job"], "JOB", ["jb"]),
    ("Ps", "Psalms", ["Psa"], "PSA", ["psalm", "pss", "psm", "pslm"]),
    ("Prov", "Proverbs", ["Pro"], "PRO", ["pr", "prv"]),
    ("Eccl", "Ecclesiastes", ["Ecc"], "ECC", ["ec", "qoh"]),
    ("Song", "Song of Solomon", ["Sng", "Song"], "SNG", ["sos", "songofsongs", "canticles", "ss"]),
    ("Isa", "Isaiah", ["Isa"], "ISA", ["is"]),
    ("Jer", "Jeremiah", ["Jer"], "JER", ["je", "jr"]),
    ("Lam", "Lamentations", ["Lam"], "LAM", ["la"]),
    ("Ezek", "Ezekiel", ["Ezk", "Ezek"], "EZK", ["eze", "ezk"]),
    ("Dan", "Daniel", ["Dan"], "DAN", ["dn", "da"]),
    ("Hos", "Hosea", ["Hos"], "HOS", ["ho"]),
    ("Joel", "Joel", ["Jol", "Joel"], "JOL", ["jl"]),
    ("Amos", "Amos", ["Amo"], "AMO", ["am"]),
    ("Obad", "Obadiah", ["Oba"], "OBA", ["ob"]),
    ("Jonah", "Jonah", ["Jon"], "JON", ["jnh"]),
    ("Mic", "Micah", ["Mic"], "MIC", ["mc"]),
    ("Nah", "Nahum", ["Nam", "Nah"], "NAM", ["na"]),
    ("Hab", "Habakkuk", ["Hab"], "HAB", ["hb"]),
    ("Zeph", "Zephaniah", ["Zep"], "ZEP", ["zp"]),
    ("Hag", "Haggai", ["Hag"], "HAG", ["hg"]),
    ("Zech", "Zechariah", ["Zec"], "ZEC", ["zc"]),
    ("Mal", "Malachi", ["Mal"], "MAL", ["ml"]),
    ("Matt", "Matthew", ["Mat"], "MAT", ["mt"]),
    ("Mark", "Mark", ["Mrk"], "MRK", ["mk", "mr"]),
    ("Luke", "Luke", ["Luk"], "LUK", ["lk", "lu"]),
    ("John", "John", ["Jhn"], "JHN", ["jn", "joh"]),
    ("Acts", "Acts", ["Act"], "ACT", ["ac"]),
    ("Rom", "Romans", ["Rom"], "ROM", ["rm", "ro"]),
    ("1Cor", "1 Corinthians", ["1Co"], "1CO", []),
    ("2Cor", "2 Corinthians", ["2Co"], "2CO", []),
    ("Gal", "Galatians", ["Gal"], "GAL", ["ga"]),
    ("Eph", "Ephesians", ["Eph"], "EPH", []),
    ("Phil", "Philippians", ["Php"], "PHP", ["phili", "philip"]),
    ("Col", "Colossians", ["Col"], "COL", []),
    ("1Thess", "1 Thessalonians", ["1Th"], "1TH", ["1thes"]),
    ("2Thess", "2 Thessalonians", ["2Th"], "2TH", ["2thes"]),
    ("1Tim", "1 Timothy", ["1Ti"], "1TI", ["1tm"]),
    ("2Tim", "2 Timothy", ["2Ti"], "2TI", ["2tm"]),
    ("Titus", "Titus", ["Tit"], "TIT", []),
    ("Phlm", "Philemon", ["Phm"], "PHM", ["philem", "phlm"]),
    ("Heb", "Hebrews", ["Heb"], "HEB", []),
    ("Jas", "James", ["Jas"], "JAS", ["jm"]),
    ("1Pet", "1 Peter", ["1Pe"], "1PE", ["1pt", "1p"]),
    ("2Pet", "2 Peter", ["2Pe"], "2PE", ["2pt", "2p"]),
    ("1John", "1 John", ["1Jn"], "1JN", ["1jo", "1jhn"]),
    ("2John", "2 John", ["2Jn"], "2JN", ["2jo", "2jhn"]),
    ("3John", "3 John", ["3Jn"], "3JN", ["3jo", "3jhn"]),
    ("Jude", "Jude", ["Jud"], "JUD", ["jde"]),
    ("Rev", "Revelation", ["Rev"], "REV", ["re", "rv", "apocalypse", "revelations"]),
]
# Apocrypha, in KJV 1611 order (OSIS ids as used by CrossWire KJVA)
APOCRYPHA = [
    ("1Esd", "1 Esdras", [], "1ES", ["1esdr", "3esdras"]),
    ("2Esd", "2 Esdras", [], "2ES", ["4ezra", "4esdras"]),
    ("Tob", "Tobit", [], "TOB", ["tobias", "tb"]),
    ("Jdt", "Judith", [], "JDT", ["jdth"]),
    ("AddEsth", "Additions to Esther", [], "ESG", ["restofesther", "therestofesther", "esthgr", "addest",
                                                  "additionstoesther", "greekesther"]),
    ("Wis", "Wisdom of Solomon", [], "WIS", ["wisdom", "ws", "wisd"]),
    ("Sir", "Sirach", [], "SIR", ["ecclesiasticus", "ecclus", "bensira", "wisdomofsirach"]),
    ("Bar", "Baruch", [], "BAR", []),
    ("EpJer", "Epistle of Jeremy", [], "LJE", ["epistleofjeremiah", "letterofjeremiah", "epjer", "lje"]),
    ("PrAzar", "Song of the Three Children (Prayer of Azariah)", [], "S3Y",
     ["prayerofazariah", "azariah", "songofthethreechildren", "songofthree", "songofthreechildren",
      "threechildren", "prazar", "s3y"]),
    ("Sus", "Susanna", [], "SUS", []),
    ("Bel", "Bel and the Dragon", [], "BEL", ["belandthedragon"]),
    ("PrMan", "Prayer of Manasses", [], "MAN", ["prayerofmanasseh", "prayerofmanasses", "manasseh", "manasses",
                                                 "prman"]),
    ("1Macc", "1 Maccabees", [], "1MA", ["1mac", "1mc", "1ma"]),
    ("2Macc", "2 Maccabees", [], "2MA", ["2mac", "2mc", "2ma"]),
]
APOC_SET = {b[0] for b in APOCRYPHA}
# other OSIS spellings seen in the wild -> ids used here
OSIS_VARIANTS = {"EsthGr": "AddEsth", "AddEst": "AddEsth", "GkEsth": "AddEsth", "1Ma": "1Macc", "2Ma": "2Macc",
                 "1Mac": "1Macc", "2Mac": "2Macc", "SgThree": "PrAzar", "SongThr": "PrAzar", "AddDan": "PrAzar",
                 "Man": "PrMan", "1Es": "1Esd", "2Es": "2Esd", "Tobit": "Tob", "Judith": "Jdt", "Sirach": "Sir",
                 "Wisd": "Wis", "LetJer": "EpJer"}
BOOKS = BOOKS + APOCRYPHA
OSIS_INDEX = {b[0]: i for i, b in enumerate(BOOKS)}           # 0..38 OT, 39..65 NT, 66.. Apocrypha
OSIS_NAME = {b[0]: b[1] for b in BOOKS}
STEP_TO_OSIS = {code: b[0] for b in BOOKS for code in b[2]}
USFM_TO_OSIS = {b[3]: b[0] for b in BOOKS}
OSIS_TO_USFM = {b[0]: b[3] for b in BOOKS}


def is_ot(osis_book: str) -> bool:
    """Hebrew-language Old Testament (not the Apocrypha)."""
    return OSIS_INDEX[osis_book] < 39


def is_apoc(osis_book: str) -> bool:
    return osis_book in APOC_SET


def norm_osis_key(key: str) -> str:
    book, _, rest = key.partition(".")
    book = OSIS_VARIANTS.get(book, book)
    return f"{book}.{rest}" if rest else book


def _key(s: str) -> str:
    s = s.lower().replace(".", "").replace("_", "")
    s = re.sub(r"^(iii|third|3rd)\s*", "3", s)
    s = re.sub(r"^(ii|second|2nd)\s*", "2", s)
    s = re.sub(r"^(i|first|1st)\s+", "1", s)
    return re.sub(r"\s+", "", s)


USER_ALIASES: dict[str, str] = {}
for _b in BOOKS:
    for _a in [_b[0], _b[1], _b[3], *_b[2], *_b[4]]:
        USER_ALIASES.setdefault(_key(_a), _b[0])
# "Jud" is Jude in STEPBible data but people also type it for Judges: refuse to guess.
USER_ALIASES.pop("jud", None)


def resolve_book(raw: str) -> str:
    k = _key(raw)
    if k == "i":  # bare roman numeral with nothing after it
        raise ValueError(f"Unrecognised book: {raw!r}")
    if k in USER_ALIASES:
        return USER_ALIASES[k]
    hits = sorted({b for a, b in USER_ALIASES.items() if a.startswith(k)}, key=OSIS_INDEX.get)
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise ValueError(f"Ambiguous book {raw!r}: could be " + ", ".join(OSIS_NAME[h] for h in hits))
    raise ValueError(f"Unrecognised book: {raw!r}")


REF_RE = re.compile(r"^(?P<book>.+?)\s*(?P<ch>\d+)(?:\s*[:.]\s*(?P<v1>\d+)(?:\s*-\s*(?P<v2>\d+))?)?$")


def parse_reference(words: list[str]) -> tuple[str, int, int | None, int | None]:
    text = " ".join(words).strip()
    m = REF_RE.match(text)
    if not m:
        raise ValueError(f"Could not read reference {text!r}. Example: 1 John 1:1")
    book = resolve_book(m.group("book"))
    ch = int(m.group("ch"))
    v1 = int(m.group("v1")) if m.group("v1") is not None else None
    v2 = int(m.group("v2")) if m.group("v2") is not None else v1
    if v1 is not None and v2 < v1:
        raise ValueError("Verse range ends before it starts.")
    return book, ch, v1, v2


# --------------------------------------------------------------------------------------
# Strong's number helpers
# --------------------------------------------------------------------------------------
STRONG_RE = re.compile(r"([GHgh])0*(\d+)([A-Za-z]?)")


def norm_strong(raw: str) -> tuple[str, str]:
    """'H07225' -> ('H7225',''); 'H7225G' -> ('H7225','G'); 'G0191' -> ('G191','')."""
    m = STRONG_RE.fullmatch(raw.strip())
    if not m:
        return raw.strip(), ""
    return f"{m.group(1).upper()}{int(m.group(2))}", m.group(3)


def strong_sort_key(s: str):
    m = re.match(r"([GH])(\d+)", s)
    return (m.group(1), int(m.group(2))) if m else (s, 0)


# Tags that carry no lexical meaning; ignored when comparing whole-verse sets.
SET_NOISE = {"H853", "G3588"}


# --------------------------------------------------------------------------------------
# Locating data
# --------------------------------------------------------------------------------------
TTESV_NAME = "TTESV - Tyndale Translation tags for ESV - TyndaleHouse.com STEPBible.org CC BY-NC.txt"


def find_data_root(explicit: str | None) -> Path:
    markers = ["kjv-strongs", "STEPBible-Data", "strongs", "bible-db", "HebrewLexicon", "Every-Promise-Thayers"]
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("INTERLINEAR_DATA"):
        candidates.append(Path(os.environ["INTERLINEAR_DATA"]).expanduser())
    candidates += [Path(__file__).resolve().parent, Path.cwd(), Path.home() / "scripts" / "interlinear_tool"]
    for c in candidates:
        if c.is_dir() and any((c / m).exists() for m in markers):
            return c
    return candidates[0] if explicit else Path(__file__).resolve().parent


def first_existing(paths) -> Path | None:
    for p in paths:
        if p and Path(p).is_file():
            return Path(p)
    return None


def discover(root: Path, args) -> dict:
    step = root / "STEPBible-Data"
    s = {}
    s["kjv"] = first_existing([Path(args.kjv_xml).expanduser()] if args.kjv_xml else [
        root / "kjv-strongs" / "kjvfull.xml", root / "kjv-strongs" / "kjv.osis.xml",
        root / "kjvfull.xml", root / "kjv.osis.xml"])
    k06 = [Path(args.kjv2006_xml).expanduser()] if args.kjv2006_xml else (
        sorted(root.glob("kjv2006*.xml")) + sorted(root.glob("*KJV2006*.xml")) +
        sorted((root / "kjv-strongs").glob("kjv2006*.xml")))
    s["kjv2006"] = first_existing(k06)
    s["ttesv"] = first_existing([step / "Tagged-Bibles" / TTESV_NAME] + sorted(step.glob("**/TTESV*.txt")))
    s["tagnt"] = sorted(step.glob("Translators Amalgamated OT+NT/TAGNT*.txt"))
    s["tahot"] = sorted(step.glob("Translators Amalgamated OT+NT/TAHOT*.txt"))
    s["tbesg"] = first_existing(sorted(step.glob("Lexicons/TBESG*.txt")))
    s["tbesh"] = first_existing(sorted(step.glob("Lexicons/TBESH*.txt")))
    s["lsj"] = sorted(step.glob("Lexicons/TFLSJ*.txt"))
    s["byz"] = first_existing([root / "bible-db" / "data" / "greek" / "byz_words.jsonl"])
    s["wlc"] = first_existing([root / "bible-db" / "data" / "hebrew" / "wlc_words.jsonl"])
    s["vmap"] = first_existing([root / "bible-db" / "data" / "versification" / "eng.json"])
    s["strongs_g"] = first_existing([root / "strongs" / "greek" / "StrongsGreekDictionaryXML_1.4" / "strongsgreek.xml"])
    s["strongs_h_osis"] = first_existing([root / "strongs" / "hebrew" / "StrongHebrewG.xml"])
    s["strongs_h"] = first_existing([root / "HebrewLexicon" / "HebrewStrong.xml"])
    s["bdb"] = first_existing([root / "HebrewLexicon" / "BrownDriverBriggs.xml"])
    ub = root / "unabridged-BDB-Hebrew-lexicon"
    s["bdbfull"] = first_existing([ub / "unabridged-BDB-Hebrew-lexicon.csv", ub / "unabridged-BDB-Hebrew-lexicon.csv.zip"])
    s["lexidx"] = first_existing([root / "HebrewLexicon" / "LexicalIndex.xml"])
    s["thayer"] = sorted((root / "Every-Promise-Thayers" / "book").glob("[0-9][0-9]-G*.md"))
    kdir = root / "kjv-strongs"
    s["kjv_apoc"] = [p for p in [kdir / "kjvdc.xml", kdir / "kjva.osis.xml", root / "kjva.osis.xml"] if p.is_file()]
    lxx = root / "LXX-Rahlfs-1935" / "11_end-users_files" / "MyBible"
    s["lxx1"] = first_existing([lxx / "Bibles" / "LXX1.SQLite3"])
    s["lxx2"] = first_existing([lxx / "Bibles" / "LXX2.SQLite3"])
    s["lxxlex"] = first_existing([lxx / "Lexicon" / "HebGrk.dictionary.SQLite3"])
    s["geneva"] = first_existing([root / "public-domain-bibles" / "GENEVA.txt"])
    if not s["geneva"] and (root / "enggnv" / "Genesis").is_dir():
        s["geneva"] = root / "enggnv"
    return s


def fingerprint(paths) -> str:
    if paths is None:
        return "missing"
    if isinstance(paths, (str, Path)):
        paths = [paths]
    expanded = []
    for p in paths:
        if p and Path(p).is_dir():
            expanded += sorted(Path(p).glob("*/*/data"))
        else:
            expanded.append(p)
    paths = expanded
    h = hashlib.sha1(INDEX_VERSION.encode())
    found = False
    for p in paths:
        if p and Path(p).is_file():
            st = Path(p).stat()
            h.update(f"{p}|{st.st_size}|{int(st.st_mtime)}".encode())
            found = True
    return h.hexdigest() if found else "missing"


# --------------------------------------------------------------------------------------
# Index builders
# --------------------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS kjv (src TEXT, verse TEXT, idx INT, kind TEXT, text TEXT, strongs TEXT,
                                morph TEXT, srcpos TEXT, added INT);
CREATE INDEX IF NOT EXISTS kjv_i ON kjv(src, verse);
CREATE TABLE IF NOT EXISTS esv (verse TEXT, idx INT, pos TEXT, strongs TEXT);
CREATE INDEX IF NOT EXISTS esv_i ON esv(verse);
CREATE TABLE IF NOT EXISTS step (verse TEXT, idx INT, wtype TEXT, word TEXT, translit TEXT, english TEXT,
                                 core TEXT, dstrong TEXT, grammar TEXT, gloss TEXT, editions TEXT, alt TEXT);
CREATE INDEX IF NOT EXISTS step_i ON step(verse);
CREATE TABLE IF NOT EXISTS orig (src TEXT, verse TEXT, idx INT, surface TEXT, strongs TEXT);
CREATE INDEX IF NOT EXISTS orig_i ON orig(src, verse);
CREATE TABLE IF NOT EXISTS lex (src TEXT, strong TEXT, sub TEXT, lemma TEXT, translit TEXT, pron TEXT,
                                gloss TEXT, body TEXT, extra TEXT);
CREATE INDEX IF NOT EXISTS lex_i ON lex(src, strong);
CREATE TABLE IF NOT EXISTS lxx (verse TEXT, idx INT, word TEXT, lexid TEXT, morph TEXT, strong TEXT, part TEXT);
CREATE INDEX IF NOT EXISTS lxx_i ON lxx(verse);
CREATE TABLE IF NOT EXISTS geneva (verse TEXT PRIMARY KEY, text TEXT);
CREATE TABLE IF NOT EXISTS rel (a TEXT, b TEXT, why TEXT);
CREATE INDEX IF NOT EXISTS rel_a ON rel(a);
"""


class OsisKJVHandler:
    """Streams a CrossWire-style OSIS Bible; records <w> units and untagged text in order."""

    def __init__(self):
        self.rows: list[tuple] = []
        self.verse = None              # current verse key (OSIS, e.g. 1John.1.1)
        self.container_depth = []      # stack for container-style <verse>
        self.chapter = None
        self.note_depth = 0
        self.added_depth = 0
        self.title_depth = 0           # inside canonical <title>
        self.w = None                  # current <w> attrs + text parts
        self.w_depth = 0
        self.buf: list[str] = []
        self.buf_added = False
        self.counter: dict[str, int] = {}
        self.pending_title: list[tuple] = []

    # target key: canonical psalm titles go to chapter.0
    def _target(self):
        if self.title_depth and self.chapter:
            return f"{self.chapter}.0"
        return self.verse

    def _emit(self, kind, text, strongs="", morph="", srcpos="", added=0):
        key = self._target()
        if not key:
            return
        n = self.counter.get(key, 0)
        self.counter[key] = n + 1
        self.rows.append((key, n, kind, text, strongs, morph, srcpos, added))

    def _flush_text(self):
        if self.buf:
            t = "".join(self.buf)
            if t.strip():
                self._emit("t", re.sub(r"\s+", " ", t).strip(), added=1 if self.buf_added else 0)
            self.buf = []

    def startElement(self, name, attrs):
        tag = name.split(":")[-1]
        if self.note_depth:
            if tag == "note":
                self.note_depth += 1
            return
        if tag == "note":
            self.note_depth = 1
            return
        if tag == "chapter":
            cid = attrs.get("osisID") or attrs.get("sID")
            if cid and not attrs.get("eID"):
                self.chapter = norm_osis_key(cid.split()[0])
            return
        if tag == "verse":
            if attrs.get("eID"):
                self._flush_text()
                self.verse = None
                return
            vid = attrs.get("osisID") or attrs.get("sID")
            if vid:
                self._flush_text()
                self.verse = norm_osis_key(vid.split()[0])
                self.chapter = self.verse.rsplit(".", 1)[0]
                if not attrs.get("sID"):
                    self.container_depth.append(True)
            return
        if tag == "title" and attrs.get("canonical") == "true":
            self._flush_text()
            self.title_depth += 1
            return
        if tag == "transChange":
            self._flush_text()
            self.added_depth += 1
            self.buf_added = True
            return
        if tag == "w":
            self._flush_text()
            if self.w is None:
                self.w = {"lemma": attrs.get("lemma", ""), "morph": attrs.get("morph", ""),
                          "src": attrs.get("src", ""), "text": [], "added": bool(self.added_depth)}
                self.w_depth = 1
            else:
                self.w_depth += 1
            return

    def endElement(self, name):
        tag = name.split(":")[-1]
        if self.note_depth:
            if tag == "note":
                self.note_depth -= 1
            return
        if tag == "verse" and self.container_depth:
            self._flush_text()
            self.container_depth.pop()
            self.verse = None
            return
        if tag == "title" and self.title_depth:
            self._flush_text()
            self.title_depth -= 1
            return
        if tag == "transChange":
            self._flush_text()
            self.added_depth = max(0, self.added_depth - 1)
            self.buf_added = bool(self.added_depth)
            return
        if tag == "w" and self.w is not None:
            self.w_depth -= 1
            if self.w_depth == 0:
                text = re.sub(r"\s+", " ", "".join(self.w["text"])).strip()
                ids = re.findall(r"strong:([GH]\d+[A-Za-z]?)", self.w["lemma"], flags=re.I)
                ids = [norm_strong(i)[0] for i in ids]
                if text or ids:
                    self._emit("w" if ids else "t", text, " ".join(ids), self.w["morph"], self.w["src"],
                               1 if (self.w["added"] or self.added_depth) else 0)
                self.w = None

    def characters(self, content):
        if self.note_depth or not self._target():
            return
        if self.w is not None:
            self.w["text"].append(content)
        else:
            if self.buf and self.buf_added != bool(self.added_depth):
                self._flush_text()
            self.buf_added = bool(self.added_depth)
            self.buf.append(content)


TOKEN_RE = re.compile(r"<!--.*?-->|<\?.*?\?>|<!\[CDATA\[.*?\]\]>|<!DOCTYPE[^>]*>|<[^>]+>|[^<]+", re.S)
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')


def tolerant_osis_parse(path: Path, h: "OsisKJVHandler"):
    """Lenient streaming tokenizer: some OSIS exports (e.g. mod2osis) are not well-formed XML."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        data = f.read()
    for m in TOKEN_RE.finditer(data):
        tok = m.group(0)
        if tok[0] != "<":
            h.characters(html.unescape(tok))
            continue
        if tok.startswith(("<!--", "<?", "<!")):
            continue
        if tok.startswith("</"):
            h.endElement(tok[2:-1].strip())
            continue
        body = tok[1:-1]
        selfclosing = body.endswith("/")
        if selfclosing:
            body = body[:-1]
        name, _, rest = body.strip().partition(" ")
        attrs = {a.group(1): html.unescape(a.group(3) if a.group(3) is not None else a.group(4))
                 for a in ATTR_RE.finditer(rest)}
        h.startElement(name, attrs)
        if selfclosing:
            h.endElement(name)


def build_kjv(con, src_name: str, path: Path, only_books: set | None = None, clear: bool = True):
    if clear:
        con.execute("DELETE FROM kjv WHERE src=?", (src_name,))
    h = OsisKJVHandler()
    tolerant_osis_parse(path, h)
    rows = [(src_name, *r) for r in h.rows
            if only_books is None or r[0].split(".", 1)[0] in only_books]
    con.executemany("INSERT INTO kjv VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def build_kjv_apocrypha(con, paths: list[Path]):
    """Add Apocrypha from kjvdc.xml / kjva.osis.xml unless the main KJV file already had it."""
    con.execute("DELETE FROM kjv WHERE src='kjv' AND (" +
                " OR ".join("verse LIKE ?" for _ in APOC_SET) + ")", [f"{b}.%" for b in APOC_SET])
    for p in paths:
        if build_kjv(con, "kjv", p, only_books=APOC_SET, clear=False):
            return


def build_ttesv(con, path: Path):
    con.execute("DELETE FROM esv")
    rows = []
    line_re = re.compile(r"^\$(\S+)\s+(\d+):(\d+)\t(.*)$")
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            m = line_re.match(line.rstrip("\n"))
            if not m:
                continue
            book = STEP_TO_OSIS.get(m.group(1))
            if not book:
                continue
            key = f"{book}.{int(m.group(2))}.{int(m.group(3))}"
            prefix = "H" if is_ot(book) else "G"
            for i, cell in enumerate(c for c in m.group(4).split("\t") if c.strip()):
                if "=" not in cell:
                    continue
                pos, tags = cell.split("=", 1)
                ids = []
                for inner in re.findall(r"<([^>]*)>", tags):
                    for n in re.findall(r"\d+", inner.split("=")[0]):
                        if len(n) <= 5 and int(n):
                            ids.append(f"{prefix}{int(n)}")
                if ids:
                    rows.append((key, i, pos.strip(), " ".join(ids)))
    con.executemany("INSERT INTO esv VALUES (?,?,?,?)", rows)


STEP_REF_RE = re.compile(
    r"^(?P<b>[1-3]?[A-Za-z]{2,4})\.(?P<c>\d+)\.(?P<v>\d+)(?P<rest>[^#\t]*)#(?P<n>\d+)=(?P<t>[^\t]*)$")


def _step_core_ids(dstrong: str) -> list[str]:
    """Pull the lexical (non-prefix) Strong's numbers out of a STEP dStrongs cell."""
    braced = re.findall(r"\{([GH]\d+[A-Za-z]?)\}", dstrong)
    ids = braced or re.findall(r"[GH]\d+[A-Za-z]?", dstrong)
    out = []
    for i in ids:
        base, _ = norm_strong(i)
        if base.startswith("H") and 9000 <= int(base[1:]) < 9100:   # STEP prefix/suffix codes
            continue
        out.append(base)
    return out


def build_step_texts(con, tagnt: list[Path], tahot: list[Path]):
    con.execute("DELETE FROM step")
    con.execute("DELETE FROM rel WHERE why='STEP alt'")
    rows, rel = [], set()
    counters: dict[str, int] = {}
    for path in [*tagnt, *tahot]:
        nt = "TAGNT" in path.name
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                cols = line.rstrip("\n").split("\t")
                m = STEP_REF_RE.match(cols[0])
                if not m:
                    continue
                book = STEP_TO_OSIS.get(m.group("b"))
                if not book:
                    continue
                ch, vs = int(m.group("c")), int(m.group("v"))
                rest = m.group("rest")
                if nt:
                    kb = re.search(r"\[(\d+)\.(\d+)\]", rest)       # KJV versification in [..]
                    if kb:
                        ch, vs = int(kb.group(1)), int(kb.group(2))
                    word, english, dcell = cols[1], cols[2], cols[3]
                    dstrong, _, grammar = dcell.partition("=")
                    lemma_gloss = cols[4] if len(cols) > 4 else ""
                    editions = cols[5] if len(cols) > 5 else ""
                    alt_cell = cols[12] if len(cols) > 12 else ""
                    translit = ""
                    mm = re.match(r"^(.*?)\s*\((.*)\)\s*$", word)
                    if mm:
                        word, translit = mm.group(1), mm.group(2)
                    gloss = lemma_gloss.partition("=")[2]
                    lemma = lemma_gloss.partition("=")[0]
                    core = _step_core_ids(dstrong)
                else:
                    word, translit, english, dstrong = cols[1], cols[2], cols[3], cols[4]
                    grammar = cols[5] if len(cols) > 5 else ""
                    alt_cell = cols[9] if len(cols) > 9 else ""
                    expanded = cols[11] if len(cols) > 11 else ""
                    em = re.search(r"\{[GH]\d+[A-Za-z]?=([^=}]*)=([^}]*)\}", expanded)
                    lemma = em.group(1) if em else ""
                    gloss = em.group(2) if em else ""
                    editions = ""
                    core = _step_core_ids(dstrong)
                key = f"{book}.{ch}.{vs}"
                alts = sorted({norm_strong(a)[0] for a in re.findall(r"[GH]\d+[A-Za-z]?", alt_cell)} - set(core))
                if len(core) == 1 and len(alts) == 1:     # 1:1 only; multi-word combos add noise
                    rel.add((core[0], alts[0])); rel.add((alts[0], core[0]))
                n = counters.get(key, 0)
                counters[key] = n + 1
                rows.append((key, n, m.group("t"), word.strip(), translit.strip(), english.strip(),
                             " ".join(core), dstrong.strip(), grammar.strip(),
                             f"{lemma.strip()}={gloss.strip()}" if lemma or gloss else "",
                             editions.strip(), " ".join(alts)))
    con.executemany("INSERT INTO step VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO rel VALUES (?,?,'STEP alt')", sorted(rel))


def _load_wlc_canon(vmap: Path | None) -> dict:
    """WLC (Hebrew versification) -> KJV coordinates, after bible-db's versification.py."""
    if not vmap:
        return {}
    mv = json.load(open(vmap, encoding="utf-8"))["mappedVerses"]
    rx = re.compile(r"^(\S+)\s+(\d+):(\d+)(?:-(\d+))?$")

    def expand(ref):
        m = rx.match(ref)
        if not m:
            return None
        a = int(m.group(3)); b = int(m.group(4)) if m.group(4) else a
        return [(m.group(1), int(m.group(2)), v) for v in range(a, b + 1)]

    out = {}
    for canon_ref, org_ref in mv.items():
        if canon_ref.split(" ", 1)[0] not in USFM_TO_OSIS:
            continue
        c, o = expand(canon_ref), expand(org_ref)
        if not c or not o or len(c) != len(o):
            continue
        for (oc, och, ov), (cc, cch, cv) in zip(o, c):
            if oc == cc:
                out[(oc, och, ov)] = (cch, cv)
    title_max = {}
    for (oc, och, ov), (_, cv) in out.items():
        if cv == 0 and ov > title_max.get((oc, och), 0):
            title_max[(oc, och)] = ov
    for (oc, och), vmax in title_max.items():
        for ov in range(1, vmax + 1):
            out[(oc, och, ov)] = (och, 0)
    out[("NUM", 25, 19)] = (26, 1)
    return out


def build_bibledb(con, byz: Path | None, wlc: Path | None, vmap: Path | None):
    con.execute("DELETE FROM orig")
    canon = _load_wlc_canon(vmap)
    rows = []
    counters: dict[str, int] = {}
    for src, path in (("byz", byz), ("wlc", wlc)):
        if not path:
            continue
        prefix = "G" if src == "byz" else "H"
        with open(path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                code = d.get("code")
                book = USFM_TO_OSIS.get(code)
                if not book:
                    continue
                ch, vs = d["chapter"], d["verse"]
                if src == "wlc":
                    ch, vs = canon.get((code, ch, vs), (ch, vs))
                key = f"{book}.{ch}.{vs}"
                ids = " ".join(f"{prefix}{int(s)}" for s in d.get("strong") or [])
                n = counters.get(src + key, 0)
                counters[src + key] = n + 1
                rows.append((src, key, n, d.get("surface", ""), ids))
    con.executemany("INSERT INTO orig VALUES (?,?,?,?,?)", rows)


# KJV Apocrypha -> LXX (Rahlfs) in eliranwong's MyBible modules. (db, book_number, chapter fn, verse fn)
#   KJV follows Theodotion for Susanna/Bel/Song of Three, and the B/A text of Tobit.
LXX_MAP = {
    ("LXX1", 165): "1Esd", ("LXX1", 170): "Tob", ("LXX1", 180): "Jdt", ("LXX1", 270): "Wis",
    ("LXX1", 280): "Sir", ("LXX1", 320): "Bar", ("LXX1", 462): "1Macc", ("LXX1", 464): "2Macc",
    ("LXX2", 325): "Sus", ("LXX2", 345): "Bel",
}
# Additions to Esther: Rahlfs puts each addition inside one Greek verse as lettered sub-verses.
# (greek chapter, greek verse) -> list of KJV (chapter, verse) in order; when the counts differ the
# whole Greek block is attached to every KJV verse of that addition.
ESTHER_ADDITIONS = {
    (1, 1): [(11, v) for v in range(2, 13)] + [(12, v) for v in range(1, 7)],     # Addition A
    (3, 13): [(13, v) for v in range(1, 8)],                                      # B
    (4, 17): [(13, v) for v in range(8, 19)] + [(14, v) for v in range(1, 20)],   # C
    (5, 1): [(15, v) for v in range(1, 17)],                                      # D (5:1a-f + 5:2a-b)
    (5, 2): [(15, v) for v in range(1, 17)],
    (8, 12): [(16, v) for v in range(1, 25)],                                     # E
    (10, 3): [(10, v) for v in range(4, 14)] + [(11, 1)],                         # F
}


def _parse_lxx_text(text: str):
    """MyBible LXX verse -> [(segment_letter, word, lexid, morph, strong)]."""
    out = []
    seg = ""
    for m in re.finditer(r"<i>\[([^\]]*)\]</i>|([^\s<]+)((?:<S>\d+</S>|<m>[^<]*</m>)*)", text):
        if m.group(1) is not None:
            seg = m.group(1)
            continue
        word, tags = m.group(2), m.group(3) or ""
        if not re.search(r"\w", word):
            continue
        nums = re.findall(r"<S>(\d+)</S>", tags)
        morph = re.findall(r"<m>([^<]*)</m>", tags)
        lexid = next((n for n in nums if len(n) == 6 and n.startswith("7")), "")
        strong = next((f"G{int(n)}" for n in nums if len(n) <= 4), "")
        out.append((seg, word, lexid, morph[0].replace("lxx.", "") if morph else "", strong))
    return out


def build_lxx(con, lxx1: Path | None, lxx2: Path | None, lexdb: Path | None):
    con.execute("DELETE FROM lxx")
    rows = []
    counters: dict[str, int] = {}

    def add(key, seg, word, lexid, morph, strong, part=""):
        n = counters.get(key, 0)
        counters[key] = n + 1
        rows.append((key, n, word, lexid, morph, strong, part))

    for label, path in (("LXX1", lxx1), ("LXX2", lxx2)):
        if not path:
            continue
        c = sqlite3.connect(str(path))
        for bn, ch, vs, text in c.execute("SELECT book_number, chapter, verse, text FROM verses"):
            bn, ch, vs = int(bn), int(ch), int(vs)
            words = None
            if (label, bn) in LXX_MAP:
                key = f"{LXX_MAP[(label, bn)]}.{ch}.{vs}"
                for w in _parse_lxx_text(text):
                    add(key, *w)
            elif label == "LXX1" and bn == 315:                       # Epistle of Jeremy = KJV Baruch 6
                for w in _parse_lxx_text(text):           # Rahlfs EpJer 0 (heading) = KJV Bar 6:1
                    add(f"Bar.6.{vs + 1}", *w)
            elif label == "LXX1" and bn == 800 and ch == 12:          # Odes 12 = Prayer of Manasses
                for w in _parse_lxx_text(text):
                    add(f"PrMan.1.{vs}", *w)
            elif label == "LXX2" and bn == 340 and ch == 3 and 24 <= vs <= 90:   # Dan 3:24-90 Th
                for w in _parse_lxx_text(text):
                    add(f"PrAzar.1.{vs - 23}", *w)
            elif label == "LXX1" and bn == 190 and (ch, vs) in ESTHER_ADDITIONS:
                words = [w for w in _parse_lxx_text(text) if w[0]]
                targets = ESTHER_ADDITIONS[(ch, vs)]
                letters = []
                for w in words:
                    if w[0] not in letters:
                        letters.append(w[0])
                if len(letters) == len(targets):
                    for w in words:
                        kc, kv = targets[letters.index(w[0])]
                        add(f"AddEsth.{kc}.{kv}", *w, part=f"Gk {ch}:{vs}{w[0]}")
                else:
                    for kc, kv in targets:
                        for w in words:
                            add(f"AddEsth.{kc}.{kv}", *w, part=f"Gk {ch}:{vs}{w[0]} (whole addition)")
        c.close()
    con.executemany("INSERT INTO lxx VALUES (?,?,?,?,?,?,?)", rows)
    con.execute("DELETE FROM lex WHERE src='lxxlex'")
    if lexdb:
        c = sqlite3.connect(str(lexdb))
        lrows = [("lxxlex", topic, "", lex or "", tr or "", "", sd or "", "", "")
                 for topic, lex, tr, sd in c.execute(
                     "SELECT topic, lexeme, transliteration, short_definition FROM dictionary "
                     "WHERE topic LIKE 'G7_____'")]
        c.close()
        con.executemany("INSERT INTO lex VALUES (?,?,?,?,?,?,?,?,?)", lrows)


def build_geneva(con, gdir: Path | None):
    con.execute("DELETE FROM geneva")
    if not gdir:
        return
    if gdir.is_file():                       # public-domain-bibles/GENEVA.txt: "Book C:V<TAB>text"
        rows = {}
        for line in gdir.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^(.+?) (\d+):(\d+)\t(.*)$", line)
            if not m:
                continue
            try:
                osis = resolve_book(m.group(1))
            except ValueError:
                continue
            rows.setdefault(f"{osis}.{int(m.group(2))}.{int(m.group(3))}", m.group(4).strip())
        con.executemany("INSERT INTO geneva VALUES (?,?)", list(rows.items()))
        return
    name_to_osis = {b[1].lower(): b[0] for b in BOOKS}
    rows = []
    for bookdir in sorted(gdir.iterdir()):
        osis = name_to_osis.get(bookdir.name.lower())
        if not osis or not bookdir.is_dir():
            continue
        for chdir in bookdir.iterdir():
            f = chdir / "data"
            if not f.is_file():
                continue
            ch = None
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"\\c\s+(\d+)", line)
                if m:
                    ch = int(m.group(1))
                    continue
                m = re.match(r"\\v\s+(\d+)\s*(.*)", line)
                if m and ch and not re.search(r"[0-9a-f]{40,}|usfm$", m.group(2)):
                    text = re.sub(r"\\[a-z0-9]+\*?", "", m.group(2)).strip()
                    rows.append((f"{osis}.{ch}.{int(m.group(1))}", text))
    con.executemany("INSERT OR IGNORE INTO geneva VALUES (?,?)", rows)


def _strip_ns(tree_root):
    for el in tree_root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return tree_root


def clean_html(s: str) -> str:
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"<ref='[^']*'>([^<]*)</ref>", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("__", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*", "\n", s)
    return s.strip()


def build_lexicons(con, s: dict, which: set[str]):
    rows = []
    rel = set()

    # --- Strong's Greek (openscriptures/strongs) ---
    if "strongs_g" in which and s["strongs_g"]:
        con.execute("DELETE FROM lex WHERE src='strongs' AND strong LIKE 'G%'")
        root = ET.parse(s["strongs_g"]).getroot()

        def render(el) -> str:
            out = [el.text or ""]
            for ch in el:
                if ch.tag == "strongsref":
                    lang = "H" if ch.get("language", "").upper().startswith("HEB") else "G"
                    out.append(f"{lang}{int(ch.get('strongs', '0'))}")
                elif ch.tag in ("greek",):
                    out.append(ch.get("unicode", ""))
                else:
                    out.append(render(ch))
                out.append(ch.tail or "")
            return "".join(out)

        for e in root.iter("entry"):
            num = int(e.get("strongs", "0"))
            if not num:
                continue
            g = e.find("greek")
            pr = e.find("pronunciation")
            deriv = e.find("strongs_derivation")
            sdef = e.find("strongs_def")
            kjv = e.find("kjv_def")
            dtxt = re.sub(r"\s+", " ", render(deriv)).strip() if deriv is not None else ""
            body = re.sub(r"\s+", " ", render(sdef)).strip() if sdef is not None else ""
            kjvt = re.sub(r"\s+", " ", render(kjv)).strip() if kjv is not None else ""
            rows.append(("strongs", f"G{num}", "", g.get("unicode", "") if g is not None else "",
                         g.get("translit", "") if g is not None else "",
                         pr.get("strongs", "") if pr is not None else "",
                         "", body, json.dumps({"derivation": dtxt, "kjv": kjvt.lstrip(":-").strip()})))

    # --- Strong's Hebrew (HebrewLexicon/HebrewStrong.xml) + outline from strongs/hebrew ---
    if "strongs_h" in which and (s["strongs_h"] or s["strongs_h_osis"]):
        con.execute("DELETE FROM lex WHERE src IN ('strongs','outline') AND strong LIKE 'H%'")
        if s["strongs_h"]:
            root = _strip_ns(ET.parse(s["strongs_h"]).getroot())

            def render_h(el) -> str:
                out = [el.text or ""]
                for ch in el:
                    if ch.tag == "w" and ch.get("src"):
                        out.append(f"H{int(re.sub(r'[^0-9]', '', ch.get('src')) or 0)}")
                    else:
                        out.append(render_h(ch))
                    out.append(ch.tail or "")
                return "".join(out)

            for e in root.iter("entry"):
                sid = e.get("id", "")
                if not re.fullmatch(r"H\d+", sid):
                    continue
                w = e.find("w")
                parts = {t: (re.sub(r"\s+", " ", render_h(e.find(t))).strip() if e.find(t) is not None else "")
                         for t in ("source", "meaning", "usage", "note")}
                rows.append(("strongs", norm_strong(sid)[0], "", (w.text or "") if w is not None else "",
                             w.get("xlit", "") if w is not None else "", w.get("pron", "") if w is not None else "",
                             "", parts["meaning"],
                             json.dumps({"derivation": parts["source"], "kjv": parts["usage"], "note": parts["note"]})))
        if s["strongs_h_osis"]:
            root = _strip_ns(ET.parse(s["strongs_h_osis"]).getroot())
            for div in root.iter("div"):
                if div.get("type") != "entry":
                    continue
                w = div.find("w")
                if w is None or not w.get("ID"):
                    continue
                items = [re.sub(r"\s+", " ", "".join(i.itertext())).strip() for i in div.iter("item")]
                if not s["strongs_h"]:
                    notes = {n.get("type"): re.sub(r"\s+", " ", "".join(n.itertext())).strip() for n in div.findall("note")}
                    rows.append(("strongs", norm_strong(w.get("ID"))[0], "", w.get("lemma", ""), w.get("xlit", ""),
                                 w.get("POS", ""), "", notes.get("explanation", ""),
                                 json.dumps({"derivation": notes.get("exegesis", ""), "kjv": notes.get("translation", "")})))
                if items:
                    rows.append(("outline", norm_strong(w.get("ID"))[0], "", w.get("lemma", ""), w.get("xlit", ""),
                                 "", "", "\n".join(items), ""))

    # --- BDB (HebrewLexicon) via LexicalIndex ---
    if "bdb" in which and s["bdb"] and s["lexidx"]:
        con.execute("DELETE FROM lex WHERE src='bdb'")
        idx = _strip_ns(ET.parse(s["lexidx"]).getroot())
        strong_to_bdb: dict[int, list[tuple[str, str]]] = {}
        for x in idx.iter("xref"):
            st, b = x.get("strong", ""), x.get("bdb", "")
            if st.isdigit() and b:
                strong_to_bdb.setdefault(int(st), []).append((x.get("aug", ""), b))
        broot = _strip_ns(ET.parse(s["bdb"]).getroot())
        bdb_text = {}
        for e in broot.iter("entry"):
            eid = e.get("id")
            if not eid:
                continue
            parts = []

            def walk(el):
                if el.tag == "status":
                    if el.tail:
                        parts.append(el.tail)
                    return
                if el.tag == "sense" and el.get("n"):
                    parts.append(f" ({el.get('n')}) ")
                if el.text:
                    parts.append(el.text)
                for ch in el:
                    walk(ch)
                if el.tail and el is not e:
                    parts.append(el.tail)

            walk(e)
            bdb_text[eid] = re.sub(r"\s+", " ", "".join(parts)).strip()
        for num, lst in strong_to_bdb.items():
            for aug, b in sorted(set(lst)):
                if b in bdb_text:
                    rows.append(("bdb", f"H{num}", aug, "", "", "", "", bdb_text[b], b))

    # --- Unabridged BDB (eliranwong, public domain, Strong's-mapped) ---
    if "bdbfull" in which and s["bdbfull"]:
        import csv, io, zipfile
        con.execute("DELETE FROM lex WHERE src='bdbfull'")
        csv.field_size_limit(10 ** 9)
        if str(s["bdbfull"]).endswith(".zip"):
            with zipfile.ZipFile(s["bdbfull"]) as z:
                name = next(n for n in z.namelist() if n.endswith(".csv") and "MACOSX" not in n)
                text = z.read(name).decode("utf-8", errors="replace")
        else:
            text = Path(s["bdbfull"]).read_text(encoding="utf-8", errors="replace")
        for r in csv.reader(io.StringIO(text), delimiter="\t"):
            if len(r) < 3 or not r[1].startswith("H"):
                continue
            body = re.sub(r"<h1>.*?</h1>|<div class=\"navigation\">.*?</div>", "", r[2], flags=re.S)
            body = re.sub(r"(?i)<hr\s*/?>|<div class=\"(point|section|remarks)\">|</p>", "\n", body)
            body = body.replace("\\&emsp;", " ").replace("&emsp;", " ")
            body = clean_html(body)
            for num in r[1].split("_"):
                rows.append(("bdbfull", norm_strong(num)[0], "", "", "", "", "", body, r[0]))

    # --- STEPBible brief lexicons (TBESG = Abbott-Smith based, TBESH = abridged BDB) ---
    for key, src in (("tbesg", "tbesg"), ("tbesh", "tbesh")):
        if key not in which or not s[key]:
            continue
        con.execute("DELETE FROM lex WHERE src=?", (src,))
        con.execute("DELETE FROM rel WHERE why=?", (src,))
        with open(s[key], encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                if not re.match(r"^[GH]\d", line):
                    continue
                p = line.rstrip("\n").split("\t")
                if len(p) < 8:
                    continue
                base, _ = norm_strong(p[0])
                dlabel = p[1].strip()
                dnum = dlabel.split("=")[0].strip()
                _, sub = norm_strong(dnum)
                ustrong = norm_strong(p[2])[0]
                if re.search(r"(?i)= a (form|spelling) of", dlabel) and ustrong != base:
                    rel.add((base, ustrong, src)); rel.add((ustrong, base, src))
                rows.append((src, base, sub, p[3], p[4], p[5], p[6], clean_html(p[7]),
                             json.dumps({"dstrong": dlabel, "ustrong": ustrong})))

    # --- LSJ (STEPBible TFLSJ) ---
    if "lsj" in which and s["lsj"]:
        con.execute("DELETE FROM lex WHERE src='lsj'")
        for path in s["lsj"]:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    if not re.match(r"^G\d", line):
                        continue
                    p = line.rstrip("\n").split("\t")
                    if len(p) < 8:
                        continue
                    base, _ = norm_strong(p[0])
                    rows.append(("lsj", base, norm_strong(p[1].split("=")[0].strip())[1], p[3], p[4], p[5], p[6],
                                 clean_html(p[7]), ""))

    # --- Thayer (Every-Promise-Thayers markdown) ---
    if "thayer" in which and s["thayer"]:
        con.execute("DELETE FROM lex WHERE src='thayer'")
        ent_re = re.compile(r"^### (?P<head>.*?)\n`Strong's (?P<num>G\d+)`\n(?P<body>.*?)(?=^---\s*$|\Z)", re.S | re.M)
        for path in s["thayer"]:
            txt = path.read_text(encoding="utf-8")
            for m in ent_re.finditer(txt):
                head = m.group("head")
                lemma, _, translit = head.partition(" â€” ")
                body = m.group("body").strip()
                body = re.sub(r"\n{3,}", "\n\n", body)
                rows.append(("thayer", norm_strong(m.group("num"))[0], "", lemma.strip(" -"), translit.strip(),
                             "", "", body, ""))

    con.executemany("INSERT INTO lex VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO rel VALUES (?,?,?)", sorted(rel))


def ensure_index(db_path: Path, s: dict, rebuild: bool, quiet: bool) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA)
    meta = dict(con.execute("SELECT k, v FROM meta").fetchall())

    def stale(name, paths):
        fp = fingerprint(paths)
        return rebuild or meta.get(name) != fp, fp

    jobs = []
    for name, paths, fn in [
        ("kjv", s["kjv"], lambda: build_kjv(con, "kjv", s["kjv"]) if s["kjv"] else con.execute("DELETE FROM kjv WHERE src='kjv'")),
        ("kjv2006", s["kjv2006"], lambda: build_kjv(con, "kjv2006", s["kjv2006"]) if s["kjv2006"] else con.execute("DELETE FROM kjv WHERE src='kjv2006'")),
        ("kjv_apoc", [s["kjv"], *s["kjv_apoc"]], lambda: build_kjv_apocrypha(con, s["kjv_apoc"])),
        ("lxx", [s["lxx1"], s["lxx2"], s["lxxlex"]], lambda: build_lxx(con, s["lxx1"], s["lxx2"], s["lxxlex"])),
        ("geneva", s["geneva"], lambda: build_geneva(con, s["geneva"])),
        ("ttesv", s["ttesv"], lambda: build_ttesv(con, s["ttesv"]) if s["ttesv"] else con.execute("DELETE FROM esv")),
        ("step", [*s["tagnt"], *s["tahot"]], lambda: build_step_texts(con, s["tagnt"], s["tahot"])),
        ("bibledb", [s["byz"], s["wlc"], s["vmap"]], lambda: build_bibledb(con, s["byz"], s["wlc"], s["vmap"])),
        ("lex_strongs_g", s["strongs_g"], lambda: build_lexicons(con, s, {"strongs_g"})),
        ("lex_strongs_h", [s["strongs_h"], s["strongs_h_osis"]], lambda: build_lexicons(con, s, {"strongs_h"})),
        ("lex_bdb", [s["bdb"], s["lexidx"]], lambda: build_lexicons(con, s, {"bdb"})),
        ("lex_bdbfull", s["bdbfull"], lambda: build_lexicons(con, s, {"bdbfull"})),
        ("lex_tbesg", s["tbesg"], lambda: build_lexicons(con, s, {"tbesg"})),
        ("lex_tbesh", s["tbesh"], lambda: build_lexicons(con, s, {"tbesh"})),
        ("lex_lsj", s["lsj"], lambda: build_lexicons(con, s, {"lsj"})),
        ("lex_thayer", s["thayer"], lambda: build_lexicons(con, s, {"thayer"})),
    ]:
        is_stale, fp = stale(name, paths)
        if is_stale:
            jobs.append((name, fp, fn))
    if jobs and not quiet:
        print(f"Building local index ({', '.join(j[0] for j in jobs)}) -> {db_path}\n"
              "This happens once (or when a data file changes)...", file=sys.stderr)
    if any(j[0] == "kjv" for j in jobs) and not any(j[0] == "kjv_apoc" for j in jobs):
        jobs.insert(1, ("kjv_apoc", fingerprint([s["kjv"], *s["kjv_apoc"]]),
                        lambda: build_kjv_apocrypha(con, s["kjv_apoc"])))
    for name, fp, fn in jobs:
        if not quiet:
            print(f"  indexing {name} ...", file=sys.stderr, flush=True)
        fn()
        con.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (name, fp))
        con.commit()
    return con


# --------------------------------------------------------------------------------------
# Lookup and comparison
# --------------------------------------------------------------------------------------
class Lookup:
    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self._rel_cache: dict[str, set[str]] = {}

    def related(self, s: str) -> set[str]:
        if s not in self._rel_cache:
            self._rel_cache[s] = {r[0] for r in self.con.execute("SELECT b FROM rel WHERE a=?", (s,))}
        return self._rel_cache[s]

    def kjv(self, src, key):
        return self.con.execute("SELECT idx, kind, text, strongs, morph, srcpos, added FROM kjv "
                                "WHERE src=? AND verse=? ORDER BY idx", (src, key)).fetchall()

    def step(self, key):
        return self.con.execute("SELECT idx, wtype, word, translit, english, core, dstrong, grammar, gloss, "
                                "editions, alt FROM step WHERE verse=? ORDER BY idx", (key,)).fetchall()

    def esv(self, key):
        return self.con.execute("SELECT pos, strongs FROM esv WHERE verse=? ORDER BY idx", (key,)).fetchall()

    def orig(self, src, key):
        return self.con.execute("SELECT surface, strongs FROM orig WHERE src=? AND verse=? ORDER BY idx",
                                (src, key)).fetchall()

    def lxx(self, key):
        return self.con.execute("SELECT idx, word, lexid, morph, strong, part FROM lxx WHERE verse=? ORDER BY idx",
                                (key,)).fetchall()

    def geneva(self, key):
        r = self.con.execute("SELECT text FROM geneva WHERE verse=?", (key,)).fetchone()
        return r[0] if r else None

    def lex(self, src, strong):
        return self.con.execute("SELECT sub, lemma, translit, pron, gloss, body, extra FROM lex "
                                "WHERE src=? AND strong=? ORDER BY sub", (src, strong)).fetchall()

    def has(self, table, where="1=1", params=()):
        return self.con.execute(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1", params).fetchone() is not None

    def verses_in_chapter(self, book, ch):
        if book == "EpJer":
            book, ch = "Bar", 6
        rows = self.con.execute("SELECT DISTINCT verse FROM kjv WHERE src='kjv' AND verse LIKE ? "
                                "UNION SELECT DISTINCT verse FROM lxx WHERE verse LIKE ?",
                                (f"{book}.{ch}.%", f"{book}.{ch}.%")).fetchall()
        return sorted({int(r[0].rsplit(".", 1)[1]) for r in rows})

    def short_gloss(self, strong):
        for src in ("tbesg", "tbesh"):
            rs = self.con.execute("SELECT gloss, extra FROM lex WHERE src=? AND strong=? AND gloss<>'' ORDER BY sub",
                                  (src, strong)).fetchall()
            if rs:
                plain = [g for g, e in rs if json.loads(e or "{}").get("dstrong", "").rstrip().endswith("=")]
                return (plain or [rs[0][0]])[0]
        r = self.con.execute("SELECT body FROM lex WHERE src='strongs' AND strong=?", (strong,)).fetchone()
        if r and r[0]:
            return textwrap.shorten(r[0], 40, placeholder="â€¦")
        return ""

    def lemma_translit(self, strong):
        r = self.con.execute("SELECT lemma, translit FROM lex WHERE src='strongs' AND strong=?", (strong,)).fetchone()
        if r:
            return r
        r = self.con.execute("SELECT lemma, translit FROM lex WHERE src IN ('tbesg','tbesh') AND strong=? LIMIT 1",
                             (strong,)).fetchone()
        return r or ("", "")


NO_SCRIPT = False          # set by --no-script

_GREEK = {"Î±": "a", "Î²": "b", "Î³": "g", "Î´": "d", "Îµ": "e", "Î¶": "z", "Î·": "Ä“", "Î¸": "th", "Î¹": "i", "Îº": "k",
          "Î»": "l", "Î¼": "m", "Î½": "n", "Î¾": "x", "Î¿": "o", "Ï€": "p", "Ï": "r", "Ïƒ": "s", "Ï‚": "s", "Ï„": "t",
          "Ï…": "y", "Ï†": "ph", "Ï‡": "ch", "Ïˆ": "ps", "Ï‰": "Å", "Ï": "w", "Ï²": "s"}
_HEBREW = {"×": "'", "×‘": "b", "×’": "g", "×“": "d", "×”": "h", "×•": "w", "×–": "z", "×—": "á¸¥", "×˜": "á¹­", "×™": "y",
           "×›": "k", "×š": "k", "×œ": "l", "×ž": "m", "×": "m", "× ": "n", "×Ÿ": "n", "×¡": "s", "×¢": "`", "×¤": "p",
           "×£": "p", "×¦": "ts", "×¥": "ts", "×§": "q", "×¨": "r", "×©": "sh", "×ª": "t", "Ö¾": "-", "×ƒ": ".", "×€": "|"}
_SYMBOLS = {"âœ“": "ok", "â””": "-", "â€¦": "...", "Â»": ">>", "Â«": "<<", "Â·": ";", "á¾½": "'", "á¾¿": "'", "â€™": "'",
            "â€˜": "'", "â€œ": '"', "â€": '"', "\u200e": "", "\u200f": ""}
_GREEK_WORD = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff][\u0370-\u03ff\u1f00-\u1fff\u0300-\u036f]*")
_HEBREW_WORD = re.compile(r"[\u0590-\u05ff\ufb1d-\ufb4f]+")


def _translit_greek(m) -> str:
    word = unicodedata.normalize("NFD", m.group(0))
    out, rough = [], False
    for ch in word:
        if ch == "\u0314":            # rough breathing
            rough = True
            continue
        if unicodedata.combining(ch):
            continue
        low = ch.lower()
        t = _GREEK.get(low, "")
        if low == "Ï…" and out and out[-1].lower() in ("a", "e", "o", "Ä“"):   # diphthongs au, eu, ou, Ä“u
            t = "u"
        if ch != low and t:
            t = t[0].upper() + t[1:]
        out.append(t)
    res = "".join(out)
    if rough and res:
        res = ("H" + res[0].lower() + res[1:]) if res[0].isupper() else "h" + res
    return res.replace("rh", "rh")


def _translit_hebrew(m) -> str:
    return "".join(_HEBREW.get(ch, "") for ch in m.group(0) if not unicodedata.combining(ch)
                   and unicodedata.category(ch) != "Mn")


def plain(text: str) -> str:
    """--no-script: Greek/Hebrew letters -> Latin transliteration, symbols -> ASCII."""
    if not NO_SCRIPT or not isinstance(text, str):
        return text
    text = _GREEK_WORD.sub(_translit_greek, text)
    text = _HEBREW_WORD.sub(_translit_hebrew, text)
    for a, b in _SYMBOLS.items():
        text = text.replace(a, b)
    return text


def disp_width(s: str) -> int:
    w = 0
    for ch in s:
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def pad(s: str, width: int) -> str:
    return s + " " * max(0, width - disp_width(s))


def print_table(headers, rows, fmt, out):
    if NO_SCRIPT:
        rows = [[plain(str(c)) for c in r] for r in rows]
    if fmt == "tsv":
        out.append("\t".join(headers))
        out.extend("\t".join(str(c).replace("\t", " ") for c in r) for r in rows)
        return
    if fmt == "csv":
        import csv, io
        buf = io.StringIO()
        wr = csv.writer(buf)
        wr.writerow(headers)
        wr.writerows(rows)
        out.extend(buf.getvalue().rstrip("\n").split("\n"))
        return
    widths = [disp_width(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r[:-1]):
            widths[i] = min(max(widths[i], disp_width(str(c))), 40)
    widths[-1] = 0
    out.append(" | ".join(pad(h, widths[i]) for i, h in enumerate(headers)).rstrip())
    out.append("-+-".join("-" * (widths[i] or 30) for i in range(len(headers))))
    for r in rows:
        out.append(" | ".join(pad(str(c), widths[i]) for i, c in enumerate(r)).rstrip())


def match_step(kjv_units, step_rows, is_nt, lk=None):
    """Assign STEP words to KJV units by Strong's number (and morphology in the NT)."""
    used = set()
    result = {}
    for u_i, (_, kind, _, strongs, morph, _, _) in enumerate(kjv_units):
        if kind != "w":
            continue
        morphs = [m.split(":", 1)[-1] for m in morph.split()] if morph else []
        for k, sid in enumerate(strongs.split()):
            want_morph = morphs[k] if k < len(morphs) else (morphs[0] if len(morphs) == 1 else "")
            best = None
            for j, r in enumerate(step_rows):
                if j in used:
                    continue
                core, alt = r[5].split(), r[10].split()
                how = "core" if sid in core else ("alt" if sid in alt else None)
                if not how and lk is not None and lk.related(sid) & set(core):
                    how = "rel"
                if not how:
                    continue
                score = {"core": 3, "alt": 2, "rel": 1}[how] + (2 if is_nt and want_morph and r[7].startswith(want_morph) else 0)
                if is_nt and "K" not in r[1] and "k" not in r[1]:
                    score -= 3          # word not in the KJV's Greek text (TR)
                if best is None or score > best[0]:
                    best = (score, j, how)
            if best:
                used.add(best[1])
                result[(u_i, sid)] = (best[1], best[2])
    return result, used


def related_in(lk: Lookup, sid: str, pool: set[str]) -> list[str]:
    return sorted((lk.related(sid) & pool) - {sid}, key=strong_sort_key)


def show_verse(lk: Lookup, book: str, ch: int, vs: int, opts, out: list[str], defs_wanted: list[str]):
    if book == "EpJer":                     # KJV prints the Epistle of Jeremy as Baruch 6
        book, ch = "Bar", 6
    key = f"{book}.{ch}.{vs}"
    ref = f"{OSIS_NAME[book]} {ch}:{vs}" if vs else f"{OSIS_NAME[book]} {ch} (title)"
    nt = not is_ot(book)
    apoc = is_apoc(book)
    units = lk.kjv("kjv", key)
    lxx_rows = lk.lxx(key) if apoc else []
    gen_text = lk.geneva(key) if opts.geneva else None
    if not units and not lxx_rows:
        out.append(f"{ref}: not found in the KJV index" +
                   (" (no KJV Apocrypha file indexed: kjv-strongs/kjvdc.xml or kjva.osis.xml)." if apoc else "."))
        return
    if apoc:
        show_apocrypha(lk, ref, key, units, lxx_rows, opts, out, defs_wanted)
        return
    step_rows = lk.step(key)
    k06 = lk.kjv("kjv2006", key)
    orig_src = "byz" if nt else "wlc"
    orig_rows = lk.orig(orig_src, key)
    esv_rows = lk.esv(key)

    k06_set = {x for r in k06 if r[1] == "w" for x in r[3].split()}
    orig_set = {x for r in orig_rows for x in r[1].split()}
    step_core = {x for r in step_rows for x in r[5].split()}
    step_any = step_core | {x for r in step_rows for x in r[10].split()}
    have_k06, have_orig, have_step = bool(k06), bool(orig_rows), bool(step_rows)
    orig_label = "Byzantine RP" if nt else "WLC (OSHB)"

    verse_text = " ".join(u[2] for u in units)
    verse_text = re.sub(r"\s+([,.;:!?)])", r"\1", verse_text)
    out.append("=" * 78)
    out.append(f"{ref}  (KJV)")
    out.append(textwrap.fill(verse_text, 78))
    out.append("")
    out.append("KJV word-by-word  [source: CrossWire KJV OSIS; KJV takes precedence]")

    rp: list[str] = []
    opts.reprint.append((ref, rp))
    matches, used = match_step(units, step_rows, nt, lk) if have_step else ({}, set())
    headers = ["#", "KJV text", "Strong's", "In text", "Lemma", "Translit", "Gloss", "Other sources (only differences)"]
    rows = []
    n = 0
    all_kjv_ids = []
    for u_i, (_, kind, text, strongs, morph, srcpos, added) in enumerate(units):
        if kind != "w":
            if not re.search(r"\w", text):
                continue
            n += 1
            rows.append([n, f"[{text}]" if added else text, "-", "", "", "", "(added in KJV, italics)" if added else "(untagged)", ""])
            rp.append((f"[{text}]" if added else text,
                       [("none", "KJV", "KJV italics, no Hebrew/Greek behind it" if added else "untagged in KJV")]))
            continue
        ids = strongs.split()
        all_kjv_ids += ids
        unit_alts: dict[str, list[str]] = {}

        def _alt(nums, src):
            for x in nums:
                if x not in ids and x not in SET_NOISE:
                    unit_alts.setdefault(x, [])
                    if src not in unit_alts[x]:
                        unit_alts[x].append(src)
        for k, sid in enumerate(ids):
            n += 1
            lemma, translit = lk.lemma_translit(sid)
            gloss = lk.short_gloss(sid)
            in_text = ""
            notes = []
            m = matches.get((u_i, sid))
            if m:
                srow = step_rows[m[0]]
                in_text = re.sub(r"[/\\×ƒ×€]", "", srow[2]).strip(",.;:Â·;!?Â¶Ö¾ ")
                ctx = srow[8].partition("=")[2].split("Â»")[0].split("@")[0].strip(" :").replace("_", " ")
                if ctx and not ctx.startswith("["):
                    gloss = ctx
                step_alts = [a for a in srow[10].split() if a != sid]
                step_name = "STEPBible TAGNT" if nt else "STEPBible TAHOT"
                if m[1] in ("alt", "rel"):
                    alt_txt = f" (alt {'/'.join(step_alts)})" if step_alts else ""
                    notes.append(f"STEP: {'/'.join(srow[5].split()) or '?'}{alt_txt}")
                    _alt(srow[5].split(), step_name)
                elif step_alts:
                    notes.append(f"STEP alt: {'/'.join(step_alts)}")
                _alt(step_alts, step_name + " alternate")
            elif have_step:
                rel = related_in(lk, sid, step_any)
                notes.append(f"STEP: {'/'.join(rel)}" if rel else "STEP: not found in verse")
                _alt(rel, "STEPBible TAGNT" if nt else "STEPBible TAHOT")
            if have_k06 and sid not in k06_set and sid not in SET_NOISE:
                rel = related_in(lk, sid, k06_set)
                notes.append(f"KJV2006: {'/'.join(rel)}" if rel else "KJV2006: untagged")
                _alt(rel, "eBible KJV2006")
            if have_orig and sid not in orig_set and not (sid in SET_NOISE and not nt):
                rel = related_in(lk, sid, orig_set)
                notes.append(f"{orig_label}: {'/'.join(rel)}" if rel else f"{orig_label}: not in verse")
                _alt(rel, f"bible-db {orig_label}")
            for r in re.findall(r"[GH]\d+", " ".join(notes)):
                if r != sid and r not in defs_wanted:
                    defs_wanted.append(r)
            label = text if k == 0 else f"  â”” (same phrase)"
            if added:
                label = f"[{label}]"
            if sid == "H853" and len(ids) > 1:
                gloss = gloss or "[object marker]"
            rows.append([n, label, sid, in_text, lemma, translit, gloss, "; ".join(notes) if notes else "âœ“"])
            if sid not in defs_wanted:
                defs_wanted.append(sid)
        answers = [(" + ".join(ids), "KJV", "CrossWire KJV")]
        for num, srcs in unit_alts.items():
            kjv_srcs = [x for x in srcs if "KJV2006" in x]
            orig_srcs = [x for x in srcs if "KJV2006" not in x]
            if kjv_srcs:
                answers.append((num, "KJV", ", ".join(kjv_srcs)))
            if orig_srcs:
                answers.append((num, "Greek" if nt else "Hebrew", ", ".join(orig_srcs)))
        rp.append((f"[{text}]" if added else text, answers))
    print_table(headers, rows, opts.format, out)

    srcs = ["STEPBible TAGNT" if nt else "STEPBible TAHOT"] if have_step else []
    if have_k06:
        srcs.append("eBible KJV2006")
    if have_orig:
        srcs.append(f"bible-db {orig_label}")
    out.append(f"âœ“ = agrees with: {', '.join(srcs) if srcs else '(no cross-check sources installed)'}")

    # Original-language words with no KJV tag
    if have_step:
        kjv_set = set(all_kjv_ids)
        extra = []
        for j, r in enumerate(step_rows):
            if j in used:
                continue
            if nt and "K" not in r[1] and "k" not in r[1]:
                continue
            core = r[5].split()
            if not core or any(c in kjv_set or (lk.related(c) & kjv_set) for c in core):
                continue
            extra.append(f"{r[2]} ({'/'.join(core)}, \"{r[4]}\")")
        if extra:
            out.append("Original-language words in this verse with no KJV tag: " + "; ".join(extra))

    # ESV
    if esv_rows:
        esv_ids = [x for r in esv_rows for x in r[1].split()]
        a = set(all_kjv_ids) - SET_NOISE
        b = set(esv_ids) - SET_NOISE
        out.append("")
        if a == b and not opts.esv:
            rp.append(("ESV (whole verse)", [("same as KJV", "ESV", "STEPBible TTESV")]))
            out.append("ESV (STEPBible TTESV): same Strong's numbers as the KJV â€” KJV result above stands "
                       "(H853/G3588 ignored; ESV tagging omits them by design).")
        else:
            out.append("ESV  [source: STEPBible TTESV; ESV text itself is not included in that file, so words "
                       "are given by position in the ESV verse]")
            erows = []
            for pos, ids in esv_rows:
                for sid in ids.split():
                    lemma, translit = lk.lemma_translit(sid)
                    if sid in a or sid in SET_NOISE:
                        cmp = "âœ“ in KJV"
                    else:
                        rel = related_in(lk, sid, set(all_kjv_ids))
                        cmp = f"KJV uses {'/'.join(rel)}" if rel else "NOT in KJV verse"
                        if sid not in defs_wanted:
                            defs_wanted.append(sid)
                    erows.append([f"word {pos}", sid, lemma, translit, lk.short_gloss(sid), cmp])
                    rp.append((f"ESV word {pos}", [(sid, "ESV", "STEPBible TTESV" +
                                                       ("" if cmp == "âœ“ in KJV" else f"  ({cmp})"))]))
            print_table(["ESV pos", "Strong's", "Lemma", "Translit", "Gloss", "vs KJV"], erows, opts.format, out)
            missing = sorted(a - b - {x for e in b for x in lk.related(e)}, key=strong_sort_key)
            if missing:
                out.append("In KJV but not tagged in ESV: " + ", ".join(missing))
    if opts.geneva:
        show_geneva(lk, units, gen_text, opts, out, rp)
    out.append("")


def render_reprint(blocks) -> list[str]:
    """Aligned, ASCII-framed summary: one entry per word, alternates on their own rows, blank line between."""
    lines = ["", "=" * 78, "STRONGS REPRINT FOR EASY READING", "=" * 78]
    for ref, entries in blocks:
        if not entries:
            continue
        ww = min(max([4] + [disp_width(plain(w)) for w, _ in entries]), 34)
        nw = max([8] + [disp_width(a[0]) for _, ans in entries for a in ans])
        vw = max([7] + [len(a[1]) for _, ans in entries for a in ans])
        lines.append("")
        lines.append(ref)
        hdr = f"  {'#':>3}  {pad('WORD', ww)}  {pad('STRONGS', nw)}  {pad('VERSION', vw)}  SOURCE"
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2 + 12))
        n = 0
        for word, answers in entries:
            n += 1
            for i, (num, ver, src) in enumerate(answers):
                num_col = f"{n:>3}" if i == 0 else "   "
                word_col = plain(word) if i == 0 else "  or"
                lines.append(f"  {num_col}  {pad(word_col, ww)}  {pad(num, nw)}  {pad(ver, vw)}  {src}".rstrip())
            lines.append("")
    lines.append("=" * 78)
    return lines


def show_apocrypha(lk, ref, key, units, lxx_rows, opts, out, defs_wanted):
    rp: list[str] = []
    opts.reprint.append((ref, rp))
    out.append("=" * 78)
    out.append(f"{ref}  (KJV Apocrypha)")
    if units:
        vt = re.sub(r"\s+([,.;:!?)])", r"\1", " ".join(u[2] for u in units))
        out.append(textwrap.fill(vt, 78))
    else:
        out.append("(KJV text for this verse not found in the indexed KJV Apocrypha file)")
    out.append("")
    tagged = [u for u in units if u[1] == "w"]
    lxx_set = {r[4] for r in lxx_rows if r[4]}
    if tagged:
        out.append("KJV word-by-word  [source: CrossWire KJV Apocrypha]")
        rows, n = [], 0
        for _, kind, text, strongs, morph, srcpos, added in units:
            if kind != "w":
                if re.search(r"\w", text):
                    n += 1
                    rows.append([n, f"[{text}]" if added else text, "-", "", "", "", ""])
                continue
            for k, sid in enumerate(strongs.split()):
                n += 1
                lemma, translit = lk.lemma_translit(sid)
                note = "âœ“" if (not lxx_set or sid in lxx_set) else (
                    "LXX: " + "/".join(related_in(lk, sid, lxx_set)) if related_in(lk, sid, lxx_set) else "LXX: not in verse")
                rows.append([n, text if k == 0 else "  â”” (same phrase)", sid, lemma, translit, lk.short_gloss(sid), note])
                rp.append((text if k == 0 else "", [(sid, "KJV", "CrossWire KJV Apocrypha")]))
                if sid not in defs_wanted:
                    defs_wanted.append(sid)
        print_table(["#", "KJV text", "Strong's", "Lemma", "Translit", "Gloss", "LXX check"], rows, opts.format, out)
        out.append("")
    elif units:
        out.append("The KJV Apocrypha file carries no Strong's tags for this verse, so the numbers below come from")
        out.append("the Greek text the KJV translators worked from (Septuagint), word by word.")
        out.append("")
    if not lxx_rows:
        why = "2 Esdras survives in Latin, not Greek, so no Strong's numbers exist for it." if key.startswith("2Esd.") \
            else "LXX data not installed (LXX-Rahlfs-1935) or no Greek verse maps to this KJV verse."
        out.append(why)
        rp.append(("(whole verse)", [("none", "-", why)]))
        return
    parts = sorted({r[5] for r in lxx_rows if r[5]})
    label = f"  [Greek {', '.join(parts[:1])}{' ...' if len(parts) > 1 else ''}]" if parts else ""
    out.append(f"Greek (Septuagint, Rahlfs 1935) word-by-word  [source: LXX-Rahlfs-1935 / Open Scriptures Strong's]{label}")
    if any("whole addition" in p for p in parts):
        out.append("Note: Rahlfs divides this Addition to Esther differently from the KJV, so the whole Greek "
                   "addition is shown.")
    rows = []
    n = 0
    for (_, word, lexid, morph, strong, part) in lxx_rows:
        n += 1
        if strong:
            lemma, translit = lk.lemma_translit(strong)
            gloss = lk.short_gloss(strong)
            if strong not in defs_wanted:
                defs_wanted.append(strong)
        else:
            e = lk.lex("lxxlex", f"G{lexid}") if lexid else []
            lemma, translit, gloss = (e[0][1], e[0][2], e[0][4]) if e else ("", "", "")
        rows.append([n, word.strip(",.;:Â·"), strong or "none", lemma, translit, gloss, morph])
        rp.append((f"{word.strip(',.;:Â·')} ({translit})" if translit else word.strip(",.;:Â·"),
                   [(strong or "none", "LXX", "LXX-Rahlfs-1935" + ("" if strong else " (word not in Strong's)"))]))
    print_table(["#", "Greek", "Strong's", "Lemma", "Translit", "Gloss", "Morph"], rows, opts.format, out)
    if any(r[2] == "none" for r in rows):
        out.append("none = no Strong's number exists (Strong's covers only words used in the Hebrew OT and Greek NT;")
        out.append("       many Apocrypha words and names fall outside it). Gloss is from the LXX-Rahlfs lexicon.")


def _gnorm(w: str) -> str:
    w = re.sub(r"[^a-z]", "", w.lower()).replace("j", "i").replace("v", "u").replace("y", "i")
    w = re.sub(r"(.)\1+", r"\1", w)
    if len(w) > 2 and w.endswith("e"):
        w = w[:-1]
    return w


def show_geneva(lk, units, gen_text, opts, out, rp=None):
    import difflib
    out.append("")
    if not gen_text:
        out.append("Geneva Bible: verse not found (install enggnv; the 1599 Geneva text there has no Apocrypha).")
        return
    out.append("Geneva Bible (1599)")
    out.append(textwrap.fill(gen_text, 78))
    out.append("No Strong's-tagged Geneva Bible exists in any free database. The numbers below are carried over")
    out.append("from the KJV tagging wherever the Geneva wording lines up with the KJV:  = same words,  ~ probable")
    out.append("(different word in the same place),  - no KJV counterpart (check manually).")
    ktoks = []          # (norm, unit index)
    for i, u in enumerate(units):
        for w in re.findall(r"[A-Za-z']+", u[2]):
            ktoks.append((_gnorm(w), i))
    gwords = re.findall(r"[A-Za-z']+|[^A-Za-z'\s]+", gen_text)
    gtoks = [(w, _gnorm(w)) for w in gwords if re.search(r"[A-Za-z]", w)]
    sm = difflib.SequenceMatcher(None, [k[0] for k in ktoks], [g[1] for g in gtoks], autojunk=False)
    assign = [(None, "-")] * len(gtoks)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                assign[j1 + d] = (ktoks[i1 + d][1], "=")
        elif tag == "replace" and (i2 - i1) == (j2 - j1) and (i2 - i1) <= 3:
            for d in range(i2 - i1):
                assign[j1 + d] = (ktoks[i1 + d][1], "~")
        elif tag == "replace":
            # unequal-length rewording: pair words that are spelled alike (handes~hands, ours~our)
            for j in range(j1, j2):
                best = max(range(i1, i2), key=lambda i: difflib.SequenceMatcher(
                    None, ktoks[i][0], gtoks[j][1]).ratio())
                if difflib.SequenceMatcher(None, ktoks[best][0], gtoks[j][1]).ratio() >= 0.75:
                    assign[j] = (ktoks[best][1], "~")
    rows, n, j = [], 0, 0
    while j < len(gtoks):
        unit, how = assign[j]
        k = j
        while k + 1 < len(gtoks) and assign[k + 1] == (unit, how):
            k += 1
        words = " ".join(g[0] for g in gtoks[j:k + 1])
        n += 1
        if unit is None:
            rows.append([n, words, "-", "-", "", ""])
        else:
            u = units[unit]
            ids = u[3].split() if u[1] == "w" else []
            rows.append([n, words, " + ".join(ids) or "-", how, u[2],
                         lk.short_gloss(ids[-1]) if ids else ("(KJV italics)" if u[6] else "")])
        j = k + 1
    print_table(["#", "Geneva text", "Strong's (via KJV)", "Match", "KJV words", "Gloss"], rows, opts.format, out)
    if rp is not None:
        for r in rows:
            how = {"=": "same wording as KJV", "~": "probable", "-": "no KJV counterpart"}.get(r[3], r[3])
            rp.append((f"Geneva: {r[1]}", [(r[2] if r[2] != "-" else "none", "Geneva", f"via KJV tagging, {how}")]))


LEX_LABELS = {
    "strongs": "Strong's",
    "outline": "Outline (BDB-based, as BLB 'Outline of Biblical Usage')",
    "thayer": "Thayer's (1889)",
    "bdb": "Brown-Driver-Briggs (Open Scriptures outline edition)",
    "bdbfull": "Brown-Driver-Briggs (unabridged)",
    "tbesg": "Abbott-Smith via STEPBible TBESG",
    "tbesh": "Abridged BDB via STEPBible TBESH",
    "lsj": "Liddell-Scott-Jones via STEPBible TFLSJ",
}


def clip(text: str, limit: int) -> str:
    text = text.strip()
    if limit <= 0 or len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + " â€¦ [--full for the rest]"


def indent_block(text: str, prefix="    ", width=100) -> list[str]:
    lines = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        lines.extend(textwrap.wrap(para, width=width, initial_indent=prefix, subsequent_indent=prefix) or [prefix])
    return lines


def show_definitions(lk: Lookup, ids: list[str], opts, out: list[str]):
    if opts.defs == "none" or not ids:
        return
    limit = 0 if opts.defs == "full" else opts.chars
    lexset = [x.strip() for x in opts.lex.split(",") if x.strip()]
    out.append("=" * 78)
    out.append("DEFINITIONS" + ("" if limit == 0 else f"  (brief; use --full for complete entries)"))
    for sid in ids:
        heb = sid.startswith("H")
        lemma, translit = lk.lemma_translit(sid)
        out.append("")
        out.append(f"{sid}  {lemma}  {translit}".rstrip())
        printed = False
        has_full = bool(lk.lex("bdbfull", sid)) if heb else False
        order = (["strongs", "outline", "bdbfull" if has_full else "bdb", "tbesh"] if heb
                 else ["strongs", "thayer", "tbesg", "lsj"])
        for src in order:
            if src not in lexset and not (src == "outline" and "strongs" in lexset) \
                    and not (src == "bdbfull" and "bdb" in lexset):
                continue
            entries = lk.lex(src, sid)
            for sub, lem, tr, pron, gloss, body, extra in entries:
                if src == "strongs":
                    ex = json.loads(extra or "{}")
                    out.append(f"  {LEX_LABELS[src]}: {lem} ({tr}{', ' + pron if pron else ''})")
                    if ex.get("derivation"):
                        out.extend(indent_block("Derivation: " + ex["derivation"]))
                    if body:
                        out.extend(indent_block("Definition: " + body))
                    if ex.get("kjv"):
                        out.extend(indent_block("KJV usage: " + ex["kjv"]))
                elif src in ("tbesg", "tbesh"):
                    ex = json.loads(extra or "{}")
                    label = ex.get("dstrong", "").rstrip(" =")
                    out.append(f"  {LEX_LABELS[src]}: {label} {lem} ({tr}) â€” {gloss}")
                    out.extend(indent_block(clip(body, limit)))
                elif src in ("bdb", "bdbfull"):
                    out.append(f"  {LEX_LABELS[src]}" + (f" [{sid}{sub}]" if sub else "") +
                               (f" [{extra}]" if src == "bdbfull" and len(entries) > 1 else "") + ":")
                    out.extend(indent_block(clip(body, limit)))
                else:
                    out.append(f"  {LEX_LABELS[src]}:")
                    out.extend(indent_block(clip(body, limit)))
                printed = True
        if not printed:
            out.append("  (no entry in the installed lexicons)")
    out.append("")


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
HELP = """\
Look up the Strong's number of every word in a Bible verse, KJV first, using only
local data files. Other tagged sources are cross-checked and any disagreement is
shown on the same line. Definitions follow (Strong's, Thayer, BDB, Abbott-Smith, LSJ).

USAGE
  interlinear.py BOOK CHAPTER:VERSE[-VERSE]   e.g.  interlinear.py 1 john 1:1
  interlinear.py BOOK CHAPTER                 whole chapter
  interlinear.py G3056 [H7225 ...]            lexicon lookup by Strong's number

EXAMPLES
  interlinear.py john 1:1
  interlinear.py 1 john 1:1-3
  interlinear.py "song of solomon" 2:1
  interlinear.py gen 1:1 --full            complete lexicon entries
  interlinear.py rom 3:23 --defs none      Strong's table only
  interlinear.py ps 3:0                    Psalm superscription (title)
  interlinear.py sirach 1:1                Apocrypha (Greek Septuagint word-by-word)
  interlinear.py 1 john 1:1 --geneva       add the Geneva Bible (1599) with KJV-derived numbers
  interlinear.py john 3:16 --format tsv    tab-separated (paste into a spreadsheet)
  interlinear.py john 1:1 --no-script      Greek/Hebrew shown as Latin letters (font shows boxes)
  interlinear.py --sources                 show which data files were found

OUTPUT
  1. KJV verse text and a word-by-word table (CrossWire KJV tagging = primary answer).
     [brackets] = words the KJV printed in italics (supplied, no Greek/Hebrew behind them).
     "Other sources" lists only disagreements:
       STEP ...     STEPBible TAGNT/TAHOT (word-by-word Greek/Hebrew, Tyndale House)
       KJV2006 ...  eBible KJV2006 tagging (uses Strong's original numbering, like Blue Letter Bible)
       Byzantine RP / WLC ...  bible-db original-language texts
     A check mark means every installed source agrees.
  2. ESV: printed only when its Strong's set differs from the KJV (or with --esv).
  3. Geneva (with --geneva / -V GENEVA / -V ALL): no Strong's-tagged Geneva exists, so numbers
     are carried over from the KJV where the wording lines up (= same words, ~ probable, - none).
  5. STRONGS REPRINT FOR EASY READING (last block): one line per word,
       word: NUMBER (version) : SOURCE  |  ALTERNATE (version) : SOURCE ...
     so the numbers alone can be read without scrolling (--no-reprint to omit).
  4. Definitions for every number shown (and every conflicting alternate):
     Hebrew: Strong's, BDB outline, unabridged BDB, STEPBible abridged BDB
     Greek:  Strong's, Thayer's, Abbott-Smith (STEPBible), LSJ (with --lex ...,lsj)

APOCRYPHA
  Tobit, Judith, Additions to Esther, Wisdom, Sirach/Ecclesiasticus, Baruch (6 = Epistle of
  Jeremy), Song of the Three Children, Susanna, Bel, Prayer of Manasses, 1-2 Maccabees, 1-2 Esdras.
  KJV text comes from kjv-strongs/kjvdc.xml or kjva.osis.xml. Strong's numbers come from the
  Greek Septuagint (Rahlfs), because the KJV Apocrypha is not Strong's-tagged. 2 Esdras exists
  only in Latin, so it has no Strong's numbers.

NUMBERING NOTE
  Modern tagging (CrossWire KJV v3, STEPBible) files inflected forms under the
  dictionary word (e.g. á¼¦Î½ "was" = G1510 eimi). Strong's original concordance and
  Blue Letter Bible give some forms their own numbers (á¼¦Î½ = G2258, á¼¡Î¼á¿¶Î½ = G2257).
  Both are shown when they differ; neither is "wrong".

DATA LOCATION
  Data root = --data DIR, else $INTERLINEAR_DATA, else the script's folder, the
  current folder, or ~/scripts/interlinear_tool. Expected inside it:
    kjv-strongs/kjvfull.xml           CrossWire KJV (required)
    STEPBible-Data/                   TAGNT, TAHOT, TTESV, TBESG, TBESH, TFLSJ
    strongs/                          openscriptures Strong's dictionaries
    HebrewLexicon/                    openscriptures BDB + Hebrew Strong's
    Every-Promise-Thayers/            Thayer's lexicon keyed to Strong's
    bible-db/                         Byzantine Greek + WLC Hebrew with Strong's
    unabridged-BDB-Hebrew-lexicon/    full BDB keyed to Strong's
    LXX-Rahlfs-1935/                  Septuagint with Strong's (Apocrypha)
    public-domain-bibles/GENEVA.txt   Geneva Bible 1599
    kjv2006-ebible.osis.xml           optional (see --sources)
  The index is cached at ~/.cache/interlinear_tool/index.sqlite (--rebuild to force).
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), description=HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter, add_help=True)
    ap.add_argument("reference", nargs="*", help="book chapter:verse, or Strong's numbers (G3056 H7225)")
    ap.add_argument("--version", "-V", choices=["KJV", "ESV", "BOTH", "GENEVA", "ALL"], default="KJV",
                    type=str.upper,
                    help="KJV (default; ESV shown only when it differs), ESV/BOTH (always show ESV), "
                         "GENEVA (add Geneva 1599), ALL (ESV + Geneva)")
    ap.add_argument("--geneva", "-g", action="store_true", help="also show the Geneva Bible (same as --version GENEVA)")
    ap.add_argument("--esv", action="store_true", help="always show the ESV block (same as --version BOTH)")
    ap.add_argument("--defs", choices=["none", "brief", "full"], default="brief", help="definitions (default: brief)")
    ap.add_argument("--full", action="store_true", help="complete lexicon entries (same as --defs full)")
    ap.add_argument("--chars", type=int, default=600, help="characters per lexicon entry in brief mode (default 600)")
    ap.add_argument("--lex", default="strongs,thayer,bdb,tbesg,tbesh",
                    help="lexicons to print: strongs,thayer,bdb,tbesg,tbesh,lsj (default: all but lsj)")
    ap.add_argument("--format", choices=["table", "tsv", "csv"], default="table", help="table layout (default: table)")
    ap.add_argument("--no-script", action="store_true",
                    help="show Greek/Hebrew as Latin transliteration and symbols as ASCII "
                         "(for terminals whose font shows boxes)")
    ap.add_argument("--no-reprint", action="store_true", help="omit the STRONGS REPRINT summary at the end")
    ap.add_argument("--data", help="data root folder")
    ap.add_argument("--kjv-xml", help="path to CrossWire KJV OSIS (default: kjv-strongs/kjvfull.xml)")
    ap.add_argument("--kjv2006-xml", help="path to eBible KJV2006 OSIS (optional cross-check)")
    ap.add_argument("--cache", help="index file (default: ~/.cache/interlinear_tool/index.sqlite)")
    ap.add_argument("--rebuild", action="store_true", help="rebuild the index from the data files")
    ap.add_argument("--sources", action="store_true", help="list detected data files and exit")
    ap.add_argument("--quiet", "-q", action="store_true", help="no progress messages while indexing")
    opts = ap.parse_args(argv)
    if opts.full:
        opts.defs = "full"
    global NO_SCRIPT
    NO_SCRIPT = opts.no_script
    opts.reprint = []
    if opts.version in ("ESV", "BOTH", "ALL"):
        opts.esv = True
    if opts.version in ("GENEVA", "ALL"):
        opts.geneva = True

    root = find_data_root(opts.data)
    s = discover(root, opts)
    if opts.sources:
        print(f"Data root: {root}")
        for k, v in s.items():
            if isinstance(v, list):
                print(f"  {k:15} {len(v)} file(s)" + (f"  e.g. {v[0]}" if v else "  MISSING"))
            else:
                print(f"  {k:15} {v if v else 'MISSING'}")
        if not s["kjv2006"]:
            print("\nOptional KJV2006 (Blue-Letter-Bible-style numbering) on Debian/Ubuntu:\n"
                  "  sudo apt install sword-text-kjv libsword-utils\n"
                  f"  mod2osis engKJV2006eb > {root}/kjv2006-ebible.osis.xml")
        return 0

    if not opts.reference and not opts.rebuild:
        ap.print_help()
        return 1

    if not s["kjv"]:
        print(f"Error: CrossWire KJV OSIS not found under {root}/kjv-strongs/. Use --kjv-xml PATH or --data DIR.",
              file=sys.stderr)
        return 2

    cache = Path(opts.cache).expanduser() if opts.cache else \
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "interlinear_tool" / "index.sqlite"
    try:
        con = ensure_index(cache, s, opts.rebuild, opts.quiet)
    except ET.ParseError as e:
        print(f"Error while indexing XML: {e}", file=sys.stderr)
        return 2
    lk = Lookup(con)
    if not opts.reference:
        print("Index rebuilt.")
        return 0

    out: list[str] = []
    defs: list[str] = []
    words = opts.reference
    if all(re.fullmatch(r"[GHgh]0*\d+[A-Za-z]?", w) for w in words):
        ids = [norm_strong(w)[0] for w in words]
        if opts.defs == "none":
            opts.defs = "brief"
        show_definitions(lk, ids, opts, out)
        print("\n".join(plain(l) for l in out))
        return 0

    try:
        book, ch, v1, v2 = parse_reference(words)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    verses = list(range(v1, v2 + 1)) if v1 is not None else lk.verses_in_chapter(book, ch)
    if not verses:
        print(f"Error: {OSIS_NAME[book]} {ch} not found.", file=sys.stderr)
        return 1
    for v in verses:
        show_verse(lk, book, ch, v, opts, out, defs)
    show_definitions(lk, defs, opts, out)
    if opts.reprint and not opts.no_reprint:
        out.extend(render_reprint(opts.reprint))
    if NO_SCRIPT:
        out = [plain(l) for l in out]
    try:
        print("\n".join(out))
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
