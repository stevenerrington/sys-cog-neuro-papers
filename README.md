# Systems & Cognitive Neuro Digest

A daily-updated, filterable digest of new systems and cognitive neuroscience papers on
**auditory processing, predictive coding, memory and sequences**. It trawls bioRxiv
and 89 journals, scores each paper for relevance, and ranks papers so that macaque and
marmoset work comes first, followed by human and rodent studies.

**Live site:** `https://<your-username>.github.io/<repo-name>/`

Inspired by [biorxiv-top](https://robertodf.github.io/biorxiv-top/), which ranks
bioRxiv preprints by how much they are read. This digest ranks papers by how relevant
they are to a set of research topics.

---

## What it does

Every morning a GitHub Action does the following:

1. **Fetches** new papers from the last 30 days:
   - **bioRxiv**: every new preprint in *Neuroscience* and *Animal Behavior & Cognition*.
   - **Europe PMC**: mirrors PubMed, plus medRxiv, PsyArXiv, Research Square and other
     preprint servers. Each topic is searched in titles and abstracts.
   - **Crossref**: covers the six listed journals that PubMed doesn't index.
2. **Keeps** journal articles only if they come from the [journal list](#journals).
   Preprints are always kept.
3. **Tags** every paper by topic, species and method using the keyword patterns in
   `config.yaml`.
4. **Scores and ranks** the papers (see [How ranking works](#how-ranking-works)).
5. **Rebuilds** the site in `docs/index.html` and commits it. GitHub Pages then serves
   the new version.

### On the site

- A ranked list showing each paper's relevance score and days since posting.
- Filters for **topic**, **species**, **method**, **journal group**, **individual
  journal**, **source** (preprints or journals) and **posting window** (7, 14 or 30 days).
- An **Any / All** switch, which controls whether a paper must match any or all of the
  selected filters.
- Free-text search over titles, abstracts and authors.
- A **"new" label**, plus a filter for papers added since the last update.
- An expandable abstract for each paper, with matched terms highlighted and a breakdown
  of why it ranked where it did.
- Light and dark themes, and a layout that works on phones.

---

## Topics

| Topic | Weight | Example terms |
|---|---|---|
| Auditory processing | 1.5 | auditory, hearing, pitch, speech, syllable, music, tonotopy, inferior colliculus, belt/parabelt |
| Predictive coding | 1.6 | prediction error, mismatch negativity, oddball, deviant, stimulus-specific adaptation, repetition suppression, surprise |
| Local–global | 2.2 | local–global paradigm, global deviant, hierarchical/nested regularities |
| Closed-loop auditory stimulation | 2.2 | closed-loop acoustic stimulation, phase-locked auditory stimulation, slow-oscillation enhancement |
| Optogenetics | 1.2 | optogenetic, channelrhodopsin, ChR2, ChRmine, GtACR, photoinhibition |
| Chemogenetics | 1.4 | chemogenetic, DREADD, hM3Dq/hM4Di, DCZ, CNO, PSAM |
| Memory | 0.7 | working/episodic/recognition memory, consolidation, engram, recall |
| Auditory memory | 2.2 | auditory working memory, echoic memory, tonal/pitch memory |
| Sequences | 1.3 | sequence learning, statistical learning, serial order, chunking, transitional probability |
| (Non-)adjacent dependencies | 2.2 | non-adjacent dependencies, artificial grammar, phrase-structure grammar, syntax |
| Vocalisations | 1.6 | vocalisation, vocal communication, contact/phee calls, birdsong, USVs |

**Species** (score multiplier): macaque ×2, marmoset ×2, other primate ×1.6, human
×1.25, rodent ×1.15, other ×1.

**Methods** (bonus added to the score): single units +2, LFP +2, fMRI +2, intracranial
(ECoG/sEEG) +1.5, EEG/MEG +1, calcium imaging +0.5, perturbation +0.5, modelling +0.5.

---

## How ranking works

For each topic, a paper scores **3 × weight** if the topic appears in its title, plus
**1 × weight** for each distinct matching term in its abstract (up to 3 terms). The
topic scores are added together, then the method bonuses (capped at 4). The total is
multiplied by the highest-scoring species found in the paper:

```
score = (Σ topic scores + method bonus) × species multiplier
```

For example, a macaque paper on sequence working memory using single units would get
sequences 7.8 + memory 2.8 + optogenetics 1.2 + method bonus 2.5 = 14.3, then × 2
(macaque) = **28.6**.

Papers scoring below `site.min_score` (default 3) are dropped. Every run re-scores the
whole archive, so changes to weights or patterns apply to papers already shown.

---

## Journals

Journal articles are kept only from these 89 journals (`journals.mode: only`). Each group
below is a filter on the site. Journals marked † aren't in PubMed, so they're fetched
from Crossref. Crossref often has no abstract for them, so they are ranked on their
titles alone.

<details>
<summary><b>Show the full list</b></summary>

**Flagship & broad (12):** Nature Neuroscience, Neuron, Nature, Science, Cell, Nature
Communications, PNAS, Current Biology, eLife, Science Advances, Nature Human Behaviour,
Cell Reports

**Reviews & opinion (11):** Trends in Cognitive Sciences, Nature Reviews Neuroscience,
Annual Review of Neuroscience, Trends in Neurosciences, Current Opinion in
Neurobiology, Current Opinion in Behavioral Sciences†, Neuroscience & Biobehavioral
Reviews, Progress in Neurobiology, Nature Reviews Psychology†, Nature Reviews Methods
Primers†, Behavioral and Brain Sciences

**Systems neuroscience (13):** Journal of Neuroscience, Journal of Neurophysiology,
Cerebral Cortex, European Journal of Neuroscience, Neuroscience, Neuroscience Letters,
Brain Research, Experimental Brain Research, Journal of Comparative Neurology,
Frontiers in Neural Circuits, Frontiers in Neuroscience, eNeuro, Brain Structure and
Function

**Cognitive neuroscience (9):** Cortex, Journal of Cognitive Neuroscience, Cognitive
Neuroscience, Cognition, Cognitive, Affective, & Behavioral Neuroscience,
Neuropsychologia, Social Cognitive and Affective Neuroscience, Brain and Cognition,
Psychonomic Bulletin & Review

**Imaging & electrophysiology (9):** NeuroImage, Imaging Neuroscience, NeuroImage:
Reports†, Human Brain Mapping, Psychophysiology, Clinical Neurophysiology, Clinical
Neurophysiology Practice, Brain Topography, Brain Stimulation

**Computational & engineering (11):** Neural Computation, PLoS Computational Biology,
Journal of Computational Neuroscience, Network Neuroscience, Neuroinformatics, Journal
of Neural Engineering, IEEE Transactions on Biomedical Engineering, Neurocomputing†,
Nature Machine Intelligence†, Nature Computational Science, Patterns

**Animal behaviour & cognition (6):** Behavioural Brain Research, Behavioral
Neuroscience, Animal Cognition, Journal of Comparative Psychology, Journal of
Experimental Psychology: Animal Learning and Cognition, Learning & Behavior

**Clinical & psychiatry (12):** Brain, Annals of Neurology, Neurology, Lancet
Neurology, JAMA Neurology, Nature Medicine, Molecular Psychiatry, Biological
Psychiatry, Biological Psychiatry: CNNI, Neuropsychopharmacology, Journal of
Neurology, Neurosurgery & Psychiatry, Acta Neuropathologica

**Cellular, molecular & development (6):** Molecular Neurobiology, Journal of
Neurochemistry, Glia, Journal of Neuroinflammation, Developmental Cell, Development

</details>

Matching ignores case, punctuation, a leading "The", and subtitles or place names in
parentheses. For example, PubMed's "Cerebral cortex (New York, N.Y. : 1991)" matches
**Cerebral Cortex**, and "The Lancet. Neurology" matches **Lancet Neurology**. Each run
logs which unlisted journals were skipped most often, so it's easy to spot ones worth
adding.

---

## Setup

You'll need a GitHub account. Setup takes about five minutes.

1. **Create a repository**, e.g. `neuro-digest`. A public repository is simplest,
   because GitHub Pages is free for public repos.
2. **Push this folder** to it, keeping the hidden `.github` folder:
   ```bash
   cd neuro-digest
   git init && git add . && git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/neuro-digest.git
   git push -u origin main
   ```
3. **Turn on Pages**: go to **Settings → Pages → Build and deployment**, set Source to
   *Deploy from a branch*, Branch to `main` and folder to **`/docs`**, then click
   **Save**.
4. **Allow the workflow to commit**: go to **Settings → Actions → General → Workflow
   permissions**, choose **Read and write permissions**, then click **Save**.
5. **Run the first update**: go to **Actions → Update digest** and click **Run
   workflow**. The first run takes about 2–5 minutes.

The site then refreshes every day at 05:17 UTC. Pushing a change to `config.yaml`,
`template.html` or `trawl.py` also triggers a rebuild. To refresh at any other time, run
the workflow by hand from the Actions tab.

---

## Configuration

Everything is set in **`config.yaml`**, so you don't need to touch any code.

| Setting | What it controls |
|---|---|
| `site.title`, `site.subtitle` | Page heading |
| `site.window_days` | Rolling window (default 30) |
| `site.min_score` | Relevance cut-off (default 3) |
| `sources.biorxiv.categories` | bioRxiv subject areas to pull |
| `sources.europepmc.context` | Neuroscience terms ANDed onto every Europe PMC query, so broad words like "memory" stay on topic |
| `sources.crossref.mailto` | Optional email address; puts Crossref requests in its faster "polite" pool |
| `journals.mode` | `only` keeps listed journals only; `all` keeps every journal |
| `journals.groups` | The journal list and its groups |
| `journals.boost` | Optional score multiplier for listed journals (useful with `mode: all`) |
| `topics.*` | Label, colour, weight, Europe PMC search phrases (`query`), and tagging regexes (`patterns`) |
| `species.*.mult` | Species multipliers |
| `methods.*.bonus` | Method bonuses |

**To add a journal**, add a line to any group:
```yaml
- {name: "Hearing Research", abbr: "Hear Res"}
```
If PubMed doesn't index the journal, add `crossref: true` to that line.

**To add a topic**, add a block under `topics:`. It appears on the site as a new filter
chip.
```yaml
  timing:
    label: "Timing"
    color: "#6d5bd0"
    weight: 1.5
    query: ["interval timing", "temporal expectation", "duration perception"]
    patterns: ['interval timing', 'temporal (expectation|prediction)', 'duration']
```

`query` controls what gets **fetched** from journals. `patterns` controls how every paper
is **tagged and scored**, including bioRxiv preprints.

---

## Running locally

```bash
pip install -r requirements.txt
python trawl.py                # fetch everything and build docs/index.html
python trawl.py --days 7       # use a shorter window
python trawl.py --build-only   # rebuild from the saved archive with no network
                               # (after editing config.yaml or template.html)
open docs/index.html
```

---

## Repository layout

```
config.yaml                    topics, species, methods, journals, settings
trawl.py                       fetching, tagging, scoring and site building
template.html                  front end; the data is inlined at build time
docs/index.html                the built site (served by GitHub Pages)
data/archive.json              rolling archive; records when each paper was first seen
.github/workflows/update.yml   daily schedule
preview/                       offline preview built from sample bioRxiv data (optional)
```

---

## Limitations

- **Tagging is keyword-based.** A paper counts as "Macaque" only if its title or
  abstract says macaque, rhesus or Macaca. "Monkey" alone is tagged *Other primate*.
  Papers that don't mention a topic term won't score, however relevant they are.
- **Crossref journals rank lower**, because their abstracts are often missing.
- **Dates come from the sources.** Europe PMC uses each article's first publication
  date, so an article indexed late can appear a few days after it was published.
- **The archive keeps only papers above `min_score`.** If you lower the threshold, the
  extra papers appear from the next fetch onwards.
- **API limits.** bioRxiv, Europe PMC and Crossref are free, public APIs. A daily run
  makes a few hundred requests, which is well within their fair-use limits.

---

## Data sources

- [bioRxiv API](https://api.biorxiv.org/)
- [Europe PMC REST API](https://europepmc.org/RestfulWebService)
- [Crossref REST API](https://api.crossref.org/)

Paper metadata and abstracts belong to their authors and publishers. This site links
to the original articles.
