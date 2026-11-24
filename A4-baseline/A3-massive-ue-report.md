# A3 Massive-UE NR-NTN Random Access Extension

**Project:** Performance Evaluation of 3GPP NR-NTN 2-Step Random Access under LEO Satellite Conditions  
**Student:** M11502215 / Lucy  
**Execution date:** 2026-11-08 (Asia/Taipei)

## 1. Objective and Scope

This extension evaluates massive activation load, abstract contention capacity, RO periodicity, and transparent-NTN delay using the existing validated ns-3 event model. The legacy analytical validation and original results remain unchanged in [`A3.md`](A3.md) and are archived under [`../results/legacy/a3-baseline-2026-11-08/`](../results/legacy/a3-baseline-2026-11-08/).

The modeled end-to-end interval is `UE activation -> simplified MsgA attempt(s) -> MsgB outcome -> RA success or attempt-limit failure`. This is not a full NR PHY/MAC/RRC stack, and the resource values are controlled abstractions rather than claims of formal 3GPP-compliant PRACH configurations.

## 2. Implementation Extension

The simulator at [`../../ns-3-dev/scratch/a3-ntn-ra/ntn-ra-sim.cc`](../../ns-3-dev/scratch/a3-ntn-ra/ntn-ra-sim.cc) now supports:

- `ueCount` verified at 10,000 UEs;
- `arrivalModel=synchronized|uniform` and `arrivalWindowMs`;
- configurable `raResources`, `roPeriodMs`, `backoffMaxMs`, and `maxAttempts`;
- a waiting-UE queue instead of scanning every UE record at every RO;
- first/last attempt times, mean/P95 access delay, and mean/P95 absolute completion time;
- legacy command aliases and the original first 23 summary CSV fields;
- retransmission eligibility at the first RO strictly after response completion and backoff;
- separate offered, activated, not-activated, successful, failed, and unfinished counts.

At each RO, eligible UEs independently select one of the configured abstract contention choices. Every transmission in a choice selected by multiple UEs is marked collided. A noncolliding attempt succeeds after

\[
t_{\mathrm{outcome}}=t_{\mathrm{attempt}}+2d+t_p,
\]

where \(d\) is the configured one-way UE-to-ground-gNB delay through the transparent satellite and \(t_p=2\) ms is abstract processing time. Collided UEs resolve the failed outcome, draw uniform backoff, and select a strictly future RO unless the four-attempt limit has been reached.

## 3. Experiment Configuration and Provenance

All numerical values in this extension are `ASSUMPTION`. 3GPP specifications provide procedural context, but these values are not presented as normative configurations.

| Parameter | Exp. 1 | Exp. 2A | Exp. 2B | Exp. 3 |
| --- | --- | --- | --- | --- |
| UE count | 1,000; 3,000; 5,000; 10,000 | 5,000 | 5,000 | 3,000 |
| Arrival model/window | Uniform / 1,000 ms | Same | Same | Same |
| Choices per RO | 48 | 32; 48; 64 | 48 | 48 |
| RO period | 20 ms | 20 ms | 10; 20; 40 ms | 20 ms |
| One-way delay | 8 ms | 8 ms | 8 ms | 4; 8; 12; 16; 20 ms |
| Backoff / attempts | Uniform 0–80 ms / 4 | Same | Same | Same |
| Horizon / processing | 15 s / 2 ms | Same | Same | Same |
| RNG | Seed 20261108; runs 1–30 | Same | Same | Same |
| Noncolliding PHY | Error-free | Same | Same | Same |

The formal matrix contains 450 independent ns-3 runs. Experiment 0 remains the separate legacy one-shot analytical collision validation and is not mixed with retry results.

## 4. Metrics and Statistical Method

\[
P_{\mathrm{success}}=\frac{N_{\mathrm{successful\ UEs}}}{N_{\mathrm{activated\ UEs}}},
\qquad
P_{\mathrm{collision}}=\frac{N_{\mathrm{collided\ transmissions}}}{N_{\mathrm{preamble\ transmissions}}}.
\]

Access delay is \(t_{\mathrm{completion}}-t_{\mathrm{activation}}\) and is reported only for successful UEs. Failed and unfinished counts are reported separately. Tables report the mean of 30 run-level statistics and a normal-approximation 95% confidence-interval half-width, \(1.96s/\sqrt{30}\). The empirical CDF pools successful-UE access-delay samples as a descriptive distribution; it is not used as the independent-run CI estimator.

## 5. Measured Results

### 5.1 Experiment 1 — Massive UE Load

| UEs | Success ± CI | Collision ± CI | Mean delay ± CI (ms) | P95 delay ± CI (ms) | Mean attempts ± CI | Failed UEs ± CI |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.9161 ± 0.0049 | 0.5362 ± 0.0076 | 81.35 ± 1.23 | 221.10 ± 2.66 | 1.978 ± 0.023 | 83.9 ± 4.9 |
| 3,000 | 0.1103 ± 0.0021 | 0.9713 ± 0.0006 | 139.21 ± 1.35 | 291.03 ± 1.98 | 3.839 ± 0.004 | 2,669.2 ± 6.2 |
| 5,000 | 0.0329 ± 0.0009 | 0.9917 ± 0.0002 | 177.32 ± 3.25 | 310.73 ± 1.99 | 3.964 ± 0.002 | 4,835.7 ± 4.4 |
| 10,000 | 0.0086 ± 0.0003 | 0.9979 ± 0.0001 | 233.09 ± 4.16 | 321.93 ± 1.84 | 3.995 ± 0.000 | 9,914.3 ± 2.7 |

With fixed 48 choices every 20 ms, offered load outgrows capacity. Success collapses and almost every transmission collides at 10,000 UEs. Delay is conditional on success and must not be interpreted without the failure count.

![Massive UE load results](../results/massive/figures/figure_massive_ue_load.png)

### 5.2 Experiment 2A — Contention Capacity

| Choices/RO | Success ± CI | Collision ± CI | Mean delay ± CI (ms) | P95 delay ± CI (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 0.0143 ± 0.0007 | 0.9964 ± 0.0002 | 214.27 ± 4.22 | 319.83 ± 2.14 |
| 48 | 0.0329 ± 0.0009 | 0.9917 ± 0.0002 | 177.32 ± 3.25 | 310.73 ± 1.99 |
| 64 | 0.0637 ± 0.0013 | 0.9837 ± 0.0003 | 152.77 ± 2.39 | 300.70 ± 1.80 |

More choices improve success and reduce collision and successful-UE delay, but even 64 choices remain heavily overloaded at 5,000 arrivals in one second.

![Contention-capacity results](../results/massive/figures/figure_preamble_capacity.png)

### 5.3 Experiment 2B — RO Period

| RO period (ms) | Success ± CI | Collision ± CI | Mean delay ± CI (ms) | P95 delay ± CI (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 0.1710 ± 0.0021 | 0.9543 ± 0.0006 | 120.79 ± 1.00 | 264.00 ± 1.50 |
| 20 | 0.0329 ± 0.0009 | 0.9917 ± 0.0002 | 177.32 ± 3.25 | 310.73 ± 1.99 |
| 40 | 0.0101 ± 0.0005 | 0.9975 ± 0.0001 | 285.06 ± 6.34 | 393.10 ± 4.59 |

More frequent ROs spread arrivals and retries over more contention opportunities. The 10 ms case performs best among the tested assumptions but still has high collision probability.

![RO-period results](../results/massive/figures/figure_ro_period.png)

### 5.4 Experiment 3 — NTN Delay

| One-way delay (ms) | Success ± CI | Collision ± CI | Mean access delay ± CI (ms) | P95 access delay ± CI (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 0.1031 ± 0.0020 | 0.9732 ± 0.0006 | 121.13 ± 1.75 | 263.63 ± 2.03 |
| 8 | 0.1103 ± 0.0021 | 0.9713 ± 0.0006 | 139.21 ± 1.35 | 291.03 ± 1.98 |
| 12 | 0.1200 ± 0.0023 | 0.9686 ± 0.0006 | 158.94 ± 2.09 | 325.83 ± 1.82 |
| 16 | 0.1286 ± 0.0025 | 0.9662 ± 0.0007 | 179.30 ± 2.06 | 356.53 ± 1.95 |
| 20 | 0.1360 ± 0.0022 | 0.9642 ± 0.0006 | 197.60 ± 1.85 | 386.70 ± 1.91 |

Longer propagation increases completion delay as expected. It also changes retry phase relative to periodic ROs because failed outcomes arrive later before backoff begins; therefore this high-load experiment measures coupled propagation-and-retry scheduling, not a pure additive-delay experiment. No timer timeout is modeled and no run had unfinished UEs.

![NTN-delay results](../results/massive/figures/figure_ntn_delay.png)

### 5.5 Completion-Time Statistics

In Experiment 1, mean absolute completion time rises from 584.15 ± 2.67 ms at 1,000 UEs to 1,035.41 ± 18.43 ms at 10,000 UEs. Mean per-run P95 absolute completion time rises from 1,058.67 ± 3.98 ms to 1,299.33 ± 1.82 ms. Every formal run completed all activated UEs as success or attempt-limit failure before 15 seconds; `unfinished_ues=0` in all 450 runs.

![Successful-UE access-delay CDF](../results/massive/figures/figure_completion_time_cdf.png)

## 6. Validation Evidence

- Build: ns-3 core plus simulator compiled with workspace-local CMake, Ninja, and Zig/Clang.
- C++ tests: 11/11 passed, covering single UE, forced collision, different resources, delay sensitivity, maximum attempts, seed determinism, conservation, future-RO retry timing, uniform arrivals, 10,000-UE load, and duplicate-attempt prevention.
- CSV checks: all four files passed schema, matrix, conservation, activation, attempt-limit, probability, and unfinished-UE checks.
- Horizon: 15 seconds was sufficient for every tested run; this follows from measured terminal-state counts rather than an assumption.

Raw and summary data are in [`../results/massive/raw/`](../results/massive/raw/). Figures are in [`../results/massive/figures/`](../results/massive/figures/), with artifact hashes in [`SHA256SUMS.txt`](../results/massive/SHA256SUMS.txt).

## 7. Limitations

- One beam and one abstract SSB/resource pool; no multi-beam interference or allocation.
- No waveform PRACH, SINR, capture, MsgA PUSCH decoding failure, MsgB reception failure, or fallbackRAR/Msg3.
- Directly configured one-way delay; no geometry, Doppler, timing advance, or scheduling-offset implementation.
- Uniform independent arrivals and resource choices; no correlated traffic or device classes.
- Failed UEs terminate only at the attempt limit; no standards timer-expiry model.
- The delay experiment couples propagation to retry/RO phase under high load.

## 8. Reproduction

From the repository root on the verified Windows environment:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\.build-tools\build-ns3-a3-zig.ps1'
& '.\ns-3-dev\build\scratch\a3-ntn-ra\ns3-dev-ntn-ra-sim-static.exe' '--selfTest=true'

$python = 'C:\Users\wenj\AppData\Local\Programs\Python\Python31210\python.exe'
& $python '.\A3-literature-review\scripts\run_massive_experiments.py' --runs 30
& $python '.\A3-literature-review\tests\check_massive_results.py'
& $python '.\A3-literature-review\scripts\plot_massive_results.py'
```

The runner rewrites only `results/massive/`; it does not modify the legacy archive or original result directories.

## 9. Thesis Relationship

The extension establishes the overload regime in which fixed resources fail, quantifies how contention capacity and RO frequency change performance, and exposes the interaction between NTN response timing and retries. These verified fixed-resource curves are a baseline for future multi-beam dynamic SSB/RO/preamble allocation, fairness, non-uniform traffic, satellite movement, and optimization work.

## References

Literature and 3GPP reference metadata are maintained in [`../study-note.md`](../study-note.md#references).
