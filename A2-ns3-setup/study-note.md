# A2 - ns-3 Setup and 3GPP Traffic Model

## Assignment

Week 7, due 2026-10-13 23:59, 10 minute presentation.

Goal: install and build ns-3, run my own simulation, and verify the traffic model with packet-size and inter-arrival distributions.

## Platform and ns-3 Version

My recorded platform for the ns-3 build:

| Item | Value |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| Compiler | GCC/G++ 11.4.0 |
| Python | 3.10.12 |
| CMake | 4.4.3 after update |
| Ninja | 1.10.1 |
| ns-3 tree | `ns-3-dev` |
| ns-3 version file | `3-dev` |
| Git describe recorded during install | `ns-3.48-192-g9611dfcb5` |

The installation screenshots and earlier command notes are in `Installation.md`.

## What Broke

The first configure attempt failed because Ubuntu 22.04's default CMake was too old for this ns-3 checkout. I fixed it by adding the Kitware apt repository and installing a newer CMake package, then reran:

```bash
./ns3 configure --enable-examples --enable-tests
./ns3 build
```

## Traffic Model: 3GPP TS 26.926

3GPP TS 26.926 (*Traffic Models and Quality Evaluation Methods for Media and XR Services in 5G Systems*) defines traffic models for XR and cloud-gaming media. I implemented the downlink XR video model with **dual eye buffers** from **TS 26.926 clause 6.5.3.1, Table 6.5.3.1-1** ("Statistical parameter values for dual eye buffer frame size"). The table takes its parameters from 3GPP TR 38.838 (XR evaluation for NR). Left and right eye are two video streams that share the total bit rate `R`, and each eye buffer produces one frame every `1/F`:

| Item | TS 26.926 Table 6.5.3.1-1 (TR 38.838) | Value used |
|---|---|---|
| Eye buffers | 2 (left / right eye), same render time | 2 |
| Frame rate | Fixed `F` fps per eye buffer, nominal arrival every `1/F` | 60 fps → 16.667 ms |
| Mean bit rate | `R` | 30 Mbps |
| Frame size | Truncated Gaussian, mean `M = R×1e6/(2×F)/8`, STD 10.5% of M, range [50%, 150%] of M | M = 31,250 B, STD 3,281 B, range [15,625, 46,875] B |
| Frame jitter | Truncated Gaussian added on top of periodic arrivals (clause 6.5.3.2, values from TR 38.838): mean 0, STD 2 ms, range [-4, 4] ms | same (default) |
| Frame arrival time | `t_k = k/F + jitter_k`, drawn independently for each eye buffer | — |

Table 6.5.3.1-1 also lists optional values: STD 4% of M, range [88%, 112%]. Table 6.5.3.1-2 (P-trace analysis; the spec labels it 6.5.3.1-1 by mistake) shows that real VR traces with 30–45 Mbps have a STD/mean of about 2–15%, which is consistent with the 10.5% statistical model. TS 26.926 clause 5.6.2 describes the full trace-based encoder/decoder model (V-Trace → S-Trace). This assignment uses the simplified statistical model instead: 1 slice per frame, no encoder simulation.

Clause 6.5.3.2 does not give its own jitter table. It states that "the jitter statistical model refers to the description in TR 38.838 ... modelled as a random variable added on top of periodic arrivals, which follows truncated Gaussian distribution", so the default run uses the TR 38.838 values.

The P-trace analysis in the same clause (Table 6.5.3.2-1, Figure 6.5.3.2-1) shows larger jitter in real traces: per-trace STD 4.0–5.3 ms, min/max up to about ±19 ms, 5%–95% range about [-8.8, +8.4] ms. The clause summarises this as **mean 0 ms, STD 5 ms, range [-8, 8] ms**. I run this as a second scenario (`--jitterStd=5 --jitterBound=8`) to compare with the TR 38.838 baseline. Because ±8 ms is still smaller than half the frame period (8.33 ms), frames of one eye buffer never reorder.

Because the jitter range (±4 ms) is smaller than half the frame period, frames never reorder. The inter-arrival time between two frames is `1/F + J(k+1) - J(k)`, so its theoretical PDF is the jitter PDF convolved with itself and shifted by 16.667 ms.

ns-3 has no built-in TS 26.926 application, so I wrote one with AI assistance (`XrVideoSource` in `src/a2_xr_traffic.cc`):

- `NormalRandomVariable` with the `Bound` attribute gives the truncated Gaussian: ns-3 redraws until `|x - mean| <= Bound`.
- At the frame time, the frame is split into UDP packets of at most 1472 bytes of UDP payload (1500-byte IP packets). Each packet carries a 12-byte `SeqTsHeader` (sequence number + send timestamp), so the receiver can measure delay.

## Scenario

Source: `A2-ns3-setup/src/a2_xr_traffic.cc`. A one-line wrapper `ns-3-dev/scratch/a2_xr_traffic.cc` includes it so that ns-3 builds it as a scratch program.

```text
XR server (node 0) ---- point-to-point ---- XR client (node 1)
10.13.0.1          100 Mbps, 5 ms delay          10.13.0.2
UDP XR video source  ───────────────────────►  UDP sink, port 5000
```

- 60 s of traffic → 3600 periods × 2 eye buffers = 7200 frames (about 157k packets), enough samples for the distributions
- `--eyeBuffers=1` switches to a single-stream model (mean `R/(8F)`)
- device queue 1000 packets, so a full frame burst never drops
- RNG seed 20261013, run 1 (reproducible)

Run command:

```bash
cd ns-3-dev
./ns3 build a2_xr_traffic
./ns3 run "scratch/a2_xr_traffic --outputDir=../A2-ns3-setup/results"
cd ..
python3 A2-ns3-setup/src/plot_a2_distributions.py

# Scenario 2: jitter observed in the TS 26.926 P-traces (STD 5 ms, [-8, 8] ms)
cd ns-3-dev
./ns3 run "scratch/a2_xr_traffic --jitterStd=5 --jitterBound=8 --outputDir=../A2-ns3-setup/results/ptrace_jitter"
cd ..
python3 A2-ns3-setup/src/plot_a2_distributions.py --results A2-ns3-setup/results/ptrace_jitter
```

Output in `A2-ns3-setup/results/`:

| File | Content |
|---|---|
| `xr_frames.csv` | per frame: nominal time, generation time, jitter, size, number of packets |
| `xr_rx_packets.csv` | per received packet: time, seq, frame id, UDP payload size, one-way delay |
| `xr_model.csv` | model parameters used by the run (read by the plot script) |
| `xr_summary.txt` | throughput, packets sent/received, mean packet delay |
| `xr_video_client.pcap` | client-side link capture, first 2 s only (open in Wireshark) |
| `xr_distribution_summary.txt` | distribution statistics, KS test, frame delay |
| `frame_size_pdf_cdf.png` | frame size PDF/CDF vs theory |
| `frame_jitter_pdf_cdf.png` | jitter PDF/CDF vs theory |
| `frame_interarrival_pdf_cdf.png` | frame inter-arrival PDF/CDF vs theory |
| `packet_size_pdf_cdf.png` | IP packet size seen at the client |
| `packet_interarrival_pdf_cdf.png` | packet inter-arrival seen at the client (log scale) |

## Verification Method

1. **Model level (what TS 26.926 defines):** frame size, jitter, and frame inter-arrival are plotted as PDF and CDF, with the theoretical curve on top. The Kolmogorov–Smirnov statistic `D` is compared with the 5% critical value `1.36/√n` (≈ 0.016 for n = 7200). If `D` is below it, the generated data is consistent with the specified distribution.
2. **Network level (what the receiver sees):** each frame turns into a burst of full-size 1500-byte packets plus one smaller last fragment. The packet inter-arrival is bimodal:
   - back-to-back packets inside a burst: 1502 B × 8 / 100 Mbps ≈ **0.12 ms**
   - gap between bursts: about one frame period minus the burst duration
3. **Sanity checks:**
   - throughput ≈ 30 Mbps × (1 + header overhead)
   - packet delay = 5 ms propagation + queueing behind earlier packets of the same frame
   - frame delay (last packet received − frame generation) ≈ 5 ms + 22 × 0.12 ms ≈ 7.6 ms, plus extra queueing when both eye frames arrive close together

## Results

> TODO: fill in after running on Ubuntu (copy numbers from `xr_summary.txt` and `xr_distribution_summary.txt`; add a Wireshark screenshot of `xr_video_client.pcap`).

| Metric | Value |
|---|---|
| Throughput (UDP payload) | |
| Packets sent / received | |
| Mean packet delay | |
| Frame delay mean / p95 | |
| KS D: frame size / jitter / inter-arrival | |

## Presentation Talking Points

1. Installed and built ns-3 on Ubuntu 22.04 and fixed the CMake version problem.
2. Studied 3GPP TS 26.926 and implemented its dual-eye-buffer XR video model (Table 6.5.3.1-1) as an ns-3 application: 2 × 60 fps frames, truncated-Gaussian frame size and jitter.
3. Proof the run is mine: CSV traces, a throughput/delay summary, and a PCAP opened in Wireshark.
4. Verification: the frame-size, jitter, and inter-arrival PDF/CDF match the theoretical curves, and the KS statistic is below the 5% critical value.
5. Network view: a frame becomes a burst of 1500-byte packets 0.12 ms apart, which explains the packet-level distributions and the ≈8 ms frame delay.
