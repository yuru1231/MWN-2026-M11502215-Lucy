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

## Traffic Model Choice

I used ns-3's built-in `ThreeGppHttpClient` and `ThreeGppHttpServer` application model. This model implements the 3GPP-style web browsing traffic model with random main-object size, embedded-object size, number of embedded objects, parsing time, and reading time.

The relevant ns-3 implementation is in:

- `ns-3-dev/src/applications/model/three-gpp-http-client.cc`
- `ns-3-dev/src/applications/model/three-gpp-http-server.cc`
- `ns-3-dev/src/applications/model/three-gpp-http-variables.cc`

Important default variables from ns-3:

| Variable | Distribution / Value |
|---|---|
| HTTP request size | Constant, 328 bytes |
| Main object size | Lognormal, mean 10710 bytes, std. dev. 25032 bytes |
| Embedded object size | Lognormal, mean 7758 bytes, std. dev. 126168 bytes |
| Number of embedded objects | Pareto, max 55, shape 1.1, scale 2 |
| Reading time | Exponential, mean 30 s |
| Parsing time | Exponential, mean 130 ms |
| MTU | 1460 bytes with probability 0.76, otherwise 536 bytes |

## Scenario

The source code is `A2-ns3-setup/src/a2_three_gpp_http.cc`. A small wrapper in `ns-3-dev/scratch/a2_three_gpp_http.cc` lets ns-3 build it as a scratch program.

Topology:

```text
HTTP client node 0 ---- point-to-point link ---- HTTP server node 1
10 Mbps, 10 ms one-way propagation delay
```

The run records:

- packet trace: `A2-ns3-setup/results/a2_packet_trace.csv`
- generated object sizes: `A2-ns3-setup/results/a2_object_sizes.csv`
- page-load trace: `A2-ns3-setup/results/a2_page_loads.csv`
- object delay trace: `A2-ns3-setup/results/a2_object_delays.csv`
- PCAP files: `A2-ns3-setup/results/a2_three_gpp_http-*.pcap`
- summary: `A2-ns3-setup/results/a2_summary.txt`

Run command:

```bash
cd ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 run "scratch/a2_three_gpp_http --outputDir=../A2-ns3-setup/results"
cd ..
python A2-ns3-setup/src/plot_a2_distributions.py
```

## Verification Method

The simulation connects to these trace sources:

- `TxMainObjectRequest` and `TxEmbeddedObjectRequest` for uplink request packets.
- `MainObject` and `EmbeddedObject` for generated 3GPP object sizes.
- `RxMainObjectPacket` and `RxEmbeddedObjectPacket` for downlink packet sizes.
- `RxDelay` for object-level one-way delay.
- `RxPage` for page-load completion.

The plotting script computes:

- packet-size PDF/CDF from downlink HTTP packets.
- inter-arrival-time PDF/CDF from consecutive downlink HTTP packet arrival times.

Generated figures:

- `A2-ns3-setup/results/packet_size_pdf_cdf.png`
- `A2-ns3-setup/results/interarrival_pdf_cdf.png`

## Presentation Talking Points

1. I installed and built ns-3, and fixed the CMake version problem.
2. I used ns-3's 3GPP HTTP application instead of a constant-size echo packet, so packet size and timing are random.
3. My trace files prove the simulator ran locally: CSV traces, summary throughput/delay numbers, and PCAP captures are generated under `results/`.
4. The PDF/CDF plots verify that the generated traffic has a non-constant packet-size distribution and a non-constant inter-arrival distribution.
