---
license: cc-by-nc-4.0
task_categories:
  - feature-extraction
  - text-classification
language:
  - en
  - de
  - es
  - fr
  - cs
  - it
  - ru
  - pl
  - pt
  - el
  - zh
  - ja
  - nl
  - sr
  - ro
  - ar
  - uk
  - mn
  - ko
  - tr
  - sv
  - he
  - hu
tags:
  - fragrance
  - perfume
  - cosmetics
  - recommendation-system
  - e-commerce
  - retail
  - fragrantika
  - multilingual
size_categories:
  - n<1K
configs:
  - config_name: fragrances
    data_files: fragrances.csv
    default: true
    sep: "|"
  - config_name: brands
    data_files: brands.csv
    sep: "|"
  - config_name: perfumers
    data_files: perfumers.csv
    sep: "|"
  - config_name: notes
    data_files: notes.csv
    sep: "|"
  - config_name: accords
    data_files: accords.csv
    sep: "|"
  - config_name: translations
    data_files: translations.csv
    sep: "|"
dataset_info:
  - config_name: fragrances
    features:
      - name: pid
        dtype: int64
      - name: url
        dtype: string
      - name: brand
        dtype: string
      - name: name
        dtype: string
      - name: year
        dtype: int64
      - name: gender
        dtype: string
      - name: collection
        dtype: string
      - name: main_photo
        dtype: string
      - name: info_card
        dtype: string
      - name: user_photoes
        dtype: string
      - name: video_url
        dtype: string
      - name: accords
        dtype: string
      - name: notes_pyramid
        dtype: string
      - name: perfumers
        dtype: string
      - name: description
        dtype: string
      - name: rating
        dtype: string
      - name: reviews_count
        dtype: int64
      - name: appreciation
        dtype: string
      - name: price_value
        dtype: string
      - name: gender_votes
        dtype: string
      - name: longevity
        dtype: string
      - name: sillage
        dtype: string
      - name: season
        dtype: string
      - name: time_of_day
        dtype: string
      - name: pros_cons
        dtype: string
      - name: by_designer
        dtype: string
      - name: in_collection
        dtype: string
      - name: reminds_of
        dtype: string
      - name: also_like
        dtype: string
      - name: news_ids
        dtype: string
  - config_name: brands
    features:
      - name: id
        dtype: string
      - name: name
        dtype: string
      - name: url
        dtype: string
      - name: logo_url
        dtype: string
      - name: country
        dtype: string
      - name: main_activity
        dtype: string
      - name: website
        dtype: string
      - name: parent_company
        dtype: string
      - name: description
        dtype: string
      - name: brand_count
        dtype: int64
      - name: country_de
        dtype: string
      - name: country_es
        dtype: string
      - name: country_fr
        dtype: string
      - name: country_cs
        dtype: string
      - name: country_it
        dtype: string
      - name: country_ru
        dtype: string
      - name: country_pl
        dtype: string
      - name: country_pt
        dtype: string
      - name: country_el
        dtype: string
      - name: country_zh
        dtype: string
      - name: country_ja
        dtype: string
      - name: country_nl
        dtype: string
      - name: country_sr
        dtype: string
      - name: country_ro
        dtype: string
      - name: country_ar
        dtype: string
      - name: country_uk
        dtype: string
      - name: country_mn
        dtype: string
      - name: country_ko
        dtype: string
      - name: country_tr
        dtype: string
      - name: country_sv
        dtype: string
      - name: country_he
        dtype: string
      - name: country_hu
        dtype: string
      - name: main_activity_de
        dtype: string
      - name: main_activity_es
        dtype: string
      - name: main_activity_fr
        dtype: string
      - name: main_activity_cs
        dtype: string
      - name: main_activity_it
        dtype: string
      - name: main_activity_ru
        dtype: string
      - name: main_activity_pl
        dtype: string
      - name: main_activity_pt
        dtype: string
      - name: main_activity_el
        dtype: string
      - name: main_activity_zh
        dtype: string
      - name: main_activity_ja
        dtype: string
      - name: main_activity_nl
        dtype: string
      - name: main_activity_sr
        dtype: string
      - name: main_activity_ro
        dtype: string
      - name: main_activity_ar
        dtype: string
      - name: main_activity_uk
        dtype: string
      - name: main_activity_mn
        dtype: string
      - name: main_activity_ko
        dtype: string
      - name: main_activity_tr
        dtype: string
      - name: main_activity_sv
        dtype: string
      - name: main_activity_he
        dtype: string
      - name: main_activity_hu
        dtype: string
  - config_name: perfumers
    features:
      - name: id
        dtype: string
      - name: name
        dtype: string
      - name: url
        dtype: string
      - name: photo_url
        dtype: string
      - name: status
        dtype: string
      - name: company
        dtype: string
      - name: also_worked
        dtype: string
      - name: education
        dtype: string
      - name: web
        dtype: string
      - name: perfumes_count
        dtype: int64
      - name: biography
        dtype: string
      - name: status_de
        dtype: string
      - name: status_es
        dtype: string
      - name: status_fr
        dtype: string
      - name: status_cs
        dtype: string
      - name: status_it
        dtype: string
      - name: status_ru
        dtype: string
      - name: status_pl
        dtype: string
      - name: status_pt
        dtype: string
      - name: status_el
        dtype: string
      - name: status_zh
        dtype: string
      - name: status_ja
        dtype: string
      - name: status_nl
        dtype: string
      - name: status_sr
        dtype: string
      - name: status_ro
        dtype: string
      - name: status_ar
        dtype: string
      - name: status_uk
        dtype: string
      - name: status_mn
        dtype: string
      - name: status_ko
        dtype: string
      - name: status_tr
        dtype: string
      - name: status_sv
        dtype: string
      - name: status_he
        dtype: string
      - name: status_hu
        dtype: string
      - name: perfumer_name_ru
        dtype: string
      - name: perfumer_name_uk
        dtype: string
      - name: perfumer_name_ja
        dtype: string
      - name: perfumer_name_zh
        dtype: string
      - name: perfumer_name_ko
        dtype: string
      - name: perfumer_name_ar
        dtype: string
      - name: perfumer_name_he
        dtype: string
      - name: perfumer_name_el
        dtype: string
      - name: perfumer_name_mn
        dtype: string
  - config_name: notes
    features:
      - name: id
        dtype: string
      - name: name
        dtype: string
      - name: url
        dtype: string
      - name: latin_name
        dtype: string
      - name: other_names
        dtype: string
      - name: group
        dtype: string
      - name: odor_profile
        dtype: string
      - name: main_icon
        dtype: string
      - name: alt_icons
        dtype: string
      - name: background
        dtype: string
      - name: fragrance_count
        dtype: int64
      - name: note_name_de
        dtype: string
      - name: note_name_es
        dtype: string
      - name: note_name_fr
        dtype: string
      - name: note_name_cs
        dtype: string
      - name: note_name_it
        dtype: string
      - name: note_name_ru
        dtype: string
      - name: note_name_pl
        dtype: string
      - name: note_name_pt
        dtype: string
      - name: note_name_el
        dtype: string
      - name: note_name_zh
        dtype: string
      - name: note_name_ja
        dtype: string
      - name: note_name_nl
        dtype: string
      - name: note_name_sr
        dtype: string
      - name: note_name_ro
        dtype: string
      - name: note_name_ar
        dtype: string
      - name: note_name_uk
        dtype: string
      - name: note_name_mn
        dtype: string
      - name: note_name_ko
        dtype: string
      - name: note_name_tr
        dtype: string
      - name: note_name_sv
        dtype: string
      - name: note_name_he
        dtype: string
      - name: note_name_hu
        dtype: string
      - name: note_group_de
        dtype: string
      - name: note_group_es
        dtype: string
      - name: note_group_fr
        dtype: string
      - name: note_group_cs
        dtype: string
      - name: note_group_it
        dtype: string
      - name: note_group_ru
        dtype: string
      - name: note_group_pl
        dtype: string
      - name: note_group_pt
        dtype: string
      - name: note_group_el
        dtype: string
      - name: note_group_zh
        dtype: string
      - name: note_group_ja
        dtype: string
      - name: note_group_nl
        dtype: string
      - name: note_group_sr
        dtype: string
      - name: note_group_ro
        dtype: string
      - name: note_group_ar
        dtype: string
      - name: note_group_uk
        dtype: string
      - name: note_group_mn
        dtype: string
      - name: note_group_ko
        dtype: string
      - name: note_group_tr
        dtype: string
      - name: note_group_sv
        dtype: string
      - name: note_group_he
        dtype: string
      - name: note_group_hu
        dtype: string
  - config_name: accords
    features:
      - name: id
        dtype: string
      - name: name
        dtype: string
      - name: bar_color
        dtype: string
      - name: font_color
        dtype: string
      - name: fragrance_count
        dtype: int64
      - name: name_de
        dtype: string
      - name: name_es
        dtype: string
      - name: name_fr
        dtype: string
      - name: name_cs
        dtype: string
      - name: name_it
        dtype: string
      - name: name_ru
        dtype: string
      - name: name_pl
        dtype: string
      - name: name_pt
        dtype: string
      - name: name_el
        dtype: string
      - name: name_zh
        dtype: string
      - name: name_ja
        dtype: string
      - name: name_nl
        dtype: string
      - name: name_sr
        dtype: string
      - name: name_ro
        dtype: string
      - name: name_ar
        dtype: string
      - name: name_uk
        dtype: string
      - name: name_mn
        dtype: string
      - name: name_ko
        dtype: string
      - name: name_tr
        dtype: string
      - name: name_sv
        dtype: string
      - name: name_he
        dtype: string
      - name: name_hu
        dtype: string
  - config_name: translations
    features:
      - name: id
        dtype: string
      - name: section
        dtype: string
      - name: en
        dtype: string
      - name: de
        dtype: string
      - name: es
        dtype: string
      - name: fr
        dtype: string
      - name: cs
        dtype: string
      - name: it
        dtype: string
      - name: ru
        dtype: string
      - name: pl
        dtype: string
      - name: pt
        dtype: string
      - name: el
        dtype: string
      - name: zh
        dtype: string
      - name: ja
        dtype: string
      - name: nl
        dtype: string
      - name: sr
        dtype: string
      - name: ro
        dtype: string
      - name: ar
        dtype: string
      - name: uk
        dtype: string
      - name: mn
        dtype: string
      - name: ko
        dtype: string
      - name: tr
        dtype: string
      - name: sv
        dtype: string
      - name: he
        dtype: string
      - name: hu
        dtype: string
---

# FragDB v5.15 — Fragrance Database (Multilingual Sample)

The most comprehensive structured fragrance database available. This is a **free sample** of FragDB: **139,501 perfumes, 23 languages** — 10-row CSV samples at root.

Full dataset: [fragdb.net](https://fragdb.net).

## What's New in v5.15

- **Data updated** from v5.14 → v5.15 (full source recrawl, parser run 260910):
  - Fragrances: 137,789 → **139,501** (+1,712)
  - Brands: 8,247 → **8,272** (+25)
  - Perfumers: 3,110 → **3,116** (+6)
  - Notes: 2,592 → **2,596** rows in `notes.csv` (+7 new, 3 retired)
- **Three note IDs retired** — the source merged case duplicates: `n473` → `n2661` (Heather),
  `n653` → `n2646` (Icing Pink), `n813` → `n2660` (Hazelnut Cocoa Spread). No fragrance
  references the retired IDs.
- **Figures on this card restated from the release files.** The notes figure is now the row
  count of `notes.csv`, the number fragdb.net shows; the full-database totals had stayed at
  v5.10. Review coverage and foreign-key figures are measured against this catalogue.
- **Reviews, news and news comments** — the same parquet files as v5.14.
- **Sample files unchanged** — the schema is identical to v5.14, so the 10-row CSVs were not
  rebuilt. A sample shows structure, not freshness.

## What's New in v5.14

- **Data updated** from v5.13 → v5.14 (incremental delta, parser run 260901):
  - Fragrances: 137,147 → **137,789** (+642)
  - Brands: 8,210 → **8,247** (+37)
  - Perfumers: 3,102 → **3,110** (+8)
  - Unique note names: **2,586** (unchanged — the notes reference only moves on a full crawl)
- **Sample files unchanged** — the schema is identical to v5.13, so the 10-row CSVs were not
  rebuilt. A sample shows structure, not freshness.

## What's New in v5.13

- **Data updated** from v5.12 → v5.13 (incremental delta, parser run 260819):
  - Fragrances: 136,682 → **137,147** (+465)
  - Brands: 8,175 → **8,210** (+35)
  - Perfumers: 3,090 → **3,102** (+12)
  - Notes: 2,586 → **2,588** (+2) — including `Kiwano`, which arrived with all 22 translations in its first cycle
- **Clean delta**: no perfume changed its canonical URL and none disappeared; field coverage flat across all 30 columns (max movement 0.22 pp)
- **Free sample refreshed** — 10-record CSV samples rebuilt from v5.13 data

## What's New in v5.12

- **Data updated** from v5.10 → v5.12 (full source recrawl, parser run 260809):
  - Fragrances: 135,308 → **136,682** (+1,374)
  - Brands: 8,093 → **8,175** (+82)
  - Perfumers: 3,057 → **3,090** (+33)
  - Notes: 2,573 → **2,586** (+13) — 100% multilingual, verified per language
- **784 records restored** — a resume-scan defect had frozen them since May; their votes, ratings and note pyramids are current again
- **Free sample refreshed** — 10-record CSV samples rebuilt from v5.12 data

## What's New in v5.9

- **Data updated** from v5.8 → v5.9 (parser run 260710):
  - Fragrances: 134,022 → **134,577** (+555)
  - Brands: 8,000 → **8,036** (+36) — **154 brand names canonicalized** (restored `Fragrance(s)` suffix; IDs stable)
  - Perfumers: 3,035 → **3,046** (+11)
  - Notes: 2,562 → **2,567** (+5)
  - URL hygiene: pyramid anchors single-domain, photo cache-busters stripped
- **Free sample refreshed** — 10-record CSV samples rebuilt from v5.9 data

## What's New in v5.8

- **Data updated** from v5.7 → v5.8 (parser run 260701):
  - Fragrances: 133,392 → **134,022** (+630)
  - Brands: 7,953 → **8,000** (+47)
  - Perfumers: 3,020 → **3,035** (+15)
  - Notes: 2,559 → **2,562** (+3)

## What's New in v5.7

- **Data updated** from v5.6 → v5.7 (parser run 260619):
  - Fragrances: 132,858 → **133,392** (+534)
  - Brands: 7,927 → **7,953** (+26)
  - Perfumers: 3,005 → **3,020** (+15)
  - Notes: 2,550 → **2,559** (+9)

## What's New in v5.6

- **Data updated** from v5.5 → v5.6 (parser run 260609):
  - Fragrances: 132,124 → **132,858** (+734)
  - Brands: 7,881 → **7,927** (+46)
  - Perfumers: 2,988 → **3,005** (+17)
  - Notes: 2,533 → **2,550** (+17)
- **Notes multilingual 100% coverage** (was 99.8%) — 6 previously gap-filled notes now complete across all 22 languages
- **Photo URL stability** — source cache-buster query params stripped, eliminating phantom diffs across releases
- Schema unchanged from v5.5 — existing loaders work without modification
- Free sample files unchanged (10-record structure preserved)

## What's New in v5.5

- **Data updated** from v5.4 → v5.5 (parser run 260601):
  - Fragrances: 130,949 → 132,124 (+1,175)
  - Brands: 7,815 → 7,881 (+66)
  - Perfumers: 2,968 → 2,988 (+20)
  - Notes: 2,522 → 2,533 (+11)

### Schema unchanged from v5.4

All F column counts identical (30/54/42/55/27/25) — existing scripts work without modification.

### From v5.4 (unchanged in v5.5)
- **23 languages** — all labels, note names, accords, countries, statuses translated
- **9 non-Latin scripts** for perfumer name transliteration
- **translations.csv** — vocabulary file (34 entries) for gender and voting labels
- **Compact notes pyramid** — `note_id,opacity,weight` (name/icon via notes.csv JOIN)
- Each note name variant has its own ID with translations
- **Gender & voting fields** use translation IDs for multilingual support

## Snapshot freshness

- **Data refreshed**: 2026-09-10 (v5.15)
- **Reviews, news, news comments** (parquet): unchanged in this release — latest review 2026-05-02, latest article 2026-04-28

## Dataset Description

| File | Records | Fields | Description |
|------|---------|--------|-------------|
| `fragrances.csv` | 10 | 30 | Iconic fragrances (v5.9) |
| `brands.csv` | 10 | 54 | Brand profiles + 22 lang translations |
| `perfumers.csv` | 10 | 42 | Perfumer profiles + 22 lang + 9 name translit |
| `notes.csv` | 10 | 55 | Fragrance notes + 22 lang translations |
| `accords.csv` | 10 | 27 | Accords + 22 lang translations |
| `translations.csv` | 34 | 25 | Gender & voting vocabulary (full) |
| `comments_sample.parquet` | 25 | 8 | User reviews preview (parquet) |
| `news_sample.parquet` | 20 | 16 | Editorial articles preview (parquet) |
| `news_comments_sample.parquet` | 20 | 9 | News comments preview (parquet) |
| `SPEC.md` | — | — | Parquet schema documentation |

### Loading the data

```python
from datasets import load_dataset

f = load_dataset("FragDBnet/fragrance-database")           # fragrances (default)
brands = load_dataset("FragDBnet/fragrance-database", "brands")
notes  = load_dataset("FragDBnet/fragrance-database", "notes")
```

## Companion Parquet Datasets — User Reviews, News, and Community Comments

FragDB ships with **three Apache Parquet datasets** containing **4.9 million rows** of user-generated content and editorial coverage — the largest publicly-organized corpus of fragrance reviews and perfumery journalism. Use them for NLP, sentiment analysis, recommendation systems, market research, or training language models on fragrance-specific text.

**Keywords:** fragrance reviews · perfume reviews · multilingual UGC corpus · NLP training data · fragrance sentiment · perfumery journalism · perfume recommendation · scent recommendation · review classification · entity linking · knowledge graph · fragrance industry news · perfume articles

### `comments.parquet` — 4.6 Million User Reviews in 23 Languages

The world's largest collection of structured fragrance reviews. Every entry includes the perfume ID (joinable with `fragrances.csv`), author username, posting date, full review text, avatar URL, and language code.

- **4,643,851 user reviews** covering every major perfume in the database
- **23 languages** — English (1.69M), Russian, Portuguese, Spanish, Korean, Turkish, Japanese, Polish, Italian, Hungarian, Serbian, Swedish, German, Hebrew, Ukrainian, French, Arabic, Greek, Czech, Chinese, Romanian, Mongolian, Dutch
- **Coverage:** 66.9% of all fragrances have at least one review (93,296 of 139,501 PIDs)
- **Deterministic global primary key** — stable comment IDs survive re-scrapes
- **Zero duplicate rows**; every `pid` joins `fragrances.csv` except 46 reviews (0.001%) on 9 perfumes no longer in the catalogue
- **Independent UGC per language** — genuine localized content, not machine translation
- **8 fields:** `pid`, `lang`, `comment_id`, `author`, `date`, `text`, `avatar_url`, `gradient_class`
- **PyArrow large_string format** — combined corpus exceeds 32-bit string offset limit

**Use cases:** sentiment analysis · review classification · recommendation systems · perfume similarity from text · language detection benchmark · multilingual NLP training corpus · fragrance market research · author network analysis · trend detection by language

### `news.parquet` — 24,440 Editorial Articles (2008–2026)

Two decades of professional fragrance journalism. Every article includes title, author, full text (plain + HTML), category, related perfumes/brands/perfumers, publication date, and main image.

- **24,440 editorial articles** from 2008 to 2026 — complete public archive
- **30+ categories** — New Fragrances (34.9%), Fragrance Reviews (22.8%), Niche Perfumery (10.4%), Designer Brands, Interviews, History, Industry News
- **Bilingual storage** — `text` (plain) for NLP, `text_html` (markup preserved) for rich display
- **Linked entities** — `related_pids[]`, `related_brands[]`, `related_perfumers[]` as JSON arrays
- **119,662 PID references** — all but 174 (0.15%) resolve; those point to perfumes no longer in the catalogue
- **63.1% archived legacy, 36.9% modern** fully-dated articles
- **16 fields:** `nid`, `title`, `category`, `author`, `url`, `is_archived`, `date_unix`, `description`, `text`, `text_html`, `main_image`, `article_images`, `related_pids`, `related_brands`, `related_perfumers`, `comments_count`

**Use cases:** content recommendation · article search engine · perfume knowledge graph · trend analysis · author influence study · entity linking · timeline analysis · industry research · niche perfumery research

### `news_comments.parquet` — 263,798 Threaded Community Comments

Community discussions attached to editorial articles, with threading support for replies. Joinable with `news.parquet` via `nid`.

- **263,798 threaded comments** across **21,820 articles** (89.3% of news articles have ≥1 comment)
- **4.9% reply rate** — threaded conversations with reply detection
- **100% populated timestamps**
- **9 fields:** `nid`, `comment_id`, `is_reply`, `author`, `date`, `date_unix`, `text`, `avatar_url`, `gradient`

**Use cases:** community engagement analysis · threaded discussion mining · reply network construction · comment sentiment · author activity profiles

### Tier Availability

The parquet datasets ship with **all paid tiers except the $200 Core**:

| Tier | CSV Core | Parquet Datasets |
|------|----------|------------------|
| **$200 One-Time Core** | ✅ | ❌ |
| **$400 One-Time Full Database** | ✅ | ✅ |
| **Annual Subscription** | ✅ | ✅ (always latest) |
| **Lifetime Access** | ✅ | ✅ (always latest) |

See https://fragdb.net/#pricing for complete tier comparison.

### Quick Start — Parquet

```python
import pyarrow.parquet as pq
import pandas as pd
import json

reviews = pq.read_table('comments.parquet').to_pandas()
fragrances = pd.read_csv('fragrances.csv', sep='|')
reviews_with_meta = reviews.merge(fragrances, on='pid', how='left')

news = pq.read_table('news.parquet').to_pandas()
news['related_pids_list'] = news['related_pids'].apply(json.loads)

news_comments = pq.read_table('news_comments.parquet').to_pandas()
```

Full schema in [`SPEC.md`](SPEC.md).

### Use Cases

**CSV Core (all tiers):**
- **E-commerce** — Enrich product listings with detailed fragrance data, notes, accords
- **Mobile Apps** — Build fragrance collection managers, scent discovery apps, perfume catalog apps
- **Data Analysis** — Analyze fragrance industry trends by brand, country, perfumer, year
- **Recommendations** — Content-based or collaborative filtering systems using accord/note vectors
- **Multilingual UIs** — Localized perfume catalogs in 23 languages out of the box
- **Knowledge Graphs** — Brand → Perfumer → Fragrance → Notes → Accords graph construction
- **Market Research** — Country-of-origin analysis, parent company portfolios, perfumer productivity stats

**Parquet Datasets ($400+ tiers):**
- **NLP & Sentiment Analysis** — Train models on 4.6M multilingual fragrance reviews
- **Recommender Systems** — Hybrid models combining CSV structure with review text similarity
- **Language Models** — Domain-specific corpus for fragrance/perfumery LLM fine-tuning
- **Review Classification** — Identify positive/negative reviews, fake review detection
- **Trend Detection** — News article timeline analysis, emerging fragrance trends
- **Author Networks** — Identify influential reviewers, perfumery journalists, community leaders
- **Content-Based Discovery** — "Articles about this perfume" — JOIN news.related_pids with fragrances.pid
- **Community Analytics** — Reply networks, engagement metrics on editorial content
- **Cross-Language Studies** — Compare review sentiment across 23 languages for the same fragrance
- **Search Engines** — Full-text search across reviews, articles, and structured metadata
- **Knowledge Extraction** — Mine 24K editorial articles for perfume facts, launch dates, perfumer interviews

### Full Database

| | Sample | Full Database |
|---|--------|---------------|
| Fragrances | 10 | **139,501** |
| Brands | 10 | **8,272** |
| Perfumers | 10 | **3,116** |
| Notes | 10 | **2,596** |
| Accords | 10 | **92** |
| Translations | 34 | **34** |
| Languages | 23 | **23** |
| **Total Records** | ~84 | **153,611** |

## Quick Start

```python
import pandas as pd

fragrances = pd.read_csv('fragrances.csv', sep='|')
brands = pd.read_csv('brands.csv', sep='|')
notes = pd.read_csv('notes.csv', sep='|')
translations = pd.read_csv('translations.csv', sep='|')

# Join and translate
fragrances['brand_id'] = fragrances['brand'].str.split(';').str[1]
df = fragrances.merge(brands, left_on='brand_id', right_on='id', suffixes=('', '_brand'))
trans = translations.set_index('id')
df['gender_ru'] = df['gender'].map(lambda x: trans.loc[x, 'ru'] if x in trans.index else x)
print(df[['name', 'name_brand', 'country_ru', 'gender_ru']])
```

## File Format

- **Format**: CSV (pipe `|` delimited)
- **Encoding**: UTF-8
- **Quote Character**: `"` (double quote)

## Links

- **Full Database**: [fragdb.net](https://fragdb.net)
- **GitHub**: [github.com/FragDB/fragrance-database](https://github.com/FragDB/fragrance-database)

## License

This sample is released under the **CC BY-NC 4.0 License**. Free for non-commercial use with attribution.

## Citation

```bibtex
@dataset{fragdb2026,
  title={FragDB Fragrance Database},
  author={FragDB},
  year={2026},
  version={5.10},
  url={https://fragdb.net},
  note={Multilingual dataset with 6 files, 23 languages}
}
```
