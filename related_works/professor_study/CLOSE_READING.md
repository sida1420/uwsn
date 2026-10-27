# Specific writing patterns in the two supplied papers

27 October 2026. This replaces the generic first-pass interpretation for these two papers. All page references below are **PDF page numbers**, starting at 1. Observed practice is separated from proposed changes to DACO.

Sources read in full body text, with visual checks of the abstract, formulation, representation diagrams, and key result tables:

- **ASC:** [Efficient approximation approaches to minimal exposure path problem in probabilistic coverage model for wireless sensor networks](<C:/Users/hgtfh/OneDrive/Documents/HAUI/3 Applied soft computing.pdf>), Applied Soft Computing 76 (2019), 726–743; 18 PDF pages. First online December 2018.
- **ESWA:** [A family system based evolutionary algorithm for obstacle-evasion minimal exposure path problem in Internet of Things](<C:/Users/hgtfh/OneDrive/Documents/HAUI/[9]. Expert system and Application .pdf>), Expert Systems With Applications 200 (2022), 116943; 14 PDF pages.

The patterns belong to these coauthored papers. They do not establish which author required each individual editorial choice. Annotations in the supplied PDFs were treated as annotations, not instructions.

## 1. The abstracts share an unusually close sentence sequence

ASC has 10 sentences and approximately 249 words; ESWA has 11 sentences and approximately 243 words. Counts use dehyphenated extracted text and whitespace-separated words. More informative than the lengths is the matching placement of the argument:

| Sentence | ASC abstract, p. 1 | ESWA abstract, p. 1 |
| --- | --- | --- |
| 1 | Exposure is a way to evaluate coverage. | Barrier coverage is useful for security applications. |
| 2 | MEP is the particular problem of interest. | MEP is the particular subproblem of barrier coverage. |
| 3 | Defines what a minimal-exposure path means. | Defines what a minimal-exposure path means. |
| 4 | Explains who uses the result and why: network designers identify weak coverage. | Explains the same use: network designers identify weak coverage. |
| 5 | Identifies an inadequate assumption: environmental disturbances are omitted. | Identifies an inadequate assumption: obstacle-free deployment. |
| 6 | Introduces the changed problem and metric: PM-based-MEP with noise. | Introduces the changed problem: OE-MEP. |
| 7 | Describes the transformed optimization problem. | Adds obstacle generation as a modeling/data contribution. |
| 8 | Introduces the two solvers as a response to the problem's characteristics. | Describes the difficulty of the changed problem. |
| 9 | Differentiates the grid and GA mechanisms. | Introduces FEA and its Family System mechanism. |
| 10 | Gives a qualitative experimental conclusion. | Adds the simulation environment. |
| 11 | — | Gives a qualitative experimental conclusion. |

**Specific observation:** both spend their first four sentences making the problem interpretable and useful. Both place the gap in sentence 5 and the changed problem in sentence 6. The solver appears later. Neither abstract contains improvement percentages, a benchmark table in prose, or a parameter list.

**Change to DACO:** introduce the collection decision and what fractional depletion means before naming the optimizer. The sentence explaining the gap must distinguish two trees with equal total energy but unequal node-level burden. Do not imitate the papers by inventing a new physical network model or claiming the first density-aware method. Our current contribution is a decision criterion and its integration into CH search. A numerical abstract result is useful when final evidence exists, but it is not a recurring requirement established by these two abstracts.

## 2. Both introductions use four main narrative paragraphs before contributions

The paragraph structure, checked against the two-column layouts, is remarkably similar. Paragraphs can cross a column or page boundary.

| Block | ASC, pp. 1–2 | ESWA, pp. 1–2 |
| --- | --- | --- |
| Paragraph 1 | Defines the coverage setting, narrows to barrier coverage, and explains why the metric matters. | Defines barrier coverage, gives concrete security examples, and narrows to MEP. |
| Paragraph 2 | Distinguishes breach/support from exposure. | Explains the practical interpretation of MEP, cites the authors' preceding work, and identifies its obstacle-free assumption. |
| Paragraph 3 | Defines MEP's use, broadens its applications, and explains how environmental factors invalidate the ideal assumption. | Explains why terrain obstacles affect modeling, algorithms, simulation, and interpretation. |
| Paragraph 4 | Treats disturbances as noise and introduces the specific model to be studied. | Defines the new problem, motivates FEA, and explains the intended roles of family retention and bridging crossover. |
| Contribution block | Four bullets. | Five bullets. |
| Final paragraph | Section-by-section roadmap. | Section-by-section roadmap. |

ASC's third paragraph is substantially longer and carries several functions; ESWA's fourth paragraph already previews the method in some detail. The common practice is not a fixed paragraph length. It is **a definition/use opening, an explanation of the inadequate assumption, a concrete proposal paragraph, then contributions and roadmap**.

**Change to DACO:** replace the earlier five-paragraph-plus-contributions introduction with four purposeful narrative blocks. Use the actual comparison against the closest available energy-only CH search, rather than a broad statement that previous algorithms fail to consider energy or density.

## 3. The contribution lists distinguish formulation from computational transformation

ASC's four bullets are: formulate the noise-aware problem and exposure measure; convert it into an objective/constraint optimization task; develop the two solution approaches and operators; evaluate accuracy and computation.

ESWA's five bullets are: formulate OE-MEP; construct its obstacle model and random instance generator; introduce FEA; conduct systematic simulations; analyze solution-quality evidence.

This explains why the formulation is prominent: in these papers, it is part of the claimed research output, not just notation placed before a metaheuristic. ESWA even promotes the instance generator to a separate contribution.

**Change to DACO:** a list saying “use ACO, consider energy, run simulations” is inadequate. The defensible items are the precisely defined density/depletion criterion, the corresponding candidate-construction and ranking procedure, and evidence isolating their behavior. Merely restating a standard 3D acoustic model should not be advertised as a novel formulation. A new dataset is a contribution only if its construction and usefulness are actually established.

## 4. Related work is organized around the exact assumption being changed

ASC, pp. 2–3, first covers ideal models and their solution approaches, then probability-based models. It explicitly distinguishes Eq. (2), a distance attenuation expression, from Eq. (3), a measurement containing random noise. The important question is not whether a previous paper uses the word “probabilistic”; it is whether it provides the noise-aware MEP metric required here. The review ends by identifying that missing metric/formulation and weaknesses in existing solvers.

ESWA, pp. 2–3, first organizes obstacle-free work by Voronoi, grid, and evolutionary methods. It then examines obstacle-aware work, distinguishing simple circular obstacles, incomplete mathematical descriptions, and grid approximation of obstacle boundaries. Thus its claim is narrower than “nobody has considered obstacles.”

**Change to DACO:** the comparison table should distinguish *where* density and energy enter a method. Useful columns are density used for sampling, structural density refreshed after node deaths, complete-tree costs used for ranking, fractional versus absolute depletion, and reporting/service assumptions. A yes/no “energy-aware” column cannot establish our difference.

## 5. The formulation first constructs the meaning of the objective

ASC devotes Eqs. (4)–(16), pp. 3–4, to building the exposure quantity before presenting the optimization task in Section 3.2. In simplified notation, its chain is:

\[
p_i(x)=Q\!\left(\frac{A-C/d(s_i,x)^\lambda}{\sigma_i}\right)
\quad\longrightarrow\quad
\bar p(x)=\prod_i[1-p_i(x)]
\]

\[
E(\mathcal P)=\int_{\mathcal P}-\log\bar p(x)\,ds
\approx -\Delta s\sum_j\sum_i\log[1-p_i(x_j)].
\]

The paper explains the detection threshold through false alarms, explains the negative sign and ordering of the exposure measure, and explains why equal subintervals are introduced. These equations progressively convert an application statement into an evaluable quantity. They are not a collection of unrelated equations decorating Section 3. The probability products require modeling assumptions; their appearance in the paper is not a reason to omit those assumptions in a new model.

ESWA follows a different but equally explicit dependency chain, pp. 3–4: individual sensing laws, Eqs. (1)–(3); aggregate intensity, Eq. (4); obstacle absorption, Eq. (5); continuous exposure, Eq. (6); numerical approximation, Eqs. (7)–(8); optimization objective, Eq. (9).

**Change to DACO:** derive the ranking descriptors in this order:

\[
\text{tree packet counts}\to c_i(T)\to
\delta_i(T)=c_i(T)/E_i\to
P(T)=\frac1n\sum_i\frac{\delta_i(T)^p}{D_i}\to
J(T)=C(T)+\lambda\bar C\,P(T)/\bar P.
\]

Explain the meaning and effect of each transformation. The power, density denominator, and reference scales are modeling/design choices that need justification. They are not an exact derivation of optimal lifetime from a physical law.

### The missing worked example in our earlier formulation

Suppose residual energies are 0.10 J and 1.00 J, and hold both density weights equal to 1. For this illustrative example only, choose the permitted exponent `p=2` rather than the current default 2.6.

| Candidate | Node 1 cost | Node 2 cost | Total cost | Fractional drains | Penalty `P` |
| --- | --- | --- | --- | --- | --- |
| A | 0.020 J | 0.010 J | 0.030 J | 20%, 1% | 0.02005 |
| B | 0.010 J | 0.020 J | 0.030 J | 10%, 2% | 0.00520 |

An energy-only ranking ties these candidates. The fractional-depletion term separates them. This arithmetic example illustrates the purpose of the criterion; it is not an experiment or evidence of longer realized lifetime.

For fixed per-round loads and an unchanged topology, a continuous depletion-time approximation is

\[
L_{\rm frozen}=\min_i E_i/c_i=1/\max_i\delta_i.
\]

This explains why large fractional drains are relevant. It does not show that minimizing the finite-power, density-weighted penalty maximizes lifetime when future CHs, routes, and live sets change.

Also explain the signs: at fixed consumption and residual energy, a **larger density denominator lowers the penalty**. We cannot describe this formula as directly penalizing dense nodes for being dense. The construction heuristic and the evaluation penalty use density in different ways.

## 6. The formal statement uses a recognizable block structure

Both papers give a prose problem statement followed by explicitly labeled **Input → Output → Objective → Constraint(s)** blocks. ASC's block spans pp. 4–5; ESWA's is on p. 4. The output is a candidate solution object, not an algorithm name. The objective then refers to the metric already developed in the preliminaries.

**Change to DACO:** after the explanatory derivation, give a compact block whose inputs are positions, residual energies, range, packet/energy rules, and the configured CH proportion; output is a CH set and its decoded tree; structural constraints specify inclusion, links, and sink reachability. Keep the round score separate from the multi-round endpoint. The calibrated references and ACO controls belong in the method definition, not the physical input list.

## 7. A limitation reappears in representation, operator, and observed failure

This is the strongest connection between the two papers:

| Location | Concrete detail |
| --- | --- |
| ASC, Section 4.2, pp. 5–6 | Introduces an additional forward-motion restriction for GA-MEP. |
| ASC, Section 4.2.1, p. 6 | Enforces nondecreasing x-coordinates and fixed-length steps in its representation. |
| ASC, Section 5.2.6, p. 14 | Reports GA-MEP improving on the grid method on 70/80 exponential instances, 62/80 uniform instances, but only 32/80 Gaussian instances. |
| ASC, same discussion | Explains that avoiding a concentrated sensing region can require moving backward, outside GA-MEP's search space. |
| ESWA, Section 4.2.3, p. 6 | Motivates bridging crossover by the need to create backward path segments around obstacles. |
| ESWA, Figs. 7 and 13 | Shows the resulting representation behavior and example paths. |

The 2019 paper's drawback becomes a concrete design target in the later work. This is much more specific than the statement that algorithms need to balance exploration and exploitation.

**Change to DACO:** explain one identifiable behavior of an energy-only selection rule, show a small example, change the relevant rule, and include a diagnostic that observes whether the behavior changes. Do not claim an expanded feasible routing space if DACO uses the same routing decoder as its baseline. Its main delta can be a change in how that shared space is sampled and ranked.

## 8. The method begins with the solution object and its validity

ASC gives its point-list representation in Fig. 2 and its geometric initialization in Fig. 3 before describing crossover. ESWA first separates the path genes from individual metadata—Age, adult age, death age—in Fig. 3. It then presents normalization in Fig. 4 and Algorithm 1 before the full evolutionary cycle. The EA-versus-FEA comparison in Fig. 5 highlights changed stages, and the complete algorithm appears later as Algorithm 4.

The repair routine is substantive: a path crossing an obstacle must be turned into a valid path, not merely assigned a better score.

**Change to DACO:** show a selected CH list/set and its decoded tree before presenting the full ACO loop. A useful figure has the same deployment in three panels: geometric density support, CH/member/outlier choices, and the final tree with per-node fractional drains. State where membership detachment occurs, what constitutes a failed candidate, and what feedback is updated. Distinguish a construction repair, a scoring rule, and a pheromone update.

## 9. The comparison against our own baseline changes the contribution wording

Inspection of the local implementation matters here:

- `src/algorithms/node_aco.py` already evaluates the completed routing tree and deposits pheromone after each successful candidate.
- `src/algorithms/clustering/node_aco/node_aco.py` already stores node pheromone and reads its current values while constructing later candidates.
- It selects the best candidate by total modeled energy.
- DACO replaces the construction heuristic with grid-derived marginal support and changes ranking to the calibrated density-weighted fractional-depletion criterion. Its evaporation/reference schedule also differs.

Therefore, **completed-tree evaluation, node pheromone, and between-candidate deposits are shared mechanisms, not standalone differences from NodeACO**. The previous draft did not make this separation sharply enough. They should still be documented, but our primary contribution and ablations must target actual deltas. This code observation is not a claim about priority across the published literature.

## 10. Experiments are ordered to explain the method before declaring a winner

ASC's Section 5 runs from p. 9 to p. 17. The order is specific:

1. Define a new diagnostic, saw-tooth degree, to quantify a stated representation weakness.
2. Vary numerical subinterval `Δs` and observe accuracy, time, and smoothness.
3. Vary the model threshold `A` and interpret its physical detection trade-off.
4. Isolate the modified grid implementation against its predecessor.
5. Vary the mixture of its two crossover operators, including each operator alone.
6. Compare grid versus GA across deployment families.
7. Compare against the preceding GA method and discuss computation.

ESWA's experimental sequence is: parameter effects of adult/death age; grid comparison; GA-MEP comparison; Island GA comparison. The final comparator is chosen because it addresses the same claimed diversity mechanism, not because it is another arbitrary optimizer.

**Change to DACO:** test model/deployment factors separately from algorithm factors. Candidate diagnostics should include fractional drains and routing success, not only surviving-node counts. Compare the full method with an energy-only score and controlled density changes before explaining broad superiority. An ACO-versus-PSO plot alone cannot identify the density/depletion contribution.

## 11. The control experiment reuses competing methods' operators

ESWA, Section 5.3.4, p. 13, implements Island GA with **the same crossover, mutation, and normalization routines as FEA**. The difference being investigated is the strategy for retaining diversity. It also uses a 50,000-fitness-evaluation stopping budget, as does the GA-MEP comparison. This is a much more diagnostic comparison than simply setting both algorithms to 100 generations. Other parameter differences remain, so it is not a perfect isolation of every component.

The GA-MEP comparison handles invalid paths by an infinite penalty, whereas FEA repairs them. Thus that comparison includes a feasibility-handling difference as well as the family mechanism. It should not be read as a clean family-only ablation.

**Change to DACO:** use the same decoder and energy evaluator in the decisive comparison. A rank-only ablation can freeze/replay the same candidate set; an online ablation must acknowledge that changing feedback changes later sampled candidates. A full density ablation affects both CH sampling and the penalty denominator, so separate those two changes if attributing effects. Count calibration and failed candidates when defining comparable computation budgets; also report wall-clock cost because evaluation costs can differ.

## 12. Each diagnostic corresponds to a claim made earlier

ASC introduces saw-tooth degree in Section 5.2.1: the average perpendicular distance from an interior path point to the line through its neighbors. It then reports that measure alongside exposure and runtime. It does not assume that a lower objective alone proves the path is smoother.

ESWA claims diversity preservation, then includes population snapshots across iterations in Fig. 12, not just a final best-value plot. Its discussion links the pictures to loss of useful branches in GA-MEP and their retention in FEA. That qualitative link is explanatory evidence, not complete causal isolation of every mechanism.

**Change to DACO:** a claim about balancing depletion needs per-node fractional-drain or residual-energy evidence at a common stage. A claim about geometric coverage of CH choices needs a spatial diagnostic. A claim about live pheromone feedback needs a controlled feedback comparison. We should select figures from claims, rather than add every conventional WSN plot.

## 13. Negative results are tied to mechanisms and operating conditions

The ASC Gaussian result above is not hidden. Table 4, p. 10, also makes a substantial cost visible: at `Δs=1`, the example lists 4.5 s for the grid method versus 642.94 s for GA-MEP, with exposure 0.094 versus 0.084. The paper later recommends the grid approach when speed matters and GA when more computation is acceptable.

ESWA, p. 13, reports average times of 202.1 s for GA-MEP and 270.8 s for FEA. Its Island GA table also has mixed test outcomes: best-of-20 paired Wilcoxon `p=0.0007`, but Mann–Whitney `p=0.419`; the SD comparison has `p=0.686`. The narrative acknowledges nonsignificant comparisons, although its final superiority wording is broader than every individual test supports.

**Change to DACO:** describe the failure regime and its mechanism. If a gain is mainly on clustered deployments or requires greater runtime, state that condition. Do not manufacture a drawback to make a paper usable, and do not discard a scientifically useful source merely because some results are strong. Prefer a scoped result statement over universal superiority.

## 14. Details to learn from without copying blindly

- ESWA's abstract says arbitrary-shaped obstacles, but the formal model represents them as **convex polygons**. The reported main experiment sets absorption `ν=1`. Broader model wording is not the same as validation across all possible shapes or attenuation regimes.
- ASC's no-backward restriction appears in the algorithm section after the general formulation. In our paper, distinguish physical feasibility from a solver's restricted search domain explicitly.
- ASC's complexity section primarily derives fitness-evaluation cost; ESWA additionally multiplies by its population/pairing/generation factors. DACO's complexity discussion should include grid construction, decoding, retries, calibration, and iteration counts rather than quote the cost of one evaluator as the entire algorithm cost.
- Do not copy the papers' “non-differentiable” or “NP-hard” labels onto DACO without a relevant argument. A probability transform involving a smooth Q-function does not by itself establish nondifferentiability everywhere.
- ESWA reports best-of-20, pooled-run, and instance-level tests. For DACO, decide the experimental unit and preserve map/run hierarchy; do not treat all repeated runs as independent deployments. A printed `p=0.0` should be reported as a numerical bound where possible, not an exact zero probability.

## 15. Concrete changes made to the working DACO text

The revised fragments in [output/daco_writing](../../output/daco_writing/README.md) now:

1. Lead with the meaning of repeated collection and depletion before naming DACO.
2. Use a four-block introduction before contributions and roadmap.
3. Name the actual difference from energy-only candidate selection, and identify shared node-pheromone/tree-evaluation machinery as shared.
4. Explain fractional depletion using a worked equal-energy example and a frozen-load lifetime relation.
5. Add explicit input/output/objective/constraint blocks.
6. Explain the separate roles and signs of density, power, calibration, and total energy in the score.

These are writing/model-explanation changes only. No algorithm, simulator, experiment, numerical result, or Overleaf main file was changed. The score remains a surrogate with stated limits; the paper still needs final method specifications and experimental evidence. First-pass fragments are preserved in `output/daco_writing/first_pass/`.
