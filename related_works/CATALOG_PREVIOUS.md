# Related works for DACO

Checked on 2026-10-26. Existing PDFs use `YYYY_Title.pdf`, where YYYY is the **first online publication year** when that date is printed in the paper. Existing descriptive filename text is preserved; the opaque filename of the QLAR PDF was replaced with its verified article title. Dates, DOI identifiers, original filenames, and SHA-256 checksums are recorded in [publication_dates.json](publication_dates.json). All nine PDF contents were verified unchanged. Two PDFs appeared during this review and were included in the final check; the FCRA paper already had its verified 2025 year prefix.

## Existing collection

| Filename prefix | Paper | DOI | Date basis |
| --- | --- | --- | --- |
| 2019 | Cluster-based routing protocols in wireless sensor networks: A survey based on methodology | [10.1016/j.jnca.2019.04.021](https://doi.org/10.1016/j.jnca.2019.04.021) | First online 2019-05-11, printed in the PDF |
| 2020 | A Clustering Routing Algorithm Based on Improved Ant Colony Optimization Algorithms for Underwater Wireless Sensor Networks | [10.3390/a13100250](https://doi.org/10.3390/a13100250) | Published 2020-10-01, printed in the PDF |
| 2020 | Two-Tier PSO Based Data Routing Employing Bayesian Compressive Sensing in Underwater Sensor Networks | [10.3390/s20205961](https://doi.org/10.3390/s20205961) | Published 2020-10-21, printed in the PDF |
| 2021 | A comprehensive survey on LEACH-based clustering routing protocols in Wireless Sensor Networks | [10.1016/j.adhoc.2020.102409](https://doi.org/10.1016/j.adhoc.2020.102409) | First online 2021-01-16, printed in the PDF |
| 2021 | A survey on energy efficiency in underwater wireless communications | [10.1016/j.jnca.2021.103295](https://doi.org/10.1016/j.jnca.2021.103295) | First online 2021-12-08; February 2022 journal issue. Date read visually from the scanned first page |
| 2022 | An Unequal Clustering Method Based on Particle Swarm Optimization in Underwater Acoustic Sensor Networks | [10.1109/JIOT.2022.3195223](https://doi.org/10.1109/JIOT.2022.3195223) | First online 2022-08-01; December 2022 issue |
| 2025 | An Efficient Clustering Algorithm for Enhancing the Lifetime and Energy Efficiency of Wireless Sensor Networks | [10.32604/cmc.2025.065561](https://doi.org/10.32604/cmc.2025.065561) | Published 2025-07-30, printed in the PDF |
| 2025 | A Q-Learning-Based Link-Aware Routing Protocol for Underwater Wireless Sensor Networks | [10.3390/jmse13122374](https://doi.org/10.3390/jmse13122374) | Published 2025-12-14, printed in the PDF |
| 2025 | Improving routing in wireless sensor networks technology on data aggregation using fused cluster routing algorithm | [10.1007/s43621-025-01300-y](https://doi.org/10.1007/s43621-025-01300-y) | Already year-prefixed; 2025 publication year verified from article first page |

## How the recommendations were selected

The current implementation in [d_aco.py](../src/algorithms/d_aco.py) and [the clustering implementation](../src/algorithms/clustering/d_aco/d_aco.py) combines ACO cluster-head selection, a 3D grid density measure, evaluated energy consumption, a powered relative-load/density penalty, live pheromone updates, and multi-hop routing. Relevance below is my assessment against those mechanisms, rather than a claim made by the cited authors.

All ten papers below are additional to the nine existing PDFs and have journal publication years after 2016. Seven concern underwater networks; three supply related methods from terrestrial/general WSNs. Recommendations are ordered approximately by usefulness for DACO's related-work discussion and baseline design.

The year column is the **journal issue/bibliographic year**, not an arXiv upload year. In particular, the soft-k-means paper is a 2021 journal article even though an arXiv copy was uploaded in 2024. The EEUMC paper is assigned to the January 2025 issue and has a 2024 DOI. Do not infer an exact publication date from the DOI string.

The quartile filter uses **SCImago/SJR 2024 journal rankings**, with a qualifying category where specified below. These are journal-level ratings, not article scores, JCR ratings, or a claim about the journal's rating in the article's publication year. Using one fixed ranking year makes the filter reproducible.

## Ten recommended papers

| # | Year | Paper and DOI | Journal / SJR 2024 | Relation to DACO |
| --- | --- | --- | --- | --- |
| 1 | 2020 | Yu et al., [An Energy Optimization Clustering Scheme for Multi-Hop Underwater Acoustic Cooperative Sensor Networks](https://doi.org/10.1109/ACCESS.2020.2993544) (EOCA) | IEEE Access / Q1 | Underwater clustering using neighbor count, residual energy, node movement, and distance to sink. A close comparison for density-aware selection; cooperative communication and adaptive transmission range need separate treatment. |
| 2 | 2018 | Hou et al., [Energy-Balanced Unequal Layering Clustering in Underwater Acoustic Sensor Networks](https://doi.org/10.1109/ACCESS.2018.2854276) (EULC) | IEEE Access / Q1 | Addresses energy imbalance and the hot-spot problem through depth layers and unequal clusters. Compare this structural allocation of load with DACO's evaluated load/density penalty. |
| 3 | 2019 | Li et al., [Energy-Efficient Load Balancing Ant Based Routing Algorithm for Wireless Sensor Networks](https://doi.org/10.1109/ACCESS.2019.2934889) (EBAR) | IEEE Access / Q1 | Direct ACO/load-balancing connection: route discovery, heuristic updates, and pheromone reinforcement. Terrestrial WSN routing, so transfer its search ideas while retaining an acoustic energy model. |
| 4 | 2020 | Zhang et al., [Routing Clustering Protocol for 3D Wireless Sensor Networks Based on Fragile Collection Ant Colony Algorithm](https://doi.org/10.1109/ACCESS.2020.2982691) | IEEE Access / Q1 | A 3D clustering and ACO routing comparison addressing load balance, relay roles, and CH replacement. General 3D WSNs; being 3D does not establish an underwater acoustic model. |
| 5 | 2021 | Zhu et al., [Improved Soft-k-Means Clustering Algorithm for Balancing Energy Consumption in Wireless Sensor Networks](https://doi.org/10.1109/JIOT.2020.3031272) (IS-k-means) | IEEE Internet of Things Journal / Q1 | Especially relevant to the density argument: density peaks/KDE initialize clusters, boundary nodes are reassigned, and multiple CHs distribute load. Terrestrial WSNs; distinguish these density measures from DACO's grid coverage measure. |
| 6 | 2021 | Omeke et al., [DEKCS: A Dynamic Clustering Protocol to Prolong Underwater Sensor Networks](https://doi.org/10.1109/JSEN.2021.3054943) | IEEE Sensors Journal / Q1 | Underwater distance- and energy-constrained k-means with dynamic energy thresholds and cluster-count selection. A useful baseline against which to justify ACO search cost and the chosen CH count. |
| 7 | 2021 | Nguyen et al., [Energy-Efficient Clustering Multi-Hop Routing Protocol in a UWSN](https://doi.org/10.3390/s21020627) (EECMR) | Sensors / Q1 | A simpler underwater baseline: depth layers, residual-energy CH selection, aggregation, and multi-hop forwarding. Helps test whether DACO improves over a less expensive selection rule. |
| 8 | 2024 | Mei et al., [Node Load and Location-Based Clustering Protocol for Underwater Acoustic Sensor Networks](https://doi.org/10.3390/jmse12060982) (LLCP) | Journal of Marine Science and Engineering / Q2 | Explicitly uses node load, location, and node degree to constrain membership and avoid congestion. Useful when explaining why density alone does not measure forwarding load. Its target is congestion/complexity, so do not treat it as an equivalent lifetime objective. |
| 9 | 2025 | Kumar et al., [Energy-efficient unequal multi-level clustering for underwater wireless sensor networks](https://doi.org/10.1016/j.aej.2024.10.026) (EEUMC) | Alexandria Engineering Journal / Q1 | Recent underwater unequal clustering combines residual-energy/sink-distance CH selection with hierarchical routing and aggregation. Compare assumptions and mechanisms before treating it as an executable baseline. |
| 10 | 2023 | Kaveripakam and Chinthaginjala, [Clustering-based dragonfly optimization algorithm for underwater wireless sensor networks](https://doi.org/10.1016/j.aej.2023.09.047) (CDFO-UWSN) | Alexandria Engineering Journal / Q1 | An alternative underwater metaheuristic with experiments varying node density, grid size, and transmission range. Useful for evaluating whether DACO's density mechanism transfers across deployments. |

The ten journal references are also available in [recommendations_daco.bib](recommendations_daco.bib). Recommendations include DOI links; no additional PDFs were downloaded into this collection.

## Reference tracing and primary sources

Four selections came directly from the references of the existing Xiao and Huang ACOCR paper (2020): EOCA is reference 11, EULC is reference 16, EBAR is reference 46, and the 3D fragile-collection ACO paper is reference 51. The remaining six came from targeted searches for underwater energy-aware clustering, density-aware energy balancing, and load-aware membership selection.

- [ACOCR publisher article and references](https://www.mdpi.com/1999-4893/13/10/250).
- [EOCA author's institutional publication record](https://coeadmin.xmu.edu.cn/teachershow_old.aspx?id=438); its bibliographic record and DOI were also checked against publisher-deposited Crossref metadata.
- [EULC discussion in Hou and collaborators' later original paper](https://faculty.cqupt.edu.cn/system/resource/storage/download.jsp?mark=QTM0RDZBMkE0QTJERDFCOEZEMDM2NDZBNUY4NUE1RTgvRTM0QzQwQTEvMTNDNDYz); EULC's title, authors, year, volume, and pages were checked against publisher-deposited Crossref metadata. The original publisher page did not load during this check.
- [EBAR institutional author record and abstract](https://researchprofiles.tudublin.ie/en/publications/energy-efficient-load-balancing-ant-based-routing-algorithm-for-w/) and [coauthor publication list](https://thomasweise.github.io/research/publications).
- [3D fragile-collection ACO author-uploaded article and abstract](https://www.researchgate.net/publication/340107803_Routing_Clustering_Protocol_for_3D_Wireless_Sensor_Networks_Based_on_Fragile_Collection_Ant_Colony_Algorithm); journal metadata checked against Crossref.
- [IS-k-means author's manuscript](https://arxiv.org/abs/2403.15700) and [IEEE journal contents confirming the 2021 issue](https://www.comsoc.org/system/files/2021-03/Publications_Contents_Digest_2021_Mar.pdf).
- [DEKCS author repository: abstract, manuscript, and publication dates](https://eprints.gla.ac.uk/227979/).
- [EECMR original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC7831061/).
- [LLCP original article](https://www.mdpi.com/2077-1312/12/6/982).
- [EEUMC publisher article](https://www.sciencedirect.com/science/article/pii/S1110016824011815).
- [CDFO-UWSN publisher article](https://www.sciencedirect.com/science/article/pii/S1110016823008359).

## Quartile evidence

| Journal | Qualifying SJR 2024 rating | Evidence |
| --- | --- | --- |
| IEEE Access | Q1, journal's displayed qualifying quartile | [SCImago 2024 ranking table](https://www.scimagojr.com/journalrank.php?country=&min=3&min_type=cd&ord=desc&order=titem&year=2024), SJR 0.849 |
| IEEE Internet of Things Journal | Q1, journal's displayed qualifying quartile | [SCImago 2024 ranking table](https://www.scimagojr.com/journalrank.php?country=Northern+America&min=30&min_type=cd&ord=desc&order=cpd&page=9&total_size=6608), SJR 2.483 |
| IEEE Sensors Journal | Q1, journal's displayed qualifying quartile | [SCImago 2024 ranking table](https://www.scimagojr.com/journalrank.php?country=Northern+America&ord=desc&order=tc&page=2&total_size=5171&wos=true), SJR 1.039 |
| Sensors | Q1, journal's displayed qualifying quartile | [SCImago 2024 ranking table](https://www.scimagojr.com/journalrank.php?country=&min=3&min_type=cd&ord=desc&order=titem&year=2024), SJR 0.764 |
| Journal of Marine Science and Engineering | Q2 in Civil and Structural Engineering | [SCImago 2024 category table](https://www.scimagojr.com/journalrank.php?category=2205&openaccess=true&ord=desc&order=titem&page=1&total_size=78), SJR 0.579 |
| Alexandria Engineering Journal | Q1 in Engineering (miscellaneous) | [SCImago profile](https://www.scimagojr.com/journalsearch.php?q=13907&tip=sid); 2024 SJR 1.037 / Q1 checked through the [annual metrics mirror](https://researchcloud.net/journal/1110-0168) because the primary profile returned HTTP 403 |

The tables without an explicit year parameter displayed 2024 data when checked; use the stated ranking year if their default later changes. Quartiles differ by category and ranking system. For example, IEEE Access can be SJR Q1 while being JCR Q2; the labels above consistently refer to SJR.

## Implications for the proposal

Read EOCA, EULC, EBAR, and IS-k-means first. Together they cover neighborhood/density information, underwater energy imbalance, ACO load balancing, and density-based energy balancing. DEKCS and EECMR are useful simpler underwater comparison candidates; LLCP sharpens the distinction between density, membership count, congestion, and forwarding load.

For DACO, the promising claim to investigate is the specific combination of **3D grid coverage density, evaluated relative forwarding depletion, and live node-pheromone reinforcement**. These sources already use density/neighborhood information, energy balancing, clustering, and metaheuristics in several combinations. This shortlist does not establish that the proposed combination is novel.

For comparable experiments, retain a common topology, acoustic energy model, routing feasibility rules, seeds, and search/evaluation budgets. Report first-node death, completed service rounds, equal-window energy consumption, and computation time separately. A lifetime number from a paper with different deployment, routing, aggregation, or stopping assumptions cannot be compared directly with DACO's simulator result.
