#!/usr/bin/env python3
"""
Paper Radar: trawl bioRxiv + Europe PMC (PubMed and all journals), tag papers
by topic / species / method, score their relevance and build a static site.

    python trawl.py                 # fetch, merge into archive, build site
    python trawl.py --build-only    # rebuild site from existing archive (no network)
    python trawl.py --days 7        # override the rolling window

Outputs
    data/archive.json   rolling archive of every paper seen within the window
    docs/index.html     the website (GitHub Pages serves /docs)
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.yaml"
ARCHIVE = ROOT / "data" / "archive.json"
TEMPLATE = ROOT / "template.html"
SITE = ROOT / "docs" / "index.html"

UA = {"User-Agent": "paper-radar/1.0 (academic literature digest; GitHub Actions)"}
TODAY = dt.date.today()


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get_json(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                return r.json()
            log(f"  HTTP {r.status_code} for {r.url[:160]}")
        except Exception as e:  # network hiccup
            log(f"  error {e!r}")
        time.sleep(2 * (i + 1))
    return None


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # strip JATS/HTML tags
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())[:120]


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def fetch_biorxiv(cfg, start: dt.date, end: dt.date) -> list[dict]:
    out = []
    for cat in cfg["categories"]:
        cursor, total = 0, None
        log(f"bioRxiv [{cat}] {start}..{end}")
        while total is None or cursor < total:
            url = f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/{cursor}"
            js = get_json(url, {"category": cat})
            if not js or not js.get("messages"):
                break
            msg = js["messages"][0]
            if msg.get("status") != "ok":
                break
            total = int(msg.get("total", 0))
            coll = js.get("collection", [])
            if not coll:
                break
            for p in coll:
                if cfg.get("new_only", True) and str(p.get("version")) != "1":
                    continue
                doi = p["doi"]
                pub = p.get("published") or "NA"
                out.append({
                    "id": f"doi:{doi.lower()}",
                    "doi": doi,
                    "title": clean(p.get("title")),
                    "authors": clean(p.get("authors")),
                    "abstract": clean(p.get("abstract")),
                    "date": p.get("date"),
                    "source": "bioRxiv",
                    "kind": "preprint",
                    "url": f"https://www.biorxiv.org/content/{doi}v{p.get('version', 1)}",
                    "institution": clean(p.get("author_corresponding_institution")),
                    "published_doi": None if pub == "NA" else pub,
                    "pubtype": p.get("type", ""),
                })
            cursor += len(coll)
            time.sleep(0.3)
        log(f"  -> {len(out)} bioRxiv records so far")
    return out


def fetch_europepmc(cfg, topics, start: dt.date, end: dt.date) -> list[dict]:
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    srcs = "(SRC:MED OR SRC:PPR)" if cfg.get("include_preprints", True) else "SRC:MED"
    out, seen = [], set()
    for key, t in topics.items():
        terms = " OR ".join(f'TITLE:"{q}" OR ABSTRACT:"{q}"' for q in t.get("query", []))
        if not terms:
            continue
        query = (f"({terms}) AND ({cfg['context']}) AND {srcs} "
                 f"AND FIRST_PDATE:[{start} TO {end}]")
        cursor, n = "*", 0
        log(f"Europe PMC [{key}]")
        while n < cfg.get("max_per_topic", 3000):
            js = get_json(base, {"query": query, "format": "json", "resultType": "core",
                                 "pageSize": 1000, "cursorMark": cursor})
            if not js:
                break
            res = js.get("resultList", {}).get("result", [])
            if n == 0:
                log(f"  hits: {js.get('hitCount')}")
            for r in res:
                n += 1
                rid = f"{r.get('source')}:{r.get('id')}"
                if rid in seen:
                    continue
                seen.add(rid)
                rec = epmc_record(r)
                if rec:
                    out.append(rec)
            nxt = js.get("nextCursorMark")
            if not res or not nxt or nxt == cursor:
                break
            cursor = nxt
            time.sleep(0.3)
    log(f"  -> {len(out)} Europe PMC records")
    return out


def epmc_record(r) -> dict | None:
    title = clean(r.get("title"))
    abstract = clean(r.get("abstractText"))
    if not title:
        return None
    is_pp = r.get("source") == "PPR"
    doi = r.get("doi")
    jinfo = (r.get("journalInfo") or {}).get("journal", {}) or {}
    journal = jinfo.get("title")
    journal_names = [x for x in (jinfo.get("title"), jinfo.get("isoabbreviation"),
                                 jinfo.get("medlineAbbreviation")) if x]
    if is_pp:
        journal = (r.get("bookOrReportDetails") or {}).get("publisher") or "Preprint"
    ptypes = [p.lower() for p in (r.get("pubTypeList") or {}).get("pubType", [])]
    if any(x in ptypes for x in ("erratum", "published erratum", "retraction of publication", "comment", "editorial")):
        return None
    if doi:
        url = f"https://doi.org/{doi}"
    elif r.get("pmid"):
        url = f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/"
    else:
        url = f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
    return {
        "id": f"doi:{doi.lower()}" if doi else f"epmc:{r.get('source')}:{r.get('id')}",
        "doi": doi,
        "pmid": r.get("pmid"),
        "title": title,
        "authors": clean(r.get("authorString")),
        "abstract": abstract,
        "date": r.get("firstPublicationDate") or r.get("firstIndexDate"),
        "source": journal or "Journal",
        "journal_names": [] if is_pp else journal_names,
        "kind": "preprint" if is_pp else "journal",
        "url": url,
        "institution": "",
        "published_doi": None,
        "pubtype": "review" if "review" in " ".join(ptypes) else "",
    }


def fetch_crossref(cfg, journals_cfg, start: dt.date, end: dt.date) -> list[dict]:
    """Journals not indexed in PubMed/Europe PMC, fetched by ISSN from Crossref."""
    base = "https://api.crossref.org"
    extra = {"mailto": cfg["mailto"]} if cfg.get("mailto") else {}
    out = []
    for g in journals_cfg["groups"].values():
        for j in g["list"]:
            if not j.get("crossref"):
                continue
            issn = j.get("issn")
            if not issn:  # look the journal up by name
                js = get_json(f"{base}/journals", {"query": j.get("full", j["name"]), "rows": 10, **extra})
                items = (js or {}).get("message", {}).get("items", [])
                want = norm_journal(j.get("full", j["name"]))
                hit = next((it for it in items if norm_journal(it.get("title", "")) == want), None)
                issn = (hit or {}).get("ISSN", [None])[0]
            if not issn:
                log(f"Crossref: could not find ISSN for {j['name']}")
                continue
            cursor, n = "*", 0
            while n < 3000:
                js = get_json(f"{base}/journals/{issn}/works", {
                    "filter": f"from-pub-date:{start},until-pub-date:{end},type:journal-article",
                    "rows": 500, "cursor": cursor, **extra})
                msg = (js or {}).get("message", {})
                items = msg.get("items", [])
                for it in items:
                    n += 1
                    title = clean(" ".join(it.get("title") or []))
                    doi = it.get("DOI")
                    if not title or not doi:
                        continue
                    parts = (it.get("published-online") or it.get("published") or it.get("issued") or {}).get("date-parts", [[None]])[0]
                    date = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts) if x) if parts and parts[0] else None
                    if date and len(date) < 10:
                        date = (date + "-01-01")[:10]
                    authors = "; ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                                        for a in it.get("author", []))
                    out.append({
                        "id": f"doi:{doi.lower()}", "doi": doi, "title": title, "authors": authors,
                        "abstract": clean(it.get("abstract")), "date": date,
                        "source": j["name"], "journal_names": [j["name"]], "kind": "journal",
                        "url": f"https://doi.org/{doi}", "institution": "", "published_doi": None,
                        "pubtype": "review" if "review" in (it.get("type") or "") else "",
                    })
                nxt = msg.get("next-cursor")
                if not items or not nxt or nxt == cursor:
                    break
                cursor = nxt
                time.sleep(0.5)
            log(f"Crossref [{j['name']}] -> {n} items")
    return out


def norm_journal(name: str) -> str:
    n = (name or "").lower()
    n = re.sub(r"\(.*?\)", "", n)            # drop "(New York, N.Y. : 1991)"
    n = re.split(r"\s:\s|;", n)[0]          # drop subtitles ("Brain : a journal of neurology")
    n = re.sub(r"&|\band\b", " ", n)          # "&" and "and" are equivalent
    n = re.sub(r"^\s*the\s+", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


def journal_index(jcfg) -> dict:
    idx = {}
    for gkey, g in jcfg["groups"].items():
        for j in g["list"]:
            for nm in (j["name"], j.get("full"), j.get("abbr")):
                if nm:
                    idx[norm_journal(nm)] = (j["name"], gkey)
    return idx


def resolve_journal(p, idx):
    """Set canonical journal name + group; returns True if the journal is listed."""
    if p["kind"] != "journal":
        p["jgroup"] = None
        return True
    for nm in p.get("journal_names") or [p.get("source", "")]:
        k = norm_journal(nm)
        hit = idx.get(k)
        if hit:
            p["source"], p["jgroup"] = hit
            return True
    p["jgroup"] = None
    return False


# ---------------------------------------------------------------------------
# Tagging & scoring
# ---------------------------------------------------------------------------
def compile_groups(cfg):
    def comp(d):
        return {k: [re.compile(p, re.I) for p in v["patterns"]] for k, v in d.items()}
    return comp(cfg["topics"]), comp(cfg["species"]), comp(cfg["methods"])


def score_paper(p, cfg, rx):
    rx_topics, rx_species, rx_methods = rx
    title, abstract = p["title"], p.get("abstract", "")
    text = f"{title} \n {abstract}"
    hits: set[str] = set()
    topics, breakdown, T = [], {}, 0.0
    for key, pats in rx_topics.items():
        w = cfg["topics"][key]["weight"]
        in_title = False
        abs_terms = set()
        for rgx in pats:
            for m in rgx.finditer(title):
                in_title = True
                hits.add(m.group(0))
            for m in rgx.finditer(abstract):
                abs_terms.add(m.group(0).lower())
                hits.add(m.group(0))
        s = w * ((3 if in_title else 0) + min(len(abs_terms), 3))
        if s > 0:
            topics.append(key)
            breakdown[key] = round(s, 2)
            T += s
    species = []
    for key, pats in rx_species.items():
        for rgx in pats:
            m = rgx.search(text)
            if m:
                species.append(key)
                hits.add(m.group(0))
                break
    # 'monkey' alone shouldn't add "Other primate" when macaque/marmoset already named
    if "other_nhp" in species and ({"macaque", "marmoset"} & set(species)):
        species.remove("other_nhp")
    methods, M = [], 0.0
    for key, pats in rx_methods.items():
        for rgx in pats:
            m = rgx.search(text)
            if m:
                methods.append(key)
                M += cfg["methods"][key]["bonus"]
                hits.add(m.group(0))
                break
    M = min(M, 4.0)
    S = max([cfg["species"][s]["mult"] for s in species] or [1.0])
    score = (T + M) * S if T > 0 else 0.0
    if p.get("jgroup"):
        score *= (cfg.get("journals") or {}).get("boost", 1.0)
    p.update({
        "score": round(score, 2),
        "topics": topics,
        "species": species,
        "methods": methods,
        "hits": sorted(hits, key=len, reverse=True)[:40],
        "breakdown": breakdown,
    })
    return p


# ---------------------------------------------------------------------------
# Archive & site
# ---------------------------------------------------------------------------
def merge(archive: dict, new: list[dict], run_date: str) -> dict:
    by_title = {norm_title(p["title"]): k for k, p in archive.items()}
    for p in new:
        key = p["id"]
        tkey = norm_title(p["title"])
        # Same paper via another route (preprint on bioRxiv and Europe PMC, or
        # preprint later published under the same title): keep one record.
        if key not in archive and tkey in by_title:
            old = archive[by_title[tkey]]
            if p["kind"] == "journal" and old["kind"] == "preprint":
                p["first_seen"] = old.get("first_seen", run_date)
                p["preprint_url"] = old["url"]
                del archive[by_title[tkey]]
                archive[key] = p
                by_title[tkey] = key
            elif old["source"] == "bioRxiv" and not old.get("abstract") and p.get("abstract"):
                old["abstract"] = p["abstract"]
            continue
        if key in archive:
            old = archive[key]
            # bioRxiv's own record is richer than its Europe PMC mirror
            if old.get("source") == "bioRxiv" and p.get("source") != "bioRxiv" and p["kind"] == "preprint":
                continue
            p["first_seen"] = old.get("first_seen", run_date)
            if len(old.get("abstract") or "") > len(p.get("abstract") or ""):
                p["abstract"] = old["abstract"]
        else:
            p["first_seen"] = run_date
        archive[key] = p
        by_title[tkey] = key
    return archive


def build_site(papers: list[dict], cfg, run_date: str, stats: dict, fragment=False) -> str:
    meta = {
        "title": cfg["site"]["title"],
        "subtitle": cfg["site"]["subtitle"],
        "updated": run_date,
        "window_days": cfg["site"]["window_days"],
        "stats": stats,
        "topics": {k: {"label": v["label"], "color": v["color"]} for k, v in cfg["topics"].items()},
        "species": {k: {"label": v["label"]} for k, v in cfg["species"].items()},
        "methods": {k: {"label": v["label"]} for k, v in cfg["methods"].items()},
        "jgroups": {k: {"label": v["label"]} for k, v in cfg["journals"]["groups"].items()},
    }
    keep = ["id", "doi", "title", "authors", "abstract", "date", "source", "kind", "url",
            "institution", "published_doi", "pubtype", "score", "topics", "species", "methods",
            "hits", "breakdown", "first_seen", "preprint_url", "jgroup"]
    slim = [{k: p.get(k) for k in keep if p.get(k) not in (None, "", [], {})} for p in papers]
    payload = json.dumps({"meta": meta, "papers": slim}, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    body = TEMPLATE.read_text().replace("__DATA__", payload)
    if fragment:
        return body
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            "</head><body>\n" + body + "\n</body></html>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--days", type=int)
    ap.add_argument("--fragment", help="also write a skeleton-less copy to this path")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    days = args.days or cfg["site"]["window_days"]
    cfg["site"]["window_days"] = days
    start, end = TODAY - dt.timedelta(days=days), TODAY
    run_date = TODAY.isoformat()

    archive = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {}
    stats = {"fetched": 0}
    if not args.build_only:
        new = []
        if cfg["sources"]["biorxiv"]["enabled"]:
            new += fetch_biorxiv(cfg["sources"]["biorxiv"], start, end)
        if cfg["sources"]["europepmc"]["enabled"]:
            new += fetch_europepmc(cfg["sources"]["europepmc"], cfg["topics"], start, end)
        if cfg["sources"].get("crossref", {}).get("enabled"):
            new += fetch_crossref(cfg["sources"]["crossref"], cfg["journals"], start, end)
        stats["fetched"] = len(new)
        archive = merge(archive, new, run_date)
    else:
        run_date = max([p.get("first_seen", "") for p in archive.values()] or [run_date])

    # drop anything that has fallen out of the window
    cutoff = (TODAY - dt.timedelta(days=days)).isoformat()
    archive = {k: p for k, p in archive.items() if (p.get("date") or run_date) >= cutoff}

    # journal list: canonical names, groups, and (mode: only) drop unlisted journals
    idx = journal_index(cfg["journals"])
    unlisted = {}
    listed = {}
    for k, p in archive.items():
        if resolve_journal(p, idx) or cfg["journals"].get("mode", "only") != "only":
            listed[k] = p
        else:
            unlisted[p["source"]] = unlisted.get(p["source"], 0) + 1
    if unlisted:
        top = sorted(unlisted.items(), key=lambda kv: -kv[1])[:40]
        log(f"Skipped {sum(unlisted.values())} papers from {len(unlisted)} unlisted journals. Most frequent:")
        for name, n in top:
            log(f"  {n:4d}  {name}")
    stats["unlisted_journals"] = len(unlisted)

    rx = compile_groups(cfg)
    scored = [score_paper(p, cfg, rx) for p in listed.values()]
    keep = [p for p in scored if p["score"] >= cfg["site"]["min_score"]]
    keep.sort(key=lambda p: (-p["score"], p["date"] or ""))
    stats.update({"archive": len(archive), "shown": len(keep),
                  "preprints": sum(p["kind"] == "preprint" for p in keep),
                  "journal": sum(p["kind"] == "journal" for p in keep)})
    log(f"archive {len(archive)} | shown {len(keep)}")

    # Archive keeps only relevant papers (+ scores recomputed every run)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps({p["id"]: p for p in keep}, ensure_ascii=False, indent=0))
    SITE.parent.mkdir(parents=True, exist_ok=True)
    SITE.write_text(build_site(keep, cfg, run_date, stats))
    if args.fragment:
        Path(args.fragment).write_text(build_site(keep, cfg, run_date, stats, fragment=True))
    log(f"wrote {SITE}")


if __name__ == "__main__":
    main()
