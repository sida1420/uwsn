# Evidence register for the professor writing study

**Access update:** the user subsequently supplied the full ASC and ESWA PDFs. Their full-text and visual close reading is documented in [CLOSE_READING.md](CLOSE_READING.md). P1/P5 access limitations below describe the initial web-only pass and no longer describe our current access to those two papers.

Checked 27 October 2026. Identity: [Nguyen Thi My Binh's supplied Scholar profile](https://scholar.google.com/citations?user=-TrfhrMAAAAJ&hl=en). A public HTML copy was retrieved to `tmp/professor_profile.html`. The profile is a discovery source; publication text below supports the analysis. The profile also lists Huynh Thi Thanh Binh as a coauthor: these are different people.

This is a purposive sample of ten sensor-network papers, spanning 2019–2026 and including recent underwater work. Detailed structure was read in accessible 2020, 2021, and 2025 article text. The 2024 article additionally exposes its introduction and roadmap. Six other papers were assessed at abstract/highlight level. We do not infer hidden section headings, equations, or experimental protocols from abstracts. This is not a systematic census, an independent replication, or a verified statement about author-specific editing responsibility in coauthored work.

## Sources and short observations

| ID | Paper / year | Primary source and access actually used | What it supports |
| --- | --- | --- | --- |
| P1 | Efficient approximation approaches to minimal exposure path problem in probabilistic coverage model for wireless sensor networks / 2019 | [Elsevier abstract and highlights](https://www.sciencedirect.com/science/article/pii/S1568494618307117), DOI 10.1016/j.asoc.2018.12.022; full article not audited | Environmental noise motivates a probabilistic exposure definition, formulation, and two approximation approaches. |
| P2 | Efficient meta-heuristic approaches in solving minimal exposure path problem for heterogeneous wireless multimedia sensor networks in internet of things / 2020 | [Springer abstract](https://link.springer.com/article/10.1007/s10489-019-01628-9); subscription preview | Named HM-MEP problem, transformation to a numerical optimization task, and tailored HEA/GPSO solvers. |
| P3 | An Elite Hybrid Particle Swarm Optimization for Solving Minimal Exposure Path Problem in Mobile Wireless Sensor Networks / 2020 | [MDPI article text](https://www.mdpi.com/1424-8220/20/9/2586), DOI 10.3390/s20092586; indexed article text and PDF text | Five main sections; Section 3 combines models, formulation, and algorithm. Time-dependent exposure motivates the mobile-network treatment. |
| P4 | Maximizing lifetime of heterogeneous wireless turnable camera sensor networks ensuring strong barrier coverage / 2021 | [Journal PDF, 14 pages](https://vjs.ac.vn/jcc/article/download/15858/384349), DOI 10.15625/1813-9663/37/1/15858 | Six sections; definitions before formulation; lifetime as sustained barrier service; staged transformation and shared physical-sensor budgets. |
| P5 | A family system based evolutionary algorithm for obstacle-evasion minimal exposure path problem in Internet of Things / 2022 | [UTS author-repository abstract](https://opus.lib.uts.edu.au/handle/10453/166903), DOI 10.1016/j.eswa.2022.116943; explicitly closed access | Obstacle-free assumptions motivate OE-MEP; characteristics of the new setting motivate FEA. Full-text structure not verified. The repository's displayed PDF filename is inconsistent with the title; it was not treated as the paper. |
| P6 | An efficient exact method with polynomial time-complexity to achieve k-strong barrier coverage in heterogeneous wireless multimedia sensor networks / 2024 | [Elsevier abstract, highlights, and introduction](https://www.sciencedirect.com/science/article/abs/pii/S1084804524001620), DOI 10.1016/j.jnca.2024.103985 | Minimum supplementary mobile-sensor objective; explicit formulation/algorithm/proof/evaluation contributions; introduction announces six sections. Full proofs were not audited. |
| P7 | Solving the maximal exposure path problem in heterogeneous directional wireless sensor networks using an improved genetic algorithm / 2025 | [Journal PDF, 18 pages](https://vjs.ac.vn/jcc/article/download/21945/2543256091), DOI 10.15625/1813-9663/21945 | Six sections; input/output/objective/constraints in Section 3; representation and operators in Section 4; runtime trade-off and limitations in Sections 5–6. |
| P8 | An efficient discretization and transformation scheme for maximizing secure lifetime problem in heterogeneous wireless rotatable camera sensor networks with barrier coverage / 2025 | [Springer abstract](https://link.springer.com/article/10.1007/s10586-025-05165-8); subscription preview | Real and integral secure-lifetime variants; discretization, flow and LP transformations; upper-bound claim. Full construction and section count not verified. |
| P9 | Extending network lifespan and securing effective barrier coverage in 3D underwater wireless sensor networks / 2026 | [Springer abstract](https://link.springer.com/article/10.1007/s10586-026-06113-w); published 3 June 2026; subscription preview | Underwater probabilistic coverage, a 3D stealth metric, and STMF flow/assignment strategy. Full equations and section count not verified. |
| P10 | Maximizing Lifetime and Target Coverage in Dynamic Underwater Wireless Sensor Networks Using an Enhanced Genetic Algorithm / 2026 | [Springer abstract](https://link.springer.com/article/10.1007/s10922-026-10080-3); published 23 May 2026; subscription preview | MLTC-UWSN names lifetime, target coverage, and connectivity together; EGA-MLTC uses key-time scheduling. Full equations and final article structure not verified. |

## Direct structural checks

P3's roadmap on PDF page 3 confirms five sections, combining formulation and algorithm in Section 3. The mobile exposure discussion motivates its time-based metric.

P4: roadmap on printed page 58; definitions on pages 60–61; formulation on page 62; method on pages 62–65; experiments from page 65; conclusion on page 68. Its normalization handles shared sensor budgets across orientations.

P6's exposed introduction gives four contribution items and a six-section roadmap. The full proofs were inaccessible; their correctness is not independently assessed here.

P7: roadmap on printed page 165; preliminaries from page 166; formulation on page 168; method from page 168; results from page 173; conclusion from page 178. Table 1 reports 30 runs. Sections 5–6 discuss computational costs and remaining limitations.

## Scope of the inference

The repeatable findings are formulation before mechanism, explicit contributions, named problems, and evidence connected to the proposed mechanism. Three directly inspected roadmaps use six main sections; one uses five. No claim is made about all publications, exact average abstract length, how she personally edits every coauthored article, or which words she would approve in a new manuscript.

## Access and preservation

The web reader exposed the journal PDF texts above. Direct downloads from the publisher and preprint URLs returned HTTP 403 in this environment; the attempted download manifest is in `sources/download_manifest.json`. No successful local source PDF download is claimed. PDF screenshots were unavailable through the web tool, so equation-layout fidelity has not been visually verified. Locators above refer to readable article text and printed PDF page labels.

## Local implementation sources used for the DACO recommendations

- `src/algorithms/d_aco.py`: calibration, full-tree checks, frozen reference scales, candidate ranking, live deposits, selected-plan return.
- `src/algorithms/clustering/d_aco/d_aco.py`: grid support, base/marginal density, CH sampling, evaporation and deposits.
- `src/algorithms/clustering/d_aco/fitness.py`: powered fractional depletion, density denominator, energy-unit objective.
- `src/algorithms/clustering/d_aco/parameters.py`: configurable controls and validation.
- `src/algorithms/clustering/clustering.py`: nearest-CH membership and outliers.
- `src/algorithms/routing/routing.py`: common routing and detachment of blocked members.
- `src/evaluate.py`: acoustic path-loss calculation and packet/aggregation bookkeeping.
- `src/simulate.py`: energy clamping and stopping behavior.
- `optimizer/metrics.py`: existing completed-round, censoring/termination, and common-window evaluation conventions.

These implementation observations support the companion draft. They do not establish theoretical novelty or experimental superiority.
