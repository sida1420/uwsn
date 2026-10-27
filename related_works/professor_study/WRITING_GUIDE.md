# Learning from Nguyen Thi My Binh's papers: a writing guide for DACO

**First-pass guide. For the specific analysis requested after supplying the full ASC and ESWA papers, use [CLOSE_READING.md](CLOSE_READING.md).** It supersedes the abstract-only observations for those papers and the generic paragraph plan below. It also narrows the DACO contribution against the actual NodeACO implementation.

Studied 27 October 2026. This is a study of a selected publication sample, not a claim to have read her entire publication record. See [EVIDENCE.md](EVIDENCE.md) for titles, access levels, and verifiable locations. The Scholar profile identifies Nguyen Thi My Binh, Hanoi University of Industry. Do not confuse her with frequent coauthor Huynh Thi Thanh Binh.

## The main finding

My interpretation of the sample is that the organizing principle is a traceable argument:

**application requirement → limitation of an existing model or solution → precisely defined problem → method adapted to that problem → evidence matched to the contribution.**

For our paper, that means the reader should understand the clustering decision and its consequences before encountering DACO's ant colony machinery. The abstract compresses this argument, the introduction motivates it, and the formulation makes its terms measurable. This interpretation is consistent with the importance you report that she places on those three parts; it is not a statement about her private reviewing criteria.

## What the publication sample actually establishes

The 2021 MMFA and 2025 MIGA articles use six numbered main sections. The 2024 ExA-KSB article's publicly accessible introduction explicitly announces the same six-part sequence. The 2020 HPSO-MMEP article uses five, combining preliminaries, formulation, and method in Section 3. Thus, six is a well-supported template for DACO and your explicit requirement, rather than a verified rule for every paper she has written. Abstract, references, and declarations do not count toward these six sections. [MMFA](https://vjs.ac.vn/jcc/article/download/15858/384349), [MIGA](https://vjs.ac.vn/jcc/article/download/21945/2543256091), [ExA-KSB](https://www.sciencedirect.com/science/article/abs/pii/S1084804524001620), [HPSO-MMEP](https://www.mdpi.com/1424-8220/20/9/2586).

The clearest learning examples are:

| Paper | What to study in its writing | What we should do for DACO |
| --- | --- | --- |
| 2019 probabilistic MEP | An omitted environmental assumption motivates a changed exposure model. | Identify the particular density/depletion interaction we study; avoid a generic claim that existing routing is inefficient. |
| 2020 HM-MEP | The transformed problem's characteristics motivate its solvers. | Explain why evaluating a completed tree changes CH selection. |
| 2020 HPSO-MMEP | Mobility changes what an exposure measure must accumulate. | Define the quantity being optimized before introducing the search rule. |
| 2021 MMFA | Definitions and a lifetime budget precede the flow construction. | Define nodes, live set, tree, consumption, and lifetime metrics before DACO. |
| 2022 OE-MEP / FEA | Obstacle-free deployment is replaced by an explicitly named constrained setting. | State the assumptions we retain as clearly as the limitation we address. |
| 2024 ExA-KSB | Formulation, algorithm, proof, and evaluation are distinct contribution items. | Make each contribution independently checkable. |
| 2025 MIGA | Input/output/objective/constraints precede representation and operators. | Separate the networking problem from the ACO search implementation. |
| 2025 MSL | Real-valued and integer activation variants are distinguished. | Distinguish modeled rounds, FND, LND, and physical service lifetime. |
| 2026 STMF | The underwater model, metric, and transformed solution are linked. | Connect 3D geometry to the density construction and energy calculation. |
| 2026 EGA-MLTC | Lifetime is paired with a specified coverage/connectivity requirement. | State the reporting obligation accompanying any lifetime claim. |

These are different research problems; they are examples of exposition, not automatically appropriate DACO baselines. Sources and access limits are attached to each entry in the evidence file.

## The six sections to use

The existing LNCS template already has the appropriate main headings. Keep this sequence:

| Section | Question it must answer | DACO content |
| --- | --- | --- |
| 1. Introduction | What exact issue matters, and what does this paper add? | Uneven deployment and heterogeneous depletion under repeated CH selection; focused gap; scoped contributions. |
| 2. Related works | What is already known, and where does our particular question fit? | Energy-aware CH choice; density/unequal clustering; relay burden; feasibility; differing information/collector assumptions. |
| 3. Preliminaries and problem formulation | What is given, chosen, optimized, and constrained? | 3D deployment, acoustic cost model, CH/tree decision, live set, energy state, feasible candidates, evaluation endpoints. |
| 4. Proposed method | How does DACO construct and rank solutions? | Grid support, marginal density, selection probabilities, route evaluation, calibrated objective, live deposits, stopping and complexity. |
| 5. Experimental results | Which claims survive controlled evaluation? | Settings and budgets, primary comparisons, ablations, sensitivity, failures, runtime and limitations. |
| 6. Conclusion | What did the evidence establish, under which assumptions? | Bounded findings, observed trade-offs, and specific remaining work. |

The order is a reading order. A productive drafting order is **3 → 4 → 5 → 2 → 1 → abstract → 6**, followed by a consistency pass. That drafting order is my recommendation, not an inferred rule of hers.

## Abstract: a compressed argument

The sampled abstracts commonly identify a setting, specify a problem, name a method, identify its main mechanism, and describe evidence. The 2019 probabilistic-MEP and 2022 obstacle-evasion papers are particularly clear examples of a model limitation driving the problem statement. [2019 paper](https://www.sciencedirect.com/science/article/pii/S1568494618307117), [2022 author-repository record](https://opus.lib.uts.edu.au/handle/10453/166903).

For DACO, use approximately 150–250 words, as requested by the supplied LNCS template. This is a template constraint, not a measured average of her abstracts.

1. **Setting and difficulty, 1–2 sentences.** Underwater nodes have limited energy; uneven deployment can concentrate collection and forwarding work.
2. **Precise problem, 1 sentence.** Select CHs over repeated rounds while accounting for total route consumption and unequal fractional depletion.
3. **Method and reason, 2–3 sentences.** Name DACO, explain grid-derived density and completed-tree evaluation, then describe pheromone feedback in functional terms.
4. **Evidence, 1–2 sentences.** Report verified endpoints, comparison conditions, uncertainty, and a meaningful cost or limitation.
5. **Bounded implication, optional.** State which studied conditions support the conclusion.

Write the final results sentences last. The companion abstract fragment is a working draft with an explicit results placeholder. It contains no invented gains.

Avoid a list of ACO parameters in the abstract. A reader needs to understand why the mechanism addresses the problem. A broad sentence claiming superiority in energy, reliability, lifetime, scalability, and robustness would create five separate evidential obligations.

## Introduction: a paragraph plan for DACO

Use about six purposeful paragraphs, adjusted to the venue's page limit. This is our proposed implementation of the observed argument, not a universal paragraph count.

**Paragraph 1: application and required service.** Identify underwater monitoring and the repeated collection task. State the resource constraint that matters to this study. Keep the discussion close to the actual simulation model.

**Paragraph 2: explain the decision and the difficulty.** CHs collect data but can also relay traffic. Give a concrete example: two candidate trees can spend similar total joules while one repeatedly drains a weak relay. Their total-energy scores can be similar even when their depletion patterns differ.

**Paragraph 3: acknowledge what prior work already addresses.** Cite specific work on energy-aware CH selection, density, unequal clustering, and relay load. The current related-work collection already includes these ideas. We cannot claim that earlier methods universally ignore density, residual energy, or forwarding.

**Paragraph 4: state the question left for DACO.** Ask whether a grid-derived density representation combined with completed-tree fractional-depletion scoring and node pheromone improves the measured energy/lifetime/runtime trade-off under shared assumptions. This is a defensible study question, not a priority claim that no previous combination exists.

**Paragraph 5: explain the proposal at mechanism level.** Density guides construction; predicted transmission, reception, and aggregation costs rank constructed trees; pheromone carries search feedback. Explain what each part contributes to the preceding question.

**Paragraph 6: state contributions and organization.** Contributions should point to artifacts the reader can inspect: the scoped formulation, the fully specified DACO mechanism, and the controlled evaluation. Results-based contribution wording must wait for final evaluation.

The 2024 ExA-KSB introduction is a useful reference for explicitly separated contributions and an exact six-section roadmap. Its exactness claim is associated with theoretical analysis; it is not a phrase to transfer to a metaheuristic. [Publisher introduction](https://www.sciencedirect.com/science/article/abs/pii/S1084804524001620).

## Problem formulation: make the scientific contract explicit

The 2021 article develops definitions before its lifetime objective and resource constraint. The 2025 article explicitly presents inputs, output, objective, and constraints before its algorithm. Those are good structural models for Section 3. [MMFA, Section 3](https://vjs.ac.vn/jcc/article/download/15858/384349), [MIGA, Section 3](https://vjs.ac.vn/jcc/article/download/21945/2543256091).

For DACO, Section 3 should let a reader implement an independent evaluator without reading the ant search. Use this order:

1. Deployment, sink, node positions, live set, communication graph, and static-position assumption.
2. Packet generation, aggregation, and transmission/reception cost rules, with units.
3. Decision: the CH set, decoded member assignment, and resulting sink-rooted tree.
4. Hard structural requirements: allowed links, inclusion of all live nodes, and sink reachability within the implemented construction.
5. Objectives and endpoint definitions, with a clear distinction between a per-round score and multi-round lifetime.
6. Explicit model limits and stopping rules.

A useful notation contract is:

| Symbol | Meaning | Status |
| --- | --- | --- |
| `V_t` | Nodes with positive residual energy before round `t` | Implemented |
| `E_i(t)` | Residual energy of node `i` | Implemented |
| `H_t` | CH set selected for that round | Implemented |
| `T_t` | Tree constructed from a CH set by the shared routing procedure | Implemented |
| `c_i(T_t)` | Nominal modeled consumption in the candidate tree | Implemented |
| `C(T_t)` | Sum of node costs | Implemented |
| `D_i(t)` | Base grid-support density, held fixed while comparing candidates in that round | Implemented |
| `P_t(T_t)` | Powered fractional-depletion/density penalty | Implemented |
| `L_A(H)` | Number of modeled rounds completed by algorithm `A`, capped at horizon `H` | Evaluation definition; label the termination cause separately |

Do not define the scientific problem merely as minimizing whatever formula DACO happens to use. Explain the operational objective first, then identify the formula as the tractable ranking surrogate used by the proposed method.

### The current objective, in understandable terms

For a candidate tree, let

\[
C(T)=\sum_{i\in V_t}c_i(T),\qquad
P_t(T)=\frac{1}{|V_t|}\sum_{i\in V_t}
\frac{[c_i(T)/\max(E_i(t),10^{-12})]^p}{\max(D_i(t),\epsilon)}.
\]

The implementation ranks it by

\[
J_t(T)=C(T)+\lambda\,\overline C_t\,
\frac{P_t(T)}{\overline P_t}.
\]

Here `C` and `C̄` are in joules; the ratio `P/P̄` is dimensionless. The references are calibrated from feasible candidates and fixed during one round. Thus both terms in `J` have energy units. In code the configurable exponent satisfies `p ≥ 1`; the current default is 2.6.

Plain language: **a candidate pays for its total energy and for taking a large fraction of individual nodes' remaining energy, weighted by the structural density around those nodes.** At fixed residual energy and density, `p > 1` makes large individual drains increasingly expensive. A smaller `D_i` increases the penalty for the same fractional drain; this term is not simply a penalty on crowded nodes. Nor is it a proof of equal depletion, sparse-node protection, or maximum lifetime.

Density used during CH construction changes as CHs are selected. Density used in the penalty is the base structural density. These two quantities must receive different symbols. The grid support is a geometric approximation used for CH selection; it is not an independently validated sensing-coverage probability.

### Current implementation limits that affect the prose

These findings come from the local source, not from her papers:

- `src/simulate.py` subtracts nominal round costs and clamps residual energy to zero. It does not first require `c_i(T) ≤ E_i(t)` for every node. Consequently the existing simulator cannot substantiate a claim of energy-feasible completion of every transmitted packet in the terminal round.
- A round can stop because the bounded candidate search returns no route. This does not prove that no physically connecting tree exists.
- CH count is prescribed by a configurable proportion, not freely optimized over all possible counts.
- Routing is a shared decoding procedure; DACO searches CH sets. Do not claim joint global optimization over every possible routing tree.
- Packet output at a CH is fixed at two packets in the current evaluator. Ordinary relays forward received packets plus their own. Write these actual rules or revise and validate the model before claiming a different aggregation rule.
- Simulated positions are fixed during a run. Updating density after node death is not a mobility model.
- Control-message exchange, collisions, packet errors, and propagation delay are not modeled by this energy evaluator. CPU time is measured separately; search evaluation does not consume simulated node battery.

These limits do not require changing the algorithm during a writing task. They require accurate model statements and explicit decisions before stronger publication claims.

## How to make the method and evidence fit the story

The method should follow the dependency order of the construction:

1. Define geometric grid weights and base density.
2. Explain marginal density as selected CHs reduce remaining support.
3. Give the CH selection probability and the candidate representation.
4. Decode memberships and routes, including outlier handling and member detachment.
5. Evaluate a completed tree, define `J`, and reject failed candidates.
6. Explain calibration, within-round live pheromone updates, elite deposit, and cross-round reference smoothing.
7. State the actual search budget and analyze all material computational components.

Name each mechanism only after giving the reason it exists. A flowchart should show this sequence; it should not introduce a seventh main section.

A sensible experimental question set is:

| Question | Necessary evidence |
| --- | --- |
| Does the full method help on the studied deployments? | Matched maps, separate algorithm seeds, a common routing/energy model, uncertainty over independent instances. |
| Is the benefit due to density? | A density ablation with explicit changes to both sampling and/or scoring; do not remove two components and attribute the effect to one. |
| Does fractional depletion matter beyond energy? | An energy-only ranking ablation under the same candidate budget. |
| Do live deposits matter? | Frozen-within-round versus live updates with other rules fixed. |
| What does the improvement cost? | Runtime, evaluation counts, calibration work, and failure frequencies. |
| Does tuning generalize? | Disjoint tuning and test seeds/maps with frozen parameters for final reporting. |
| What does a long run mean? | FND, observed LND where applicable, modeled completed rounds, and termination/horizon flags. |
| Is energy comparable? | Energy over a common completed-work window, not just each algorithm's different stopping time. |

These are recommendations for our evaluation, not claims that every sampled paper performed every check. The MIGA paper is an especially useful example of explicitly acknowledging the runtime/quality trade-off and remaining limitations. We should preserve that willingness to state costs, while checking every table and formula independently. [MIGA, Sections 5–6](https://vjs.ac.vn/jcc/article/download/21945/2543256091).

## Writing rules to adopt

- Define an acronym on first use and keep a single name for each problem, algorithm, and metric.
- Explain each equation's purpose before it and its symbols and implications immediately after it.
- Distinguish a definition, modeling assumption, analytical result, and empirical observation.
- Make each introduction contribution correspond to a method component, a proof if any, or an experimental result.
- Group related work by the problem dimension it addresses, then discuss the closest comparable methods precisely.
- State which limitation a mechanism addresses; avoid lengthy textbook introductions to ACO or generic claims about optimization.
- Discuss regimes where the method is expensive, ineffective, or outside scope.
- Use restrained claims. A finite search is not an exact solver, an empirical plateau is not a convergence proof, and polynomial algorithm runtime does not imply polynomial exact solution of a general hard problem.
- Learn the structure and argumentative roles. Use original wording and independently checked equations.

## Immediate DACO writing priorities

First, freeze what counts as a completed round and the primary endpoint. Second, document the energy and aggregation contract. Third, align Section 3 with the actual candidate decoder and scoring rule. Then refine the introduction around that contract and the literature gap. Finalize quantitative abstract and conclusion claims only after the final experiments.

Working LaTeX fragments are in [output/daco_writing](../../output/daco_writing/README.md). They cover the abstract, introduction, and formulation; method and results still require complete drafting and final evidence. The existing Overleaf main file has not been overwritten by this study.
