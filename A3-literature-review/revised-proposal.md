# Revised Project Proposal

**Original A1 title:** Impact of Traffic Demand on LEO NTN Performance Using SNS-3  
**Revised A3 title:** Performance Evaluation of 3GPP NR-NTN 2-Step Random Access under LEO Satellite Conditions  
**Student:** M11502215 / Lucy

## 1. Original A1 Baseline

The original A1 proposal investigated how traffic demand affects service performance in an SNS-3 transparent LEO satellite scenario. Its central question was how much offered downlink traffic is served when total load or the spatial distribution of demand changes.

The proposed A1 system contained moving LEO satellites, a gateway, Earth-fixed geographical cells, fixed user terminals, and Poisson packet arrivals. Demand was defined per UT and aggregated per cell. The intended experiments varied total offered load and per-cell demand ratios. The primary metric was Demand Satisfaction Ratio (DSR), supported by throughput, packet-delivery ratio, and packet delay.

This document uses that actual A1 proposal—not a later multi-beam RA thesis direction—as the formal comparison baseline.

## 2. Revision Summary

| Category | Original A1: SNS-3 Traffic Demand | Revised A3: NR-NTN Random Access | Reason for change |
| --- | --- | --- | --- |
| Research question | How much cell traffic demand is served? | How do UE load and propagation delay affect RA? | Both papers show that access contention, not downlink capacity, limits dense IoT/LEO users |
| Network direction | Forward-link/downlink service | Uplink initial-access abstraction | RA contention occurs during UE access |
| Simulator plan | SNS-3 reference scenario | Standalone ns-3 event model | Local checkout lacks an installed SNS-3/NR 2-Step implementation |
| Satellite behavior | Moving LEO constellation from TLE | One transparent satellite with fixed geometry | Isolate contention and timing |
| Spatial model | 72 Earth-fixed cells, 360 UTs planned | One beam and one associated SSB | Remove spatial-allocation confounders |
| Traffic model | Poisson packets, cell-level demand | UE population swept from tens to thousands of activations | P1 evaluates RA versus UE population \(M\) (up to 1,000); P2 uses 1,000 devices/cell |
| Access/resource model | Resource mechanism pending SNS-3 audit | Fixed abstract contention choices per RA occasion, with retries and backoff | P1 keeps the RA resource rate fixed (\(R \times J \times C / T = 11.2\)) and uses \(N_{\mathrm{PTmax}} = 5\) with a backoff window |
| Main metrics | DSR, throughput, PDR, packet delay | UE success, collision probability, attempts, RA delay | P1 reports RA success and delay; P2 separates collision from decoding success |
| Validation | Packet-path functional validation planned | Simulation checked against an analytical collision formula | P1 validates its analytical model against simulation |
| Output | Reproducible traffic-demand scenario | Reproducible fixed-resource RA baseline | Establish a control case before multi-beam allocation (P2) |

## 3. Revised Problem Statement

Multiple UEs attempting random access share a finite set of contention resources. When many UEs become active together, selecting the same resource causes collisions and retries. In a transparent LEO NTN, the satellite path also increases the time between a UE transmission and the network response.

The revised project asks:

1. How does the number of simultaneously contending UEs affect collision probability, UE-based success probability, attempts, and RA completion delay?
2. How does configured one-way UE-to-ground-gNB propagation delay affect RA completion time when contention and other parameters are controlled?

The modeled end-to-end interval is `UE activation -> simplified MsgA transmission -> MsgB outcome -> RA completion`. It excludes application traffic, full 5GC signaling, and user-plane throughput.

## 4. Revised System and Method

The planned architecture contains multiple stationary UEs, one serving beam, one transparent LEO satellite, and one ground gateway/gNB. The simulator will use ns-3 event scheduling and random streams but does not claim a complete NR PHY/MAC/RRC implementation.

The simplified procedure is:

1. A UE activates and waits for an eligible modeled RA occasion.
2. It selects one valid abstract contention choice representing an RO/preamble and associated MsgA resource.
3. Choices selected by multiple UEs in the same occasion collide.
4. A unique choice succeeds after one forward propagation delay, processing time, and one reverse propagation delay.
5. A collided UE backs off and retries until the maximum-attempt limit.

Metrics follow the reviewed papers: UE-based RA success probability, per-transmission collision probability, number of attempts, and RA completion delay (activation to MsgB outcome).

## 5. Planned Experiments

| Experiment | Purpose | Main variable | Literature basis |
| --- | --- | --- | --- |
| Validation | Check the collision implementation | UE count with a single attempt | One-shot formula in study note §2.3; P1's analysis-versus-simulation approach |
| RA load | Measure contention under fixed resources | UE population, with retries and backoff | P1 (success vs. \(M\)); P2 (1,000 devices/cell) |
| NTN delay | Measure the effect of propagation on RA completion | Configured one-way delay | 3GPP TR 38.821 NTN timing; gap left by P1 and P2 |

Each setting will record topology, traffic model, PHY/MAC parameters, simulation time, and seeds, matching the reproduction checklist used in the study note (§4.1).

## 6. Why the Revision Was Necessary

**What the literature changed.** Both papers frame dense access as a contention problem: P1 shows that RA success and delay depend on how contention resources and retries are configured, and P2 shows that LEO access is limited by scarce beams and resource collisions. The A1 question (downlink demand satisfaction) does not capture this initial-access bottleneck. Neither paper models 2-Step RA completion delay under NTN propagation, so that became the revised focus.

**Practical reasons.** The original A1 required constellation motion, coverage determination, packet paths, downlink resource management, Poisson traffic calibration, and per-cell demand accounting before its main experiments could be interpreted. That scope is too broad to validate step by step.

The local ns-3 audit also found no installed 5G-LENA, SNS-3, or verified NR 2-Step RA implementation. Modifying LTE 4-Step RA and presenting it as NR 2-Step RA would be technically incorrect. A small event-driven abstraction provides explicit assumptions, analytical validation, deterministic seeds, and inspectable metrics without overstating standards compliance.

## 7. Postponed A1 and Thesis Components

The following items are postponed rather than abandoned:

- SNS-3 constellation integration and TLE-driven satellite motion.
- Earth-fixed cells and spatially non-uniform traffic demand.
- Poisson packet traffic and Demand Satisfaction Ratio.
- Forward-link packet delivery, throughput, PDR, and application delay.
- Dynamic beam hopping, SSB-to-RO mapping, and preamble allocation.
- Multi-beam interference, power allocation, fairness, and utilization.
- Detailed PRACH detection, MsgA decoding, MsgB loss, and fallbackRAR/Msg3.
- Handover, overlapping coverage, timing advance, and geometry-derived scheduling offsets.

## 8. Relationship to Future Research

The revised proposal does not replace the broader traffic-demand or dynamic-allocation thesis direction. It plans a fixed-resource control case. Future multi-beam or traffic-aware policies can reuse the same UE-level success, transmission-level collision, attempt, and completion-delay definitions and compare against this baseline under controlled seeds and traffic conditions.

## References

[1] M11502215 / Lucy, “Impact of Traffic Demand on LEO NTN Performance Using SNS-3,” A1 Project Proposal, 2026. Source: [`../A1-background/Proposal.md`](../A1-background/Proposal.md).

[2] T.-A. Lin and R.-G. Cheng, “Analytical Modeling and Performance Evaluation of Beam-Based Random Access Protocol for 5G Beamforming Networks,” *IEEE Internet of Things Journal*, vol. 10, no. 24, pp. 22246–22255, Dec. 2023, doi: [10.1109/JIOT.2023.3305547](https://doi.org/10.1109/JIOT.2023.3305547).

[3] S. Jeon, S. Kim, G. Im, and Y.-S. Jeon, “Beam-Hopping Pattern Design for Grant-Free Random Access in LEO Satellite Communications,” *IEEE Transactions on Wireless Communications*, vol. 25, pp. 8246–8259, 2026, doi: [10.1109/TWC.2025.3636684](https://doi.org/10.1109/TWC.2025.3636684).
