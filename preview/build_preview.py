"""Build an offline preview from sample bioRxiv records (no network)."""
import sys, json, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml, trawl
from sample_biorxiv import R

cfg = yaml.safe_load(trawl.CONFIG.read_text())
recs = []
for p in R:
    recs.append({"id": f"doi:{p['doi'].lower()}", "doi": p["doi"], "title": p["title"], "authors": p["authors"],
                 "abstract": p["abstract"], "date": p["date"], "source": "bioRxiv", "kind": "preprint",
                 "url": f"https://www.biorxiv.org/content/{p['doi']}v1", "institution": p["institution"],
                 "published_doi": None, "pubtype": "new results"})
archive = {}
for r in recs:  # simulate daily runs: first seen the day after posting
    seen = (dt.date.fromisoformat(r["date"]) + dt.timedelta(days=1)).isoformat()
    archive = trawl.merge(archive, [r], seen)
rx = trawl.compile_groups(cfg)
scored = [trawl.score_paper(p, cfg, rx) for p in archive.values()]
keep = sorted([p for p in scored if p["score"] >= cfg["site"]["min_score"]], key=lambda p: -p["score"])
drop = [p for p in scored if p["score"] < cfg["site"]["min_score"]]
for p in keep: print(f"{p['score']:6.1f}  {','.join(p['species']):22s} {','.join(p['topics']):45s} {p['title'][:70]}")
print("dropped:", [(p['score'], p['title'][:50]) for p in drop])
stats = {"preview": "Preview · bioRxiv only, 23 Sep – 6 Oct"}
out = trawl.build_site(keep, cfg, "2026-10-07", stats, fragment=True)
Path(sys.argv[1]).write_text(out)
Path(sys.argv[2]).write_text(trawl.build_site(keep, cfg, "2026-10-07", stats))
