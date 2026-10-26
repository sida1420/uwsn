# DACO related works

Updated 26 October 2026 after critical reading. Start with the [complete paper summaries and screening decisions](PAPER_REVIEW.md). They cover all nine local papers, all ten previous recommendations, five replacements, and two other candidates that were not selected.

Each review explains the problem, method in plain language, results, limitations, and relation to DACO. Selected equations are explained. Author-stated limitations are separated from the reviewer's assessment. Five earlier recommendations have explicitly limited summaries because their full original methods/results could not be audited; they are replaced in the active list.

## Revised 10 additional papers

All ten are additional to the original nine PDFs and were published after 2016. Quartiles are journal-level SJR ratings, not JCR or article-quality scores. Ratings use 2024 except IEBR, explicitly labeled 2025.

| # | Issue year | Paper | Journal / SJR quartile | Limitation to understand |
| --- | --- | --- | --- | --- |
| 1 | 2020 | [EOCA: An Energy Optimization Clustering Scheme for Multi-Hop Underwater Acoustic Cooperative Sensor Networks](https://doi.org/10.1109/ACCESS.2020.2993544) | IEEE Access / Q1 (2024) | AUV assistance, shallow scenario, collection trajectory outside scope |
| 2 | 2021 | [Improved Soft-k-Means Clustering Algorithm for Balancing Energy Consumption in Wireless Sensor Networks](https://doi.org/10.1109/JIOT.2020.3031272) | IEEE Internet of Things Journal / Q1 (2024) | Terrestrial single-hop model; LND uses an 85%-dead proxy |
| 3 | 2021 | [DEKCS: A Dynamic Clustering Protocol to Prolong Underwater Sensor Networks](https://doi.org/10.1109/JSEN.2021.3054943) | IEEE Sensors Journal / Q1 (2024) | Underwater RF/AUV experiment; dense-region preference can harm outliers |
| 4 | 2021 | [Energy-Efficient Clustering Multi-Hop Routing Protocol in a UWSN](https://doi.org/10.3390/s21020627) | Sensors / Q1 (2024) | Re-clustering overhead and range-dependent results |
| 5 | 2024 | [Node Load and Location-Based Clustering Protocol for Underwater Acoustic Sensor Networks](https://doi.org/10.3390/jmse12060982) | Journal of Marine Science and Engineering / Q2 (2024) | Capacity/complexity objective; not a lifetime evaluation |
| 6 | 2019 | [A PSO-Based Uneven Dynamic Clustering Multi-Hop Routing Protocol for Wireless Sensor Networks](https://doi.org/10.3390/s19081835) | Sensors / Q1 (2024) | Terrestrial model, ideal MAC, control-message energy excluded |
| 7 | 2021 | [Game-Theory-Based Clustering Scheme for Energy Balancing in Underwater Acoustic Sensor Networks](https://doi.org/10.1109/JIOT.2021.3055857) | IEEE Internet of Things Journal / Q1 (2024) | Static reliable links; percentage wording needs correction |
| 8 | 2019 | [Improved energy-balanced algorithm for underwater wireless sensor network based on depth threshold and energy level partition](https://doi.org/10.1186/s13638-019-1533-y) | EURASIP Journal on Wireless Communications and Networking / Q2 (2025; mirror) | Routing restrictions and sector/depth assumptions; not CH selection |
| 9 | 2019 | [An Energy-Efficient Redundant Transmission Control Clustering Approach for Underwater Acoustic Networks](https://doi.org/10.3390/s19194241) | Sensors / Q1 (2024) | Aggressive reduction can lose information; mobile collector required |
| 10 | 2021 | [Underwater Wireless Sensor Networks: An Energy-Efficient Clustering Routing Protocol Based on Data Fusion and Genetic Algorithms](https://doi.org/10.3390/app11010312) | Applied Sciences / Q2 (2024) | Computation/fusion assumptions; simulation-only evaluation |

References: [revised BibTeX](recommendations_daco.bib). Retrieved public manuscripts: [sources](sources/). EECRP appeared online in December 2020 for a 2021 issue; the soft-k-means arXiv copy was uploaded in 2024, but its journal article is 2021.

## Original collection and decisions

The original PDFs remain unchanged, with year-only prefixes. The original filename/date/hash record is in [publication_dates.json](publication_dates.json).

- Background: Fanian survey (2019), LEACH survey (2021), underwater energy survey (online 2021 / issue 2022).
- Retained algorithms: ACOCR (2020), Two-Tier PSO (2020), UCPSO (2022), QLAR (2025).
- Excluded from the empirical set: FCRA (2025), AC-ACO (2025), with specific evidence in the review. Simulator code and source PDFs were not changed.
- Earlier recommendations held for incomplete original-text audit: EULC, EBAR, fragile-collection ACO, EEUMC, CDFO-UWSN. An access limitation is not a finding of scientific invalidity.

The [previous catalog](CATALOG_PREVIOUS.md) and [previous references](recommendations_daco_previous.bib) are preserved for traceability and superseded by this list.

## Ranking sources

- IEEE Access, Sensors, Applied Sciences: [SCImago 2024 table](https://www.scimagojr.com/journalrank.php?country=&min=3&min_type=cd&ord=desc&order=titem&year=2024), respectively 0.849/Q1, 0.764/Q1, and 0.521/Q2.
- IEEE Internet of Things Journal: [SCImago table displaying 2024 data](https://www.scimagojr.com/journalrank.php?country=Northern+America&min=30&min_type=cd&ord=desc&order=cpd&page=9&total_size=6608), 2.483/Q1.
- IEEE Sensors Journal: [SCImago table displaying 2024 data](https://www.scimagojr.com/journalrank.php?country=Northern+America&ord=desc&order=tc&page=2&total_size=5171&wos=true), 1.039/Q1.
- JMSE: [SCImago Civil and Structural Engineering table displaying 2024 data](https://www.scimagojr.com/journalrank.php?category=2205&openaccess=true&ord=desc&order=titem&page=1&total_size=78), 0.579/Q2 in that category.
- EURASIP Journal on Wireless Communications and Networking: [SJR 2025 category mirror](https://scienceaijournal.com/journals/eurasip-journal-on-wireless-communications-and-networking-1687-1472), Q2 in Signal Processing, Computer Networks and Communications, and Computer Science Applications. The primary profile was inaccessible; this is not represented as direct 2024 verification.

Tables without an explicit year parameter can later change defaults. Quartiles are screening conditions, not guarantees that every experiment is sound.
