# A1 Project Proposal (Initial Draft)

## Basic Information

| Item | Content |
| --- | --- |
| Project Title | Impact of Traffic Demand on LEO NTN Performance Using SNS-3 |
| Student ID / Name | M11502215 / Lucy |
| Git Repository | [MWN-2026-M11502215-Lucy](https://github.com/yuru1231/MWN-2026-M11502215-Lucy) |
| Proposal Approval Date | TBD |

# A1. Project Summary

## 1. Problem to be Solved

Low Earth Orbit Non-Terrestrial Networks (LEO NTN) provide ground communication services through continuously moving satellites. As satellite positions change, their coverage relationships and the communication conditions between satellites and ground terminals may also vary over time.

Existing research has already explored Traffic-Aware Beam Hopping, Power Allocation, and Demand Forecasting; therefore, this project does not claim to be the first to study Traffic Demand, nor does it aim to propose a new resource allocation algorithm.

This project focuses on:

> Given the Traffic Demand of a Cell, in a clearly defined and reproducible Transparent LEO NTN scenario, how much of that Demand is actually served? What is the speed and quality of service? When Traffic Load or Spatial Traffic Distribution changes, does this degree of demand satisfaction change accordingly?

## 2. Key Challenges

**Challenge 1: Footprint / Coverage Area Changes Across Space and Time**

LEO satellites move at high speed, and the Footprint and Beam pointing continuously change, so the time window and service conditions under which a ground Cell can actually be served are not fixed — the same Cell may be served by different satellites/Beams at different times, or may temporarily fall outside any coverage area.

**Challenge 2: Link Conditions Change Dynamically with Satellite Geometry**

The distance and elevation angle between the satellite and the ground continuously change as the satellite moves, which in turn affects propagation delay and link quality; even if Traffic Demand remains constant, geometry changes alone can cause service performance to fluctuate.

**Challenge 3: Interaction Between Spatiotemporal Non-Uniformity of Ground Demand and Limited Service Capacity**

Ground Traffic Demand itself has spatial non-uniformity, while the NTN's service capacity is simultaneously constrained by the coverage and link dynamics described in Challenges 1 and 2. This project's core question — how Demand Satisfaction changes with Traffic Load and Spatial Distribution — is meaningful precisely under this NTN-specific spatiotemporal coupling constraint, rather than being an abstract queueing-theory problem.

## 3. Proposed Method

This project will use SNS-3 to build a set of LEO NTN reference scenarios based on a Transparent Satellite architecture, including ground-side Traffic Sources, a Gateway (GW), moving LEO Satellites, fixed geographical Cells, and User Terminals (UTs) at fixed positions.

Initially, only the Forward Link (Downlink) will be studied. Transparent Satellite is chosen as the system architecture.

Traffic Generation adopts a Poisson Packet Arrival Model with fixed packet size. Demand is first defined at the UT level, then aggregated by fixed geographical Cell; the UT-to-Cell Aggregation is a modeling design of this study and does not claim to directly replicate any implementation in the literature.

After establishing the reference scenario and confirming its actual transmission behavior (**Experiment Scenario 1 — Reference Scenario Establishment and Functional Validation**), two controlled experiments are conducted:

- **Experiment Scenario 2 — Traffic Load Variation:** Fix the spatial distribution ratio of demand, vary the total Offered Load.
- **Experiment Scenario 3 — Spatial Traffic Distribution:** Fix the total expected Offered Load and UT positions, vary the demand ratio per Cell.

## 4. Expected Outcomes

The project is expected to produce a reproducible LEO NTN reference scenario, establish a demand configuration method that allows adjusting Traffic Load and Spatial Distribution, and use the Demand Satisfaction Ratio (DSR) as the primary metric, together with Throughput, Delay, and PDR, to produce performance measurements of the degree to which demand is served.

The outcomes will include experiment settings, measurement definitions, comparative charts, functional validation records, and model limitations, for use in subsequent NTN simulation research.

# A2. System Architecture

## 1. System Assumptions

| Item | This Study's Setting | Basis and Boundary |
| --- | --- | --- |
| Satellite System | LEO satellites | Starlink 1584 |
| Payload | Transparent Satellite | |
| Traffic Direction | Forward Link / DL | |
| Ground Terminal | Fixed UT | |
| Geographic Region | Earth-fixed geographical cells | |
| Demand Definition | UT-level Demand, aggregated by Cell | |
| Traffic Model | Poisson Packet Arrival, fixed Packet Size | |

## 2. Environment

### Network Architecture

The expected Forward-Link data path of this study is:

```
Ground-side Traffic Source
        │
        ▼
   Gateway (GW)
        │  Feeder Link
        ▼
  Moving LEO Satellite (Transparent Payload)
        │  Service Link
        ▼
 ┌──────────┬──────────┬──────────┐
 │  Cell 1  │  Cell 2  │  Cell C  │
 │ Fixed UTs│ Fixed UTs│ Fixed UTs│
 └──────────┴──────────┴──────────┘
```

Cell is the geographic and demand analysis unit; the links and packet paths shown in the diagram are still pending implementation confirmation. 5GC or gNB are not discussed at this stage, nor is ISL required.

### Satellite Geometry

The positions of UTs and geographic Cells are fixed within a single experiment, while the satellite moves along its orbit.

The satellite orbit is configured using TLE files; since satellite position, propagation distance, Doppler, and other link conditions can all be pre-computed from the TLE, this study uses this to pre-compute the satellite position, Footprint range, and Serving Cell correspondence at each time step, as a concrete method for addressing Challenge 1 (Footprint dynamics) and Challenge 2 (link geometry dynamics) — satellite geometry is a known quantity that can be pre-computed, rather than random noise, allowing subsequent analysis to separate performance changes caused by geometry from those caused by Traffic Demand.

The simulation region, Elevation Threshold, coverage determination, and the actual configuration of service relationships are left to be determined later.

### Traffic Demand Model

Let $\lambda_i$ be the average packet arrival rate of UT $i$, in packets/s; let $L$ be the fixed packet size, in bytes.

For an observation interval of length $\Delta t$, this study adopts:

$$N_i(\Delta t) \sim \operatorname{Poisson}(\lambda_i \Delta t)$$

The average Offered Traffic Rate of a UT is defined as:

$$R_i^{\text{offered}} = 8 L \lambda_i$$

The total Offered Traffic Rate of Cell $c$ is defined as:

$$R_c^{\text{offered}} = \sum_{i \in \mathcal{T}_c} R_i^{\text{offered}}$$

where $\mathcal{T}_c$ is the set of UTs located in Cell $c$.

The Poisson Arrival and fixed packet size follow Mu et al. [2]; assigning the model to UTs and then aggregating to Cells, together with the notation and formulas above, are operational definitions proposed by this study.

Initially, the average arrival rate is fixed within a single experiment, and traffic is only adjusted between experiments. Poisson is not claimed to be a complete Video, Voice, or Web Traffic Model.

## 3. Formal Definition of the Reference Scenario and Resource Management

This section replaces all previous vague references to an "Existing SNS-3 baseline."

| Term | Definition | Notes |
| --- | --- | --- |
| Simulation Framework | SNS-3 / ns-3 simulation framework | The simulation tool selected for this study. The actual version, components, and available features are pending an architecture inventory |
| Reference Scenario | The LEO NTN reference scenario established by this study | A documented set of system model, Traffic Model, parameters, and observation conditions, used as a common reference for subsequent controlled experiments |
| Resource Management Mechanism | The actual resource management mechanism adopted in the reference scenario | Its configuration, resource-sharing method, and behavior will be confirmed and documented after the SNS-3 architecture inventory; no algorithm name is specified at this time |

The reference scenario is the comparison condition this study aims to establish; it does not claim that SNS-3 already includes a built-in example that fully meets the requirements. It is also not equivalent to a baseline scenario in the literature. If reproducing a paper's curve is needed in the future, the model and parameters must be separately confirmed for comparability.

## 4. Input Parameters

| Parameter | Description | Status |
| --- | --- | --- |
| Constellation / Orbit | TLE of SNS-3's built-in Starlink scenario (1584 satellites) | Reusing SNS-3's example scenario |
| Simulation Region | ROI: Taiwan | Boundary coordinates pending confirmation |
| Earth-fixed Cells | 72 Cells | Splitting method (grid / hexagon, etc.) and per-cell size pending |
| UT Configuration | 5 UTs per Cell, 360 UTs total, fixed positions | Position distribution method (random / uniform) pending |
| Packet Size $L$ | Fixed packet size | TBD |
| Arrival Rate $\lambda_i$ | Average packet arrival rate per UT | Experiment control parameter |
| Traffic Load | Total expected Offered Load | Experiment A |
| Spatial Distribution | Per-Cell demand ratio | Experiment B |
| Channel Configuration | Channel and related model settings | TBD |
| Resource Management | Actual mechanism of the reference scenario | Pending SNS-3 inventory |
| Simulation Duration / RNG | Simulation time, random seed settings | TBD |

## 5. Output Parameters

| Metric | Measurement Content |
| --- | --- |
| Actual Offered Traffic | Traffic actually generated within the observation interval |
| Demand Satisfaction Ratio (DSR) | Within a specified observation deadline, the ratio of successfully delivered payload bytes to the Actual Offered Traffic, computed per Cell (primary PM, defined in §A3) |
| Throughput | Amount of data successfully received per unit time |
| End-to-End Delay | Time difference between send and receive for matched packets (covers only successfully delivered packets; must be interpreted together with DSR/PDR) |
| PDR | Ratio of successfully received packets to sent packets |
| Per-cell Results | Performance results aggregated by fixed geographic Cell |

> Measurement endpoints are not yet finalized. For example, Demirci et al. [4] measure One-way Delay from GW LLC to UT LLC, which cannot be directly compared as Application-to-Application Delay.

## 6. Proposed Modules

The table below represents the logical functions required for the research; it does not imply re-developing C++ modules of the same name.

| Function | Work Content |
| --- | --- |
| Topology & Geometry | Build the satellite, GW, UT, and geographic Cell scenario required for the research |
| Communication & Channel | Complete satellite communication according to the confirmed simulation mechanism |
| Traffic Demand | Configure UT Arrival Rate and aggregate Cell Demand |
| Resource Management | Identify and document the mechanism actually used in the reference scenario |
| Performance Measurement | Obtain packet transmission, reception, and performance data |
| Experiment & Analysis | Perform controlled comparisons and analyze results |

This version does not specify SNS-3 classes, functions, installation order, or Trace interfaces.

# A3. Expected Deliverables and Validation

## Validation Method

This study handles three separate matters:

| Task | Question to Answer |
| --- | --- |
| Scenario Establishment | Does the system configuration match this study's definition? |
| Functional Validation | Are packets actually sent and received via the expected path? |
| Model Validation / External Comparison | Is the simulation result consistent with an applicable reference model or literature result? |

This phase first completes reference scenario establishment and functional validation; the specific target and method for external comparison are pending confirmation of comparable reference data.

Although Demirci et al. [4] also use SNS-3, they adopt a Regenerative Payload, ISL, Self-similar Traffic, and dynamic Beam Hopping. Therefore, their results cannot be directly treated as a reproduction target for this study's Transparent/Poisson scenario.

## Experiment Scenario 1 — Reference Scenario Establishment and Functional Validation

- **Experiment Design:** Build the selected LEO NTN architecture and a fixed Poisson Traffic setting, record system parameters, and confirm the expected communication path and actual packet behavior.
- **Experiment Purpose:** Before changing Traffic Demand, first establish a repeatable reference scenario with clearly defined measurements; also gradually increase the Offered Load for a single Cell / small number of UTs to find the critical point at which DSR starts to drop, as the basis for designing the load range of Scenario 2 and 3.
- **Expected Evidence:** Configuration records, actual packet send/receive data, basic performance results, a single-Cell DSR–Load calibration curve, and confirmed functionality and limitations.

> This Scenario is internal baseline establishment and validation; it is not equivalent to completing a reproduction of a literature curve.

## Experiment Scenario 2 — Traffic Load Variation

- **Independent Variable:** Total Expected Offered Load.
- **Control Conditions:** Fixed UT positions, per-Cell demand ratio, Satellite Configuration, Traffic Model, and the resource management mechanism adopted by the reference scenario.
- **Experiment Purpose:** Under a fixed spatial distribution, observe how DSR, Throughput, Delay, and PDR change as load changes.

Mu et al. [2] evaluate their method under different Traffic Demand Rates, supporting load variation as a research variable; this study's control method and measurement endpoints are defined separately.

## Experiment Scenario 3 — Spatial Traffic Distribution

- **Research Question:** Under the same Total Offered Load, does a different Spatial Traffic Distribution change the Demand Satisfaction and overall network performance of each Cell?
- **Independent Variable:** The Offered Traffic ratio of each Earth-fixed Cell.
- **Control Conditions:** Keep the total expected Offered Load, UT positions, satellite scenario, Traffic Model, and resource management mechanism unchanged.
- **Experiment Purpose:** Examine whether, with the same total demand but different geographic distribution, the overall and per-Cell DSR, Throughput, Delay, and PDR show differences.

Zhao et al. [3] examine the relationship between non-uniform geographic demand and resource allocation, providing the research motivation for this experiment. This experiment does not assume that Cells/Beams must share a limited resource for it to be valid: if each Cell has its own fixed capacity, concentrated demand may still cause a single Cell's demand to exceed its own service capacity, lowering DSR; if a shared resource exists across Cells, additional interaction effects may also occur. Which case applies is left to be explained after obtaining the results and comparing them against the actual mechanism of SNS-3; it is not assumed as a precondition for this experiment.

> The range of Total Offered Load must first be determined based on the single-Cell DSR–Load critical point calibrated in Experiment Scenario 1; otherwise, if the load range is far below any Cell's service capacity, DSR will approach 100% under all Spatial Distributions, and the experiment will not be able to detect any difference.

### Definition of Demand Satisfaction Ratio (DSR)

For Cell $c$, within the observation period, define:

$$\mathrm{DSR}_c = \frac{B_c^{\text{delivered}}}{B_c^{\text{offered}}} \times 100\%$$

where $B_c^{\text{offered}}$ is the actual payload data volume generated by the UTs in that Cell, and $B_c^{\text{delivered}}$ is the portion of that data successfully delivered to the destination UT within the specified observation deadline. DSR is conceptually based on the Traffic Satisfaction Rate in Mu et al. [2], but its numerator is the actually delivered data volume rather than the Effective Capacity from an analytical model; it is a packet-delivery-based metric proposed by this study. The method for selecting the observation deadline is to be confirmed by the Task 1 pre-validation.

## Statistical Evaluation

Each scenario is planned to be repeated over multiple Random Seeds, reporting the mean and confidence interval. At least 10 runs and a 95% Confidence Interval are initially adopted as planning targets; the final number of runs and statistical method are still to be determined.

Demirci et al. [4] adopt 20 different Seeds and report a 95% Confidence Interval for some results, which can serve as a reference for statistical presentation, but does not mean this study must replicate the same sample size.

The configured average load of Poisson Traffic and the actual traffic generated in a single run are not necessarily the same, so the Actual Offered Traffic must also be recorded for every experiment.

## Expected Deliverables

| Deliverable | Content |
| --- | --- |
| D1. Reference Scenario | Fully documented LEO NTN simulation configuration |
| D2. Functional Validation Record | Confirmation results of expected vs. actual packet paths |
| D3. Traffic Scenarios | Controlled experiment settings for load and geographic distribution |
| D4. Performance Results | Throughput, Delay, PDR, and related charts |
| D5. Analysis Report | Comparative analysis, assumptions, and limitations |
| D6. Reproducibility Records | Configuration, random seed information, and experiment outputs |

# A4. Cross-Validation

No formal experiment results have been produced at this stage, so only the questions to be checked and the evidence to be used are listed here; conclusions remain Pending.

| Validation Question | Planned Evidence | Conclusion |
| --- | --- | --- |
| Does the System Model match the research scope? | Records of architecture, geometry, UT, and Traffic settings | Pending |
| Has satellite packet transmission actually been completed? | Traceable Tx/Rx and transmission path records | Pending |
| Is the reference scenario reproducible? | Same configuration and results across multiple runs | Pending |
| Are Traffic Load and Spatial Distribution independently controlled? | Parameters and Actual Offered Traffic for each experiment | Pending |
| Can performance differences be reasonably attributed to the research variables? | Performance comparison and variance analysis under the same observation conditions | Pending |
| Is there a basis for external comparison? | Assumptions, parameters, and measurement definitions of compatible literature or reference models | Pending |
| Can this serve as a foundation for subsequent NTN research? | Reproducible configuration, measurement methods, validation records, and known limitations | Pending |

> A4 should ultimately be answered based on evidence, not by directly claiming the simulator has been fully validated just because code was completed or charts were produced.

# References

| No. | Reference | Scope of Use in This Proposal |
| --- | --- | --- |
| [1] | Fu et al., 2023 — *Satellite and Terrestrial Network Convergence on the Way Toward 6G* | NTN and Transparent Satellite architecture |
| [2] | Mu et al., 2023 — *Dynamic Beam Hopping for LEO Satellites with Differentiated Traffic Demands* | LEO Downlink, geographic Cells, Poisson Arrival, Differentiated Demand |
| [3] | Zhao et al., 2025 — *Demand-Aware Beam Hopping and Power Allocation for Load Balancing in Digital Twin Empowered LEO Satellite Networks* | Non-uniform spatial demand, Cell Demand, and limited resources |
| [4] | Demirci et al., 2026 — *The Impact of Demand Forecasting on Delay and Jitter* | SNS-3 cross-layer measurement method, Cell-level Demand, and statistical experiments |
