# A3 — Literature Review

**Project:** Performance Evaluation of 3GPP NR-NTN 2-Step Random Access under LEO Satellite Conditions
**Student:** M11502215 / Lucy
**Due:** 2026-11-10 23:59 (Asia/Taipei) · **Presentation:** 2026-11-17 (10 min)

A3 is a literature review only. No experiment is required. I review two IEEE papers on random access (RA) in beamforming and LEO satellite networks, extract the settings needed to reproduce their results, and revise my A1 proposal based on what I read.

## Assignment Requirements and Where They Are Answered

| # | Requirement (from the TA's 11/09 reminder) | Where | Status |
| :- | :--- | :--- | :--- |
| 1 | Review 1–3 IEEE papers on the topic | [study-note.md](study-note.md), §2–§3 (two papers) | Done |
| 1a | Per paper: problem, importance, challenges | §2.1 (Paper 1), §3.1 (Paper 2) | Done |
| 1b | Per paper: system model (environment, inputs, outputs, performance metrics) | §2.2–§2.3 (Paper 1), §3.2 (Paper 2) | Done |
| 1c | Per paper: key results and reproduction settings (topology, traffic model, PHY/MAC parameters, simulation time, seeds) | §2.4, §3.4–§3.5, and the reproduction summary in §4.1 | Done; P1 simulation time and seeds still `UNAVAILABLE` |
| 2 | Revise the A1 proposal; state what changed and why | [revised-proposal.md](revised-proposal.md) (§2 lists each change and the paper behind it; §6 explains why) | Done |
| 3 | Slides | `slides/` | **TODO** |
| 4 | PowerPoint Speaker Coach feedback | [rehearsal-feedback.md](rehearsal-feedback.md) | **TODO** |
| 5 | Accessible link to the rehearsal recording | [rehearsal-feedback.md](rehearsal-feedback.md) | **TODO** |

## Reviewed Papers

| | Paper | Venue | Why it is relevant |
| :- | :--- | :--- | :--- |
| P1 | T.-A. Lin and R.-G. Cheng, "Analytical Modeling and Performance Evaluation of Beam-Based Random Access Protocol for 5G Beamforming Networks" | *IEEE Internet of Things Journal*, vol. 10, no. 24, 2023, doi:[10.1109/JIOT.2023.3305547](https://doi.org/10.1109/JIOT.2023.3305547) | Beam/RO-mapped contention, retries, and analytical validation of RA |
| P2 | S. Jeon, S. Kim, G. Im, and Y.-S. Jeon, "Beam-Hopping Pattern Design for Grant-Free Random Access in LEO Satellite Communications" | *IEEE Trans. Wireless Communications*, vol. 25, 2026, doi:[10.1109/TWC.2025.3636684](https://doi.org/10.1109/TWC.2025.3636684) ([arXiv](https://arxiv.org/abs/2508.03391)) | LEO resource scarcity, dense access (1,000 devices/cell), and uneven demand |

Supporting standards (TS 38.300/38.321/38.213/38.211/38.331, TR 38.821) are listed in the study note references.

## Key Takeaways

- **P1** shows that, under beamforming, the way beams map to RA occasions changes collision and retry behavior. Its RA patterns share the same resource rate (R×J×C/T = 11.2) with N_PTmax = 5 and W_BO = 120, at M = 1000 UEs. It also motivates checking a simulator against an analytical collision model.
- **P2** shows that LEO access is limited by the number of simultaneously active beams and by uneven traffic. The reported setup is 80 cells, 6 active beams, 600 km altitude, 1,000 devices per cell, activation probability 0.01, and 20 resource blocks.
- **Gap:** Neither paper offers a small, inspectable ns-3 model that combines RA contention and retries with transparent-NTN propagation delay. This gap drives the revised proposal.

## What Changed from A1 (Summary)

| | A1 proposal | Revised after A3 |
| :--- | :--- | :--- |
| Question | How much downlink traffic demand is served (SNS-3)? | How do UE load and NTN propagation delay affect 2-Step RA? |
| Direction | Downlink service | Uplink initial access |
| Simulator | SNS-3 reference scenario | Standalone ns-3 event model (SNS-3 and NR 2-Step RA are not available locally) |
| Metrics | DSR, throughput, PDR, packet delay | RA success, collision probability, attempts, RA completion delay |

The full reasoning is in [revised-proposal.md](revised-proposal.md) §2 and §6.

## Notes and Known Gaps

- **P1 settings come from a meeting deck.** P1's RA patterns, retry limit, and backoff window were recorded from the supplied meeting deck summarizing the paper (labeled `DECK`). The simulation horizon and seed policy are not stated there and remain `UNAVAILABLE`. Cross-check them against the full text before exact replication.
- **Paper choice and path.** For the Basic path, the TA asks students to start from the assigned 802.11e paper. These two RA papers fit the Advanced (self-chosen NTN) topic. If the Basic path applies, the 802.11e paper still needs to be added.
- **No experiments in A3.** Per the TA's instructions, this folder contains only the review, the revised proposal, and the presentation material.

## Directory Structure

```text
A3-literature-review/
├── README.md                 this file
├── study-note.md             literature review of P1 and P2
├── revised-proposal.md       revised A1 proposal: what changed and why
├── rehearsal-feedback.md     Speaker Coach feedback and recording link (TODO)
└── slides/                   presentation slides (TODO)
```
