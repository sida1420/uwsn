# Understanding and screening the DACO related works

## Section 3 study: model, task and method are different layers

27 October 2026. The relevant modeling and problem-definition passages were reread across all sixteen top-level local PDFs, along with the professor's two supplied papers. Three of the sixteen are surveys rather than original optimization formulations. The energy survey is scanned, so its existing OCR was used. The earlier screening decisions below remain in force; inspecting an excluded paper's organization does not validate its results.

| Local paper | Passages checked (PDF pages) | Implication for Section 3 |
| --- | --- | --- |
| PUDCRP | 4-5: network/energy; 12-13: CH score | Deployment assumptions and radio costs precede the proposed PSO/clustering choices. Do not import its radio model or turn a search score into the lifetime definition. |
| RTC | 5: problem statement and preliminaries; 7 onward: protocol | The reporting task includes data reduction and mobile collection. Those application assumptions cannot silently become DACO assumptions. |
| Fanian survey | 3: taxonomy; 30: synthesis | CH selection, routing and algorithm-specific evaluation criteria must be distinguished; the survey has no single original physical optimization model to imitate. |
| IEBR | 2: routing context; 8: constrained throughput objective; 10: lifetime measure | The optimization variable, performance quantity and link/energy constraints are stated separately. Its throughput program is not a lifetime theorem. |
| ACOCR | 5-6: network/energy; subsequent ACO and protocol sections | Physical communication costs are established before search mechanisms. Fixed cubes and CH-only relaying are its choices, not assumptions for our ordinary-relay model. |
| EOCA | 4-5: AUV, acoustic channel and drift models | Collector assistance and movement belong to the service model. Its noise/drift formulas are not needed in a stationary, fixed-range energy study. |
| Two-Tier PSO | 6: sensing/reconstruction setting; 10: hop-energy model | The information task determines what traffic counts mean. Compressed sensing and reconstruction quality cannot be replaced with an invented payload story. |
| EECRP | 6-7: model assumptions; 7: route-cost problem before GA encoding | The mathematical task describes a measurable route cost and explicit constraints; the optimizer and encoding follow it. |
| LEACH survey | 3-4: taxonomy, set-up and data communication | Election, membership and communication are separate parts of collection, not interchangeable descriptions of the objective. |
| Underwater energy survey | 1-2 and overview, via OCR | Energy saving spans several layers. The acoustic energy abstraction should state its scope without importing MAC, charging or hardware claims. |
| EECMR | 5-7: network and channel/energy; 11: lifetime evaluation | Node roles and cost assumptions precede protocol decisions; survival measures are not an arbitrary powered penalty. |
| UCPSO | 4: Section III model, followed by Section IV CH encoding/fitness | Its distinction between system model and proposed fitness was missing from the earlier drafts. The calibrated DACO penalty belongs to Section 4, not the definition of lifetime. |
| LLCP | 4-5: problem statement and network model | Formulate the performance actually being sought: capacity/complexity there, lifetime here. A convenient search criterion cannot substitute for that task. |
| QLAR | 4-5: graph, assumptions and MDP | State the network decision and accumulated objective before the learning procedure; do not borrow its mobility assumptions. |
| FCRA | 7-8: energy equations and clustering procedure | Retains its earlier evidence exclusion. Its radio model, loose terminology and missing service distinctions are not a template for our formulation. |
| AC-ACO | 7-8: model definition, residual-energy update and method boundary | Retains its earlier evidence exclusion. Separate energy accounting from search updates and do not import its terrestrial cost law. |

The professor's ASC paper builds the physical exposure quantity in Section 3.1, Eqs. (4)-(16), before the formal task in Section 3.2, Eq. (17). Her ESWA paper similarly derives exposure in Eqs. (6)-(8) and states the task in Eq. (9). Crucially, their derived quantity is the problem's exposure measure; that does not justify treating DACO's calibrated search fitness as network lifetime. The detailed page-based reading remains in `professor_study/CLOSE_READING.md`.

The revised Section 3 therefore contains the reporting graph, packet/energy accounting and admissible collection schedules, followed by duration maximization and an energy preference among schedules of equal duration. It does not claim that the implemented heuristic solves this full sequential optimization. The fixed two-packet CH rule and clipped battery update remain explicit model conventions. Grid support, powered depletion, calibration, pheromone and bounded construction are Section 4 material; no part of Section 4 was rewritten in this pass. Source comparisons and citations remain in Introduction/Related works, as requested.

Additional previously studied manuscripts were also checked: IS-k-means pp. 3-4 distinguishes clustering cost and membership constraints from KDE and the proposed algorithm; DEKCS pp. 3-4 separates RF/AUV channel assumptions from the clustering rule. The cached GTC download was not a readable PDF, so no fresh full-text claim is made for it here.

Review date: 26 October 2026. Scope: all **nine local PDFs and ten previously recommended papers**, followed by replacement candidates. Read this document instead of treating the earlier recommendation table as a quality assessment.

## What changed after reading

The revised additional-paper list contains **10 papers**: EOCA, IS-k-means, DEKCS, EECMR, LLCP, PUDCRP, GTC, IEBR, RTC, and EECRP. The original collection contributes three background surveys and four useful algorithm papers: ACOCR, Two-Tier PSO, UCPSO, and QLAR.

I exclude **AC-ACO (2025)** and **FCRA (2025)** from the proposed empirical related-works set because of specific unresolved reporting/reproducibility problems. Their summaries and evidence are preserved below. Existing PDFs have not been deleted.

I also withdraw five earlier recommendations from the active list: EULC, EBAR, fragile-collection ACO, EEUMC, and CDFO-UWSN. Their concepts remain relevant, but I could not obtain enough of their original methods and experimental results for the requested critical audit. This is an **access/evidence hold, not a finding that those papers are unsound**. Their limited summaries below do not pretend to be full-paper reviews.

Large improvements alone are not grounds for rejection. A useful paper can have a large gain against a weak baseline, yet clearly state its assumptions and costs. Conversely, a future-work paragraph does not repair contradictory tables. I apply your screening rule to **unsupported universal superiority, unclear evaluation, and unresolved contradictions**, while keeping papers with understandable, defensible limitations. Author-stated limitations and my assessment are labeled separately.

## A short guide to the problem

A normal sensor sends its reading to a **cluster head (CH)**. The CH receives several readings, combines them, and sends information toward the **sink**, possibly through other sensors. A CH near the sink may forward its own cluster's traffic plus traffic from distant clusters. It can die early even when most sensors still have energy: this is the **hot-spot/energy-hole problem**.

Three quantities must not be confused:

- **Density:** how many sensors, or how much covered sensing volume, surround a location.
- **Load:** how much receiving, processing, and forwarding work a node actually performs.
- **Relative depletion:** what fraction of its remaining battery that work consumes, approximately `round_energy_i / remaining_energy_i`.

A dense location may be a good place for a CH, but its CH can become overloaded. A sparse location may contain an irreplaceable bridge to the sink. Maximizing density or minimizing total energy alone does not necessarily protect that bridge.

Most papers below change one or more of four things: **which nodes become CHs, which members join each CH, which relay path carries their traffic, or how much information is transmitted**. These changes must be distinguished when comparing against DACO.

Notation used below: `E_i` is remaining energy; `e_i` is one-round consumption; `d_ij` is link distance; `D_i` is distance to the sink; `tau` is pheromone; `eta` is heuristic desirability. FND/HND/LND mean first/half/last node death. PDR is the fraction of generated packets delivered. A service round in DACO is not automatically equivalent to any paper's FND or LND.

Equations labeled **teaching model** explain the mechanism with simpler notation; they are not verbatim reproductions or implementation specifications. Other equations identify their paper equation or section. PDF page references are one-based positions in the local file, rather than printed journal page numbers.

## Decision map

| ID | Paper | Decision | Appropriate use |
| --- | --- | --- | --- |
| L1 | Fanian survey, 2019 | Keep: background | Taxonomy and evaluation criteria |
| L2 | ACOCR, 2020 | Keep with caveats | Closest existing ACO/acoustic routing reference |
| L3 | Two-Tier PSO, 2020 | Keep with caveats | Joint energy and sensing-quality discussion |
| L4 | LEACH survey, 2021 | Keep: background | Explain CH selection versus routing |
| L5 | Underwater energy survey, online 2021 / issue 2022 | Keep: background | Physical and protocol-layer assumptions |
| L6 | UCPSO, 2022 | Keep: high relevance | Relay-load-aware unequal clustering |
| L7 | QLAR, 2025 | Keep: complementary | Mobility, connectivity, and control overhead |
| L8 | FCRA, 2025 | Exclude from empirical set | Simulator/baseline specification unresolved |
| L9 | AC-ACO, 2025 | Exclude from empirical set | Parameter and energy-accounting inconsistencies |
| R1 | EOCA, 2020 | Keep: qualify scenario | Neighbor-aware clustering with AUV assistance |
| R2 | EULC, 2018 | Hold; replace for now | Original full-method/result audit incomplete |
| R3 | EBAR, 2019 | Hold; replace for now | Abstract verified; experimental audit incomplete |
| R4 | Fragile-collection ACO, 2020 | Hold; replace for now | Abstract/figures verified; method audit incomplete |
| R5 | IS-k-means, 2021 | Keep: high relevance | Density and energy balance; terrestrial model |
| R6 | DEKCS, 2021 | Keep: methodological reference | Underwater RF/AUV scenario, not acoustic validation |
| R7 | EECMR, 2021 | Keep with caveats | Simple underwater clustering/relay baseline |
| R8 | LLCP, 2024 | Keep: complementary | Capacity/load constraints, not lifetime optimization |
| R9 | EEUMC, 2025 | Hold; replace for now | Abstract verified; results audit incomplete |
| R10 | CDFO-UWSN, 2023 | Hold; replace for now | Headline percentages not sufficiently interpretable |
| N1 | PUDCRP, 2019 | Add: methodological reference | Distribution-aware unequal clustering |
| N2 | GTC, 2021 | Add with arithmetic caveat | CH rotation through modeled incentives |
| N3 | IEBR, 2019 | Add: complementary | Energy balance constrained by routing feasibility |
| N4 | RTC, 2019 | Add: application-dependent | Explicit energy versus information-loss trade-off |
| N5 | EECRP, 2021 | Add with caveats | Fusion plus route search; computation cost acknowledged |

## The nine papers already in your folder

### L1. Cluster-based routing protocols in wireless sensor networks: A survey based on methodology (2019)

**Source:** Fanian and Kuchaki Rafsanjani, [DOI](https://doi.org/10.1016/j.jnca.2019.04.021). Local PDF: [read](2019_Cluster-based%20routing%20protocols%20in%20wireless%20sensor%20networks%20A%20survey%20based%20methodology.pdf). Useful material: classification and comparison tables, especially Tables 11 and 14.

**Problem.** Many clustering papers report longer lifetime, but organize their methods differently and optimize different things. Reading only their final lifetime curves makes them difficult to compare.

**Proposal in plain language.** This is a map of the literature, not a new routing algorithm. It groups methods into classical, fuzzy, metaheuristic, and hybrid fuzzy/metaheuristic approaches. It asks what information each method needs, where optimization runs, what it optimizes, and what its limitations are.

For example, a fuzzy system can choose a CH using energy and neighbor count, while ACO chooses the route afterward. Calling the whole method simply an “ACO algorithm” conceals that distinction.

**Results and limitations.** Its contribution is structured comparison, not a common simulator experiment demonstrating that one algorithm wins. Its tables identify issues such as neighbor-information overhead, one-hop scalability limits, and missing application assumptions. **My assessment:** the surveyed protocols were evaluated under different conditions; their gains cannot be pooled into a reliable numerical ranking. Its terrestrial focus also does not supply an acoustic channel model.

**Use for DACO.** Keep as background and as a template for your comparison table: CH selection, membership, routing, objective, information required, cost, and limitation. Do not cite it as experimental proof that DACO's chosen family is superior.

### L2. A Clustering Routing Algorithm Based on Improved Ant Colony Optimization Algorithms for Underwater Wireless Sensor Networks (ACOCR, 2020)

**Source:** Xiao and Huang, [DOI](https://doi.org/10.3390/a13100250). Local PDF: [read](2020_A%20Clustering%20Routing%20Algorithm%20Based%20on%20Improved%20Ant%20Colony%20Optimization%20Algorithms%20for%20UWSN.pdf). Inspect PDF pp. 5–11 for assumptions and method; pp. 12–15 for results and limitations.

**Problem.** Randomly chosen CHs can have little remaining battery or poor locations. Choosing a short next hop alone can send traffic through weak nodes or along an expensive overall route.

**Proposal in plain language.** Partition the water volume into cubes. Within each cube, prefer a well-powered node that is close both to the sink and its members. Then use improved ACO to select CH-to-sink routes. Limit pheromone values, adjust evaporation, and restrict the ants' search area.

The CH score in Eq. (14) is:

$$
I_i=\frac{\lambda E_i}{D_i\,\bar d_i},
$$

where `bar d_i` is mean distance to the other nodes in its cube. Higher energy helps; longer collection/forwarding distances hurt. The routing heuristic in Eq. (13) is:

$$
\eta_{ij}=\frac{E_j/E_0}{\sigma d_{ij}+(1-\sigma)D_j}.
$$

Ants prefer relays that have more battery and offer economical progress toward the sink.

**Results.** The paper compares ACOCR with LEACH, DUCS, LEACH-ANT, CUWSN, and EOCA. For its 400-node example at round 1200, Table 2 reports packet loss of 12.8% for ACOCR versus 14.9% for EOCA. These numbers describe that experiment, not DACO's topology.

**Author-stated limits.** The underwater multipath effect is omitted; more realistic network simulation is future work. **My assessment:** the nodes are static, positions are known, each cube becomes a cluster, and the sink computes routes. Cube occupancy can vary greatly in nonuniform deployments. The text's packet-loss definition is also worded inconsistently with the conventional lost/generated definition, so verify the actual calculation before reproducing that metric.

**Use for DACO.** Keep. Explain that it uses ACO mainly for **routing after CH selection**, whereas DACO uses density-aware ACO to select CH sets and evaluates the resulting tree. Do not present them as the same search problem.

### L3. Two-Tier PSO Based Data Routing Employing Bayesian Compressive Sensing in Underwater Sensor Networks (2020)

**Source:** Chen, Xiong, and Chu, [DOI](https://doi.org/10.3390/s20205961). Local PDF: [read](2020_Two-Tier%20PSO%20in%20Underwater%20Sensor%20Networks.pdf). Method: PDF pp. 7–15; experiments: pp. 15–19; future work: pp. 19–20.

**Problem.** Sending every sensor reading is expensive. Sending fewer measurements saves transmissions, but may make the original environmental signal impossible to reconstruct accurately. CHs near the sink can also become overworked.

**Proposal in plain language.** Run PSO twice. First choose CHs with sensible collection distances and distribution. Then choose participating sensors and routes that also produce a useful compressed measurement matrix. The sink reconstructs the environmental field using Bayesian compressive sensing.

The key sensing relationship is:

$$
y=\Phi\Psi x+n.
$$

`x` is a sparse representation of the environmental signal; `Psi` transforms it into sensor readings; `Phi` describes which combinations are collected; `n` is noise. A better route must therefore carry information that is useful for reconstruction, not merely use little energy. The second fitness combines a reconstruction-quality term and an energy/balance term.

**Results.** The simulation uses 1000 selected temperature-data locations over an approximately 18.5 km × 14.5 km × 0.8 km region. It compares with DRMCS and a 3D extension of ICCS. Reported first death occurs after roughly 100 rounds instead of about 70 for its comparators. The advantage in reconstruction error becomes less pronounced at high measurement ratios.

**Author-stated limit.** Clustering and routing are optimized separately; integrated optimization is future work. **My assessment:** more measurements can improve reconstruction but require more communication. Performance depends on signal sparsity, compression assumptions, fitness weights, and two search stages. The calibration discussion uses a reconstructed signal as a proxy for unavailable ground truth, so do not treat every reported error as an independent measurement against known truth.

**Use for DACO.** Keep for the energy–information trade-off and layered balancing idea. It is not a fair direct lifetime comparison unless DACO uses equivalent compression and data-quality requirements.

### L4. A comprehensive survey on LEACH-based clustering routing protocols in Wireless Sensor Networks (2021)

**Source:** Daanoune, Abdennaceur, and Ballouk, [DOI](https://doi.org/10.1016/j.adhoc.2020.102409). Local PDF: [read](2021_A%20comprehensive%20survey%20on%20LEACH-based%20clustering%20routing%20protocols%20in%20WSNs.pdf). See Tables 9–11 and the discussion around PDF pp. 17–19.

**Problem.** LEACH rotates CHs randomly, but many extensions modify different parts of the process. A better CH rule does not necessarily give a better transmission route.

**Proposal in plain language.** Organize LEACH descendants according to whether they improve CH selection, data transmission, or both. Compare their assumptions and features: residual energy, single/multi-hop communication, mobility, scalability, and deployment.

**Results and limitations.** The survey compares 27 protocols and discusses complexity, deployment, fault tolerance, and other open issues. It does not run all protocols under one acoustic simulator. **My assessment:** labels such as “high energy efficiency” in its qualitative tables summarize the reviewed literature; they are not standardized effect sizes. LEACH's terrestrial/radio assumptions require care underwater.

**Use for DACO.** Keep as background. It supports explaining why your contribution must specify both **selection** and **transmission**. It does not establish that a new optimizer alone solves energy imbalance.

### L5. A survey on energy efficiency in underwater wireless communications (online 2021; journal issue 2022)

**Source:** Islam et al., [DOI](https://doi.org/10.1016/j.jnca.2021.103295). Local PDF: [read](2021_A%20survey%20on%20energy%20efficiency%20in%20underwater%20wireless%20communications.pdf). This file is scanned: OCR was used for reading, and the first page was visually checked. Useful material: Tables 2, 5–7 and Sections 3–6.

**Problem.** Underwater batteries are hard to replace, but network lifetime depends on much more than which nodes are CHs. The physical link, MAC scheduling, localization, and energy supply all matter.

**Proposal in plain language.** Review energy-saving methods across the stack. Compare acoustic, optical, RF, and magnetic-induction communication; then examine routing, MAC, localization, harvesting, and charging.

**What you should understand.** Acoustic links can cover long distances but have limited bandwidth and long propagation times. Other technologies can offer attractive rates or energy costs under different range, alignment, and water conditions. A method successful under one technology is not automatically validated for another.

**Results and limits.** This is a survey, not a new algorithm or controlled numerical winner. **My assessment:** it organizes evidence from heterogeneous hardware, applications, and models. It cannot provide one transferable lifetime improvement percentage. Its scope also predates later papers in your collection.

**Use for DACO.** Keep to justify the acoustic model and boundaries of your claims. It is particularly useful for explaining why DEKCS's RF experiment and terrestrial first-order radio experiments need adaptation before becoming DACO baselines.

### L6. An Unequal Clustering Method Based on Particle Swarm Optimization in Underwater Acoustic Sensor Networks (UCPSO, 2022)

**Source:** Hou et al., [DOI](https://doi.org/10.1109/JIOT.2022.3195223). Local PDF: [read](2022_An_Unequal_Clustering_Method_Based_on_Particle_Swarm_Optimization_in_Underwater_Acoustic_Sensor_Networks.pdf). Read PDF pp. 4–6 for the method and pp. 7–9 for experiments and limitations.

**Problem.** A CH receiving many member packets may also relay packets from other CHs. Treating every cluster equally ignores that second burden and can kill near-sink CHs early.

**Proposal in plain language.** Represent a CH selection as a binary string. Search using discrete PSO with exchanges, personal/global best solutions, and mutation. Evaluate predicted round consumption and prefer CHs with healthy batteries. After choosing CHs and routes, adjust cluster sizes using remaining energy, sink distance, and the number of inter-cluster forwarding duties.

The two objective ingredients are `f1 = E0 / mean_CH_energy` and `f2 = predicted_total_round_energy`, mapped through a sigmoid before weighting. A member chooses a CH using Eq. (7):

$$
w_{i,c}=\frac{d(i,c)}{r_c}.
$$

Here `r_c` is the CH's adapted service range. A heavily burdened CH receives a smaller range, making it less attractive to additional members. Nearby sensors can also send directly to the sink.

**Results.** It improves node-survival and early energy-consumption measures against LEACH, EULC, and IPSO. Crucially, its total residual-energy curve crosses IPSO's around round 241: keeping more sensors working can consume more energy later. The paper explains this rather than claiming superiority in every quantity at every time.

**Author-stated limits.** The study does not consider network connectivity or information-transmission reliability. **My assessment:** reliable-link assumptions, centralized information, discrete-search budget, and sigmoid/weight choices limit transferability.

**Use for DACO.** Keep as a core reference. Its relay-aware unequal membership addresses a closely related problem. Distinguish its **cluster-size control** from DACO's **penalty on evaluated relative depletion divided by structural density**.

### L7. A Q-Learning-Based Link-Aware Routing Protocol for Underwater Wireless Sensor Networks (QLAR, 2025)

**Source:** Li et al., [DOI](https://doi.org/10.3390/jmse13122374). Local PDF: [read](2025_A%20Q-Learning-Based%20Link-Aware%20Routing%20Protocol%20for%20Underwater%20Wireless%20Sensor%20Networks.pdf). See PDF pp. 8–15, 16–17, and 24–29.

**Problem.** An energy-efficient next hop is useless if it moves out of range before forwarding the packet. Fixed routing metrics and stale neighbor information are especially weak in mobile underwater networks.

**Proposal in plain language.** Learn which next hop is promising, using residual energy, geometry, and predicted **link expiration time**. Weight these metrics adaptively using entropy weights. Predict neighbor state between Hello messages and change Hello frequency according to expected link lifetime.

The standard Q-learning idea is:

$$
Q(s,a)\leftarrow(1-\alpha)Q(s,a)+\alpha[r+\gamma\max_{a'}Q(s',a')].
$$

In ordinary language: revise the attractiveness of a next hop using its immediate reward and expected downstream reward. Eq. (14) sets the Hello interval proportionally to the shortest predicted neighbor-link lifetime. Short-lived links require more frequent updates.

**Results.** NS-3 experiments use a 500 m cube, 20–60 nodes, speeds of 1–5 m/s, 30 runs, and 95% confidence intervals. The paper also disables its link metric to test that component's contribution.

**Trade-offs reported by the paper.** Short Hello intervals increase control energy and collisions; long intervals can reduce PDR, especially at high mobility. **Author-stated future work:** current-driven motion, multipath, load balancing, and redundancy suppression. **My assessment:** the binary range-based channel simplifies real acoustic links; this is next-hop routing, not CH selection, and its short-run delivery metrics do not prove lifetime improvements.

**Use for DACO.** Keep as a complementary reference for the gap between energy balance and dependable connectivity. Do not claim DACO already solves QLAR's mobility problem.

### L8. Improving routing in wireless sensor networks technology on data aggregation using fused cluster routing algorithm (FCRA, 2025)

**Source:** Ghantasala et al., [DOI](https://doi.org/10.1007/s43621-025-01300-y). Local PDF: [read](2025_Improving%20routing%20in%20wireless%20sensor%20networks%20technology%20on%20data%20aggregation%20using%20fused%20cluster%20routing%20algorithm.pdf). Decision: **exclude from the empirical related-works set**.

**Problem.** Nearby sensors often transmit similar readings. Forwarding all of them wastes energy, bandwidth, and time.

**Proposal in plain language.** Form clusters around suitable CHs, use spatial/temporal correlation to combine repeated information, and forward aggregated data. The intended saving is simply: fewer transmitted bits should require less communication energy. This is a data-reduction intervention as well as a routing intervention.

**What is reported.** The results discuss aggregation, delay, and throughput, and claim broader gains in energy use and lifetime.

**Why exclude it.** In Section 4.1, on PDF p. 10, the same setup paragraph describes implementation in **NS-3** and then says **NS-2** results were used for comparisons. Baseline identities also shift: that paragraph names CDA, DAITCADA, EDT, and DRINA, while later results discuss CBDAW and DCSTC. Table 1 contains “system magnitude 90” and “determined nodes 500” without a sufficiently clear mapping to the evaluated node count. These ambiguities prevent confidently reconstructing the claimed comparison. The reported radio frequency is 2.6 GHz, so it is also not an underwater-acoustic experiment.

**Author-stated limits.** Larger deployments, implementation issues, security, and numerical data-quality evaluation remain future work. **My assessment:** these statements do not resolve the evaluation inconsistencies. This is a reason to avoid using its gains as evidence, not an allegation about the authors' intent.

**Replacement.** Prefer RTC for an explicit information-loss trade-off, and EECRP for a specified underwater fusion-plus-routing pipeline.

### L9. An Efficient Clustering Algorithm for Enhancing the Lifetime and Energy Efficiency of Wireless Sensor Networks (AC-ACO, 2025)

**Source:** Zhou, Chen, and Cao, [DOI](https://doi.org/10.32604/cmc.2025.065561). Local PDF: [read](2025_LongMinh_An%20Efficient%20Clustering%20Algorithm%20for%20Enhancing%20the%20Lifetime%20and%20Energy%20Efficiency%20of%20Wireless%20Sensor%20Networks%20%281%29.pdf). Decision: **exclude as a trusted empirical baseline until clarified**.

**Problem.** Ordinary ACO may reinforce poor choices too strongly and converge before exploring enough alternatives, producing uneven energy use.

**Proposal in plain language.** Add a deterministic chaotic signal to perturb the search, and adapt evaporation and heuristic influence as optimization progresses. The logistic map is:

$$
x_{t+1}=r x_t(1-x_t).
$$

Its irregular values perturb pheromone/search decisions so the ants keep exploring. The energy-aware heuristic favors well-powered nearby nodes. This is a terrestrial RF WSN method in the paper; using the idea in an acoustic simulator does not reproduce its experiment.

**Results claimed.** Higher survival, lower consumption, better delivery, and lower delay against ACO, PSO, GA, and LEACH variants.

**Specific unresolved problems.** Table 2 on PDF p. 16 sets communication radius to **20 m**; its accompanying setup text on p. 17 says **50 m**. With 200 nodes initially at 0.6 J, total initial energy is 120 J. At round 2000, Table 3 reports 101.9 J consumed, leaving 18.1 J. Averaged over the original 200 nodes, that is **0.0905 J**, whereas Table 4 reports **0.12 J**. The tables do not explain a denominator or population change that reconciles these values. Both table pages were visually checked; see the [rendered evidence](evidence/README.md).

Algorithm 1 also places physical residual-energy updates inside the ant loop. A reproduction must establish whether these are hypothetical candidate evaluations or real transmissions; confusing them changes the experiment. The convergence discussion does not substitute for a finite-budget performance guarantee.

**Author-stated limit.** Computational cost in very large heterogeneous networks requires further work. **My assessment:** the unresolved parameter and energy-accounting inconsistencies are more material than a generic complexity caveat.

**Replacement.** Use ACOCR for acoustic ACO and UCPSO/PUDCRP for load-aware clustering. Your existing AC-ACO implementation may still be tested as an internally defined comparator, but should not be described as a validated exact reproduction of this paper.

## The ten papers from the earlier recommendation list

### R1. An Energy Optimization Clustering Scheme for Multi-Hop Underwater Acoustic Cooperative Sensor Networks (EOCA, 2020)

[DOI](https://doi.org/10.1109/ACCESS.2020.2993544) · IEEE Access, SJR 2024 Q1. The [author-uploaded full text](https://www.researchgate.net/publication/341320417_An_Energy_Optimization_Clustering_Scheme_for_Multi-Hop_Underwater_Acoustic_Cooperative_Sensor_Networks) supplied the method, scenario, and results sections.

**Problem/proposal.** Selecting the node covering most neighbors can exhaust that node. EOCA combines neighbor coverage, residual energy, and sink distance in distributed CH competition, then reduces effective communication range as batteries decline. In plain language: choose useful gathering points without repeatedly overworking them.

**Results and boundary.** The study uses an AUV-assisted cooperative network; one experiment has 90 nodes at 20 m depth over a 10 km square, and results are averaged over 200 Monte Carlo runs. Area and node-count sweeps show where delivery and lifetime deteriorate, rather than establishing deployment-independent gains.

**Stated limit:** optimizing the AUV collection trajectory is outside scope, and the AUV is assumed capable of correctly collecting from sufficiently nearby CHs. **My assessment:** this substantial assistance prevents treating its lifetime result as a direct surface-sink DACO comparison. Shrinking communication range also makes connectivity a necessary check.

**Decision/use.** Keep for neighbor-aware clustering and adaptive-range ideas; qualify the AUV and shallow deployment. It does not establish a solution to DACO's complete 3D forwarding-load problem.

### R2. Energy-Balanced Unequal Layering Clustering in Underwater Acoustic Sensor Networks (EULC, 2018)

[DOI](https://doi.org/10.1109/ACCESS.2018.2854276) · IEEE Access, SJR 2024 Q1. **Access status: original methods/results audit incomplete.**

**Verified idea.** The paper addresses unequal energy use by dividing the network into depth-related layers and forming unequal clusters. Later primary papers describe CH competition using residual energy, node degree, and sink distance. The intuition is to leave forwarding-heavy CHs less local collection work.

**What cannot yet be concluded.** I did not obtain the original full experimental section. I therefore do not certify its exact radius formula, lifetime definition, gain percentages, control overhead, or robustness. A later paper's description is not a substitute for auditing EULC's own results.

**Decision/use.** Hold out of the active evidence set. GTC provides an accessible underwater layered-clustering alternative, and UCPSO provides a more direct discussion of relay-dependent membership. This hold is not evidence that EULC has no drawbacks or implausible results.

### R3. Energy-Efficient Load Balancing Ant Based Routing Algorithm for Wireless Sensor Networks (EBAR, 2019)

[DOI](https://doi.org/10.1109/ACCESS.2019.2934889) · IEEE Access, SJR 2024 Q1. [Author institution record](https://researchprofiles.tudublin.ie/en/publications/energy-efficient-load-balancing-ant-based-routing-algorithm-for-w/). **Access status: abstract verified; full result audit incomplete.**

**Problem/proposal.** A route with attractive immediate energy cost can repeatedly burden the same nodes. EBAR combines pseudo-random route discovery, modified pheromone updates, an expected-energy heuristic, and energy-based opportunistic broadcasts. The intended effect is to balance forwarding while limiting discovery traffic.

**Limits of this summary.** It is a terrestrial routing paper, not an acoustic CH-selection experiment. The abstract does not establish the actual cost of its control traffic or the precise circumstances in which its predicted-lifetime improvement holds. Those must be checked in the complete paper.

**Decision/use.** Hold rather than invent a negative result. Replace its role in the current list with GTC/IEBR for inspectable energy-balancing mechanisms; retain ACOCR as the directly read ACO reference. Reconsider EBAR when its full text is available.

### R4. Routing Clustering Protocol for 3D Wireless Sensor Networks Based on Fragile Collection Ant Colony Algorithm (2020)

[DOI](https://doi.org/10.1109/ACCESS.2020.2982691) · IEEE Access, SJR 2024 Q1. [Author-uploaded record](https://www.researchgate.net/publication/340107803_Routing_Clustering_Protocol_for_3D_Wireless_Sensor_Networks_Based_on_Fragile_Collection_Ant_Colony_Algorithm). **Access status: abstract and figure descriptions checked; complete method unavailable.**

**Problem/proposal.** CHs in 3D networks can consume too much energy. The proposal adds a load-transfer node and a secondary CH, with ACO-generated inter-cluster routes. One node helps carry current work while another is prepared to take over, reducing repeated reconstruction.

**Limits.** “3D” does not mean an underwater acoustic model. Without the full algorithm and experiments, I cannot verify role-management overhead, replacement rules, search budgets, or failure handling. The abstract's dominance over three protocols is insufficient for your quality filter.

**Decision/use.** Hold and replace with PUDCRP for an inspectable distribution-aware clustering mechanism and explicit evaluation assumptions. Do not cite unverified performance percentages from this record.

### R5. Improved Soft-k-Means Clustering Algorithm for Balancing Energy Consumption in Wireless Sensor Networks (IS-k-means, journal 2021)

[DOI](https://doi.org/10.1109/JIOT.2020.3031272) · IEEE Internet of Things Journal, SJR 2024 Q1. [Full author manuscript](https://arxiv.org/abs/2403.15700); uploaded 2024, but the journal article is 2021. See manuscript pp. 6–12.

**Problem/proposal.** Arbitrary centers create poor clusters; always choosing dense-area CHs overloads them. Initialize centers using density peaks/KDE, form soft memberships, move suitable boundary nodes to balance cluster sizes, and rotate through multiple candidate CHs.

For cluster center `mu_c`, membership is proportional to `exp(-beta * ||x_i-mu_c||²)`: nearer clusters are more likely, but boundary nodes remain movable.

**Results/limits.** It compares seven schemes using lifetime and energy variance. Its own discussion shows that a method can have later LND yet much earlier FND: sacrificing many nodes is not good balance. Critically, its evaluation treats **85% node death as “all nodes dead”**, so its reported LND is a proxy. The EB-CRP comparator is adapted, rather than its untouched original implementation.

**Stated limit:** extension to multi-hop is future work. **My assessment:** radio energy, single-hop operation, density bandwidth/stiffness choices, and changed comparator definitions limit transfer.

**Decision/use.** Keep; highly relevant prior density/balance work. Do not claim grid density is novel merely because DACO uses a different optimizer.

### R6. DEKCS: A Dynamic Clustering Protocol to Prolong Underwater Sensor Networks (2021)

[DOI](https://doi.org/10.1109/JSEN.2021.3054943) · IEEE Sensors Journal, SJR 2024 Q1. [Author manuscript and repository](https://eprints.gla.ac.uk/227979/). See manuscript PDF pp. 4–8.

**Problem/proposal.** A node near a geometric centroid may poorly serve an uneven deployment. Cluster using k-means, select a sufficiently powered node close to many members, vary the number of clusters with an elbow rule, and relax CH energy thresholds as the network depletes. An AUV gathers CH data.

**Results.** It reports approximately 90.5% and 41.2% improvements over LEACH and k-means-based LEACH in its defined lifetime experiment.

**Essential correction:** the actual simulation is **underwater RF**, with a nominal **2 m** radio range and an AUV, not DACO's long-range acoustic network. The authors explicitly acknowledge that favoring dense regions can harm proportional fairness and drain outliers early. Future work includes coverage, delay, and reliability trade-offs.

**Decision/use.** Keep as a methodological reference, not acoustic validation. It is particularly useful for explaining why DACO should protect sparse/bridge nodes instead of optimizing average collection distance alone.

### R7. Energy-Efficient Clustering Multi-Hop Routing Protocol in a UWSN (EECMR, 2021)

[DOI](https://doi.org/10.3390/s21020627) · Sensors, SJR 2024 Q1. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7831061/). Method and evaluation: PDF pp. 8–15.

**Problem/proposal.** CHs should not remain burdened indefinitely, and deep nodes need a route through shallower layers. Elect CHs using energy, sink distance, and CH-role duration; assign boundary nodes as relays between layers; rotate roles.

Eq. (8) combines normalized role duration, sink distance, and energy into a CH weight. This is an inexpensive rule rather than population search.

**Results/limits.** Experiments compare with LEACH, DBR, and EERBLC under different node counts and 150/200 m ranges. At the lower range, some clustering methods have similar survival performance; the text also notes favorable EERBLC results in some settings. Mobility-triggered re-clustering costs energy. The paper acknowledges range/performance trade-offs and leaves topology optimization and firmware deployment open.

**My assessment:** topology changes every 100 rounds simplify continuous mobility. The reproduced energy equations and a range/energy explanation require careful unit/definition checks before coding.

**Decision/use.** Keep as a conditional, simpler underwater baseline; avoid claiming it wins under every range or that reported residual energy proves delivery quality.

### R8. Node Load and Location-Based Clustering Protocol for Underwater Acoustic Sensor Networks (LLCP, 2024)

[DOI](https://doi.org/10.3390/jmse12060982) · Journal of Marine Science and Engineering, SJR 2024 Q2. [Full text](https://www.mdpi.com/2077-1312/12/6/982). See Sections 3.3–3.5 and 4.

**Problem/proposal.** Fewer, larger clusters simplify coordination, but too many members overload a CH. Estimate capacity using packet sizes, TDMA slots, propagation delays, and guard time. Admit/remove members and prioritize clustering so each cluster is large **without exceeding capacity**.

Teaching model: `sum(member bit rates) <= usable CH service rate`. The paper's Eq. (7) is a more detailed timing constraint.

**Results/limits.** NS-3 tests use five repetitions and vary density, packet size, and range. When load grows, LLCP sometimes needs **more clusters** to prevent the steep delays seen in its DEKCS comparator. That is a visible cost, not free superiority. The design assumes a particular TDMA frame and omits intra-cluster ACK confirmation.

**My assessment:** cluster count is a proxy for complexity, not measured energy lifetime. The DEKCS adaptation also needs scrutiny given DEKCS's different original RF/AUV setting.

**Decision/use.** Keep for load/capacity reasoning. It does not prove DACO's energy-balance objective or solve its complete routing problem.

### R9. Energy-efficient unequal multi-level clustering for underwater wireless sensor networks (EEUMC, issue 2025)

[DOI](https://doi.org/10.1016/j.aej.2024.10.026) · Alexandria Engineering Journal, previously screened as SJR 2024 Q1. [Publisher record](https://www.sciencedirect.com/science/article/pii/S1110016824011815). **Access status: abstract verified; full experimental audit incomplete.**

**Verified idea.** Use a hierarchy of unequal clusters, choose CHs from remaining energy and sink proximity, and combine routing with adaptive aggregation. The intended benefit is to distribute energy use and reduce transmitted data.

**What remains unknown.** I could not inspect the complete equations, aggregation rule, matched baseline configuration, uncertainty, or numerical results. The abstract's general superiority claim is not enough to separate the benefit of clustering from the benefit of transmitting less information.

**Decision/use.** Withdraw from the active shortlist until audited. EECRP and RTC offer inspectable fusion/routing mechanisms and identifiable costs. No conclusion about EEUMC's intrinsic validity follows from the access problem.

### R10. Clustering-based dragonfly optimization algorithm for underwater wireless sensor networks (CDFO-UWSN, 2023)

[DOI](https://doi.org/10.1016/j.aej.2023.09.047) · Alexandria Engineering Journal, previously screened as SJR 2024 Q1. [Publisher record](https://www.sciencedirect.com/science/article/pii/S1110016823008359). **Access status: abstract verified; full audit incomplete.**

**Verified idea.** Use dragonfly-inspired search to organize clusters and forwarding, and test different deployment sizes, densities, and ranges.

**Evidence concern.** The abstract reports 78.13% and 64.71% improvements “in terms of” node number and transmission range. Those are normally scenario inputs, so the measured output and denominator must be identified before the percentages are meaningful. I could not obtain the full evaluation needed to resolve this; that alone does not prove the underlying experiments are wrong.

**Decision/use.** Withdraw for now. Replace with PUDCRP for a readably specified distribution-aware search mechanism, and IEBR for an inspectable energy/feasibility trade-off. Do not repeat the abstract's percentages in your related-works section.

## Five replacements, with explicit costs

### N1. A PSO-Based Uneven Dynamic Clustering Multi-Hop Routing Protocol for Wireless Sensor Networks (PUDCRP, 2019)

Ruan and Huang, [DOI](https://doi.org/10.3390/s19081835) · Sensors, SJR 2024 Q1. [Publisher full text](https://www.mdpi.com/1424-8220/19/8/1835). Key sections: 5–7; PDF pp. 13–23.

**Problem/proposal.** Equal geographical grids need not contain equal numbers of sensors. Use PSO to place unequal circular service areas according to the deployment; choose CHs using battery, neighbor count, and sink distance. Smaller near-sink clusters reserve energy for relaying. Route through suitable CHs near the direct line to the sink.

Eq. (19) gives a weighted CH score using `E_i/E0`, normalized neighbor count, and normalized sink proximity.

**Results/limits.** Table 3 reports residual-energy mean 0.3065 J and standard deviation 0.0591 J in one 200-node experiment. However, Section 6 assumes an ideal MAC and excludes control-message energy costs. It uses static terrestrial nodes and radio energy. More search and centralized information are not free under DACO's conditions.

**Decision/use.** Add as a methodological density/distribution comparator, not an acoustic lifetime claim. It is useful precisely because the evaluation boundary is explicit.

### N2. Game-Theory-Based Clustering Scheme for Energy Balancing in Underwater Acoustic Sensor Networks (GTC, 2021)

Xing et al., [DOI](https://doi.org/10.1109/JIOT.2021.3055857) · IEEE Internet of Things Journal, SJR 2024 Q1. [Full author-hosted PDF](https://faculty.cqupt.edu.cn/system/resource/storage/download.jsp?mark=QTM0RDZBMkE0QTJERDFCOEZEMDM2NDZBNUY4NUE1RTgvRTM0QzQwQTEvMTNDNDYz), especially pp. 3–6.

**Problem/proposal.** Every sensor would prefer another sensor to perform expensive CH duties. Model the choice as a game; add incentives to select and rotate a collectively useful CH within nonuniform layers. The sink computes the game.

Eq. (7) starts from `CH utility = remaining energy - CH cost`; a member instead pays its forwarding cost. An incentive changes which choice is attractive.

**Results/limits.** Reported FND is 900 rounds versus 690 for EULC and 484 for LEACH. The prose mislabels ratios as percentage increases: 900 versus 690 is **30.4% later**, not 130% later. Use the round counts. Assumptions include static known locations, reliable symmetric links, and a sink communicating with all nodes.

**My assessment:** incentives are a coordination model, not a proof of global lifetime optimality; mobility and actual signaling costs need separate evaluation.

**Decision/use.** Add with the arithmetic correction and assumptions visible. It supplies an alternative balancing mechanism rather than another unqualified optimizer-win claim.

### N3. Improved energy-balanced algorithm for underwater wireless sensor network based on depth threshold and energy level partition (IEBR, 2019)

Feng et al., [DOI](https://doi.org/10.1186/s13638-019-1533-y) · EURASIP Journal on Wireless Communications and Networking. **SJR 2025 Q2**, independently mirrored; this ranking year differs from the other entries. [Publisher full text](https://link.springer.com/article/10.1186/s13638-019-1533-y), Sections 3.3–5.

**Problem/proposal.** Balancing batteries by repeatedly changing relays can create loops or unreliable long links. Build routes using suitable transmission distances and depth progress, then alternate load among energy-level/ring-sector choices. Constrain delivery rather than minimizing energy alone.

Teaching model: maximize delivered packets subject to battery, link-distance, capacity, and link-quality constraints. The paper explicitly formulates these constraints in Section 3.3.3.

**Results/limits.** It compares lifetime, transmission loss, and throughput across network radius and density, with an approximately 25% lifetime improvement reported in its tested comparisons. Strict depth/distance restrictions can remove a useful detour; relay-state maintenance costs communication. The authors leave spatial extension and dynamic depth thresholds for future work.

**Decision/use.** Add as routing context. It helps explain why DACO's balance score must be checked together with feasible connectivity; it is not a CH-selection baseline.

### N4. An Energy-Efficient Redundant Transmission Control Clustering Approach for Underwater Acoustic Networks (RTC, 2019)

Ahmed et al., [DOI](https://doi.org/10.3390/s19194241) · Sensors, SJR 2024 Q1. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6806349/), Sections 4.4 and 5.1–5.4.

**Problem/proposal.** Similar readings are repeatedly transmitted. Use a region/cluster hierarchy and statistical similarity tests at CHs and region heads; send selected representative information to a mobile sink, with role rotation and sleep scheduling.

The basic teaching rule is `similar(a,b) = 1 if distance(a,b) <= delta`. The complete scheme additionally uses variance-based tests and thresholds.

**Results/explicit cost.** Threshold experiments show energy/transmission reductions, but Section 5.1 warns that more aggressive similarity settings can lose original information. Mobility increases control exchanges and can degrade delivery. A mobile collector and assumptions about correlated, statistically modeled readings are essential.

**My assessment:** fewer packets are not a free gain if DACO must deliver every sensor's information. The stated MAC/simulation configuration also warrants verification before importing numerical results.

**Decision/use.** Add for application-dependent data reduction, replacing FCRA's role. Discuss the information-loss and collector assumptions, rather than presenting RTC as a matched DACO energy baseline.

### N5. Underwater Wireless Sensor Networks: An Energy-Efficient Clustering Routing Protocol Based on Data Fusion and Genetic Algorithms (EECRP, 2021)

Xiao, Huang, and Wang, [DOI](https://doi.org/10.3390/app11010312) · Applied Sciences, SJR 2024 Q2. [Publisher full text](https://www.mdpi.com/2076-3417/11/1/312), Sections 4–8.

**Problem/proposal.** Poor routes and redundant readings waste energy. Choose CHs from energy/location, restrict membership by depth/distance, fuse member data using a trained neural network, and use a modified genetic algorithm to find CH-to-sink paths. The sink trains the network and searches routes.

Teaching model: `outgoing bits = compression factor × incoming bits`; the saving depends on whether the fused output preserves the application's required information.

**Results/cost.** Reported FND is approximately 623 versus 574 rounds for FCMMFO in one experiment. Section 7.4 acknowledges higher computational complexity than basic LEACH variants, and the conclusion explicitly identifies simulation-only validation. Aggregation quality, sink computation, and sending trained parameters are additional assumptions/costs.

**Decision/use.** Add for fusion-plus-routing discussion. It has identifiable burdens and a specified method, but do not attribute all its gain to routing or copy its aggregate “energy efficiency” label without checking the denominator.

## Rejected replacement candidates

### C1. An energy efficient hierarchical routing approach for UWSNs using biology inspired intelligent optimization (CTRGWO-CRP, 2025)

[DOI](https://doi.org/10.1038/s41598-025-21336-4) · Scientific Reports. **Do not add as a replacement.**

The method combines gray-wolf search, cloning, mutation, and opposition-based learning to choose CHs. The intended benefit is better exploration and battery balance. However, its PDF p. 11 says about **60%** of nodes remain alive at round **300**, while Table 4 puts the **first** node death at **331**. Before first death, all nodes should still be alive. Its scenario-2 prose calls 1229 versus 750 a 166% extension; the increase is actually **63.9%**. These conflicts were checked on the rendered page, not inferred from extraction artifacts. A limits paragraph does not resolve them. Reject its numerical claims pending correction.

### C2. A Cluster Sleep-Wake Scheduling Algorithm Based on 3D Topology Control in Underwater Sensor Networks (2019)

[DOI](https://doi.org/10.3390/s19010156) · Sensors. **Do not use as a direct replacement baseline for the present DACO problem.**

Its mechanism is understandable: partition the volume, keep a well-powered working sensor in each unit, sleep redundant sensors, and rotate temporary controllers. The indexed original methods/results describe 300 nodes in a 100 m cube and tests of coverage/connectivity/lifetime. This can save energy by reducing the active sensing set. That differs from serving all live sensors' required data in DACO, especially in sparse deployments. The printed coverage definition also uses an intersection where total covered-volume coverage ordinarily requires a union; clarify the implemented measure before using its quantitative coverage claim. It remains background for duty cycling, not one of the 10 replacements/recommendations.

## What to write in DACO's related-works section

Organize by the unsolved mechanism, not a list of optimizer names:

1. **CH selection and geometry:** ACOCR, DEKCS, and IS-k-means show that residual energy, position, and density already influence clustering. Their limits concern fixed partitions, sparse-node fairness, radio/AUV assumptions, or single-hop operation.
2. **Unequal work and forwarding:** UCPSO and PUDCRP adapt cluster sizes; GTC rotates expensive roles; IEBR constrains relay choices. They motivate evaluating forwarding burden as well as local cluster density.
3. **Information and feasibility:** Two-Tier PSO, RTC, and EECRP save energy partly by changing transmitted information. LLCP manages capacity. QLAR manages link stability with a control-overhead trade-off. These are complementary objectives, not evidence that energy-only optimization solves everything.
4. **Your precise gap:** examine whether a 3D grid-coverage density combined with evaluated relative node depletion and live node-pheromone feedback improves the balance/energy/computation trade-off under a common acoustic and routing model. This review does not prove that combination is novel or universally better.

An example explanatory paragraph, to adapt after checking your final experimental configuration:

> Existing clustering schemes improve energy use through energy-aware CH selection, unequal membership, and role rotation. UCPSO explicitly reduces the local collection burden of CHs involved in inter-cluster forwarding, whereas density-based schemes such as IS-k-means improve cluster geometry and distribute CH duties. These approaches motivate distinguishing node density from the energy burden of a completed routing tree. DACO investigates whether using structural grid density together with evaluated relative depletion can improve this balance. Comparisons must retain equivalent communication, data-delivery, and computation assumptions; gains from an AUV, compression, or sleeping sensors cannot be attributed to CH selection alone.

Avoid claiming that previous studies “ignore density,” “ignore load,” or “have no drawbacks.” Several explicitly address those concepts. Explain which density, which load, which decision, and which experimental condition differ.

## Reading order and how to judge the results

Start with **UCPSO → ACOCR → IS-k-means → LLCP → QLAR**. Then read IEBR, DEKCS, and PUDCRP. Read the compression/fusion papers when deciding whether your application allows data reduction.

For every comparison, record the event being measured, the number of active sources, delivered information, acoustic/RF channel, sink assistance, control traffic, and search budget. Compare energy over equal service windows. If one algorithm has dead or sleeping sensors, lower consumption alone is not evidence of greater efficiency.

The strongest related-works statement has four parts: **the problem, the mechanism, the conditional result, and the cost or unresolved condition**. The cost can be stated by the authors or inferred from an explicit assumption; it must not be invented merely to make DACO look better.

## Source and ranking notes

The local PDFs were read through text extraction; the scanned underwater-energy survey required Windows OCR. Methods/results/limitations were checked, and tables underlying exclusions were rendered for visual inspection. This is a critical literature reading, **not independent reproduction of the experiments**. The five held papers have deliberately limited, source-labeled summaries.

The additional-paper quartiles remain journal-level SJR ratings, not article quality scores or JCR labels. IEEE Access, IEEE Internet of Things Journal, IEEE Sensors Journal, Sensors, and JMSE use the 2024 evidence recorded in [the catalog](README.md). Applied Sciences is Q2 in the [SCImago 2024 ranking table](https://www.scimagojr.com/journalrank.php?country=&min=3&min_type=cd&ord=desc&order=titem&year=2024). IEBR's journal is Q2 in the **2025** SJR edition according to this [category-by-category mirror](https://scienceaijournal.com/journals/eurasip-journal-on-wireless-communications-and-networking-1687-1472); this is disclosed rather than mislabeling it 2024. The primary ranking profile was not accessible, so retain that provenance if strict institutional quartile verification is required.

The revised ten-paper references are in [recommendations_daco.bib](recommendations_daco.bib); earlier recommendations are preserved in [recommendations_daco_previous.bib](recommendations_daco_previous.bib). Public manuscripts successfully downloaded for this review are retained in [sources](sources/). Other reviewed primary full texts are linked at their original repositories above.
