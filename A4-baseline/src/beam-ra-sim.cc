/*
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * A4 baseline: ns-3 simulation of the beam-based NR random-access protocol of
 * T.-A. Lin and R.-G. Cheng, "Analytical Modeling and Performance Evaluation of
 * Beam-Based Random Access Protocol for 5G Beamforming Networks,"
 * IEEE IoT-J 10(24):22246-22255, 2023 (Sec. II, Table I, Scenario I / Fig. 4).
 *
 * Model (paper Sec. II-B/C):
 *  - Discrete time-slots of length Delta = 0.125/6 ms (one RO time unit).
 *  - One beam. RA frames of J consecutive RA time-slots, R channels per slot
 *    (R = N^RA * N^F preamble/RO combinations), C frames per RO repetition
 *    period T. Frame offsets inside T are given explicitly per pattern.
 *  - One-shot arrival: M UEs become ready at slot 1.
 *  - A ready UE picks uniformly an RA slot among the remaining slots of the
 *    current RA frame (or among the J slots of the next frame if it is ready in
 *    a non-RA slot), then a channel uniformly among R.
 *  - Error-free channel: a transmission succeeds iff no other UE picked the
 *    same (slot, channel). Result known at the end of the slot.
 *  - Collided UEs draw a backoff counter uniformly in [0, W_BO-1]; the counter
 *    reaches zero at slot j+1+counter; then the slot-selection rule repeats.
 *  - At most N_PTmax transmissions per UE.
 *
 * Each ns-3 run (RngSeed, RngRun) contains `samples` independent one-shot
 * samples; one CSV row with the aggregated counts is written per run.
 * The ns-3 clock uses femtosecond resolution and each RA slot that carries
 * transmissions is a scheduled event at (slot-1)*Delta.
 */

#include "ns3/core-module.h"

#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("BeamRaSim");

namespace
{

struct Pattern
{
    std::string name;
    uint32_t r;                          // channels per RA slot
    uint32_t j;                          // RA slots per RA frame
    uint32_t t;                          // RO repetition period (slots)
    std::vector<uint32_t> frameOffsets;  // 0-based frame starts within T
};

Pattern
GetPattern(const std::string& name)
{
    // Table I with N^RA = 56; pattern (iv) layout from Fig. 5(d): slots 1, 5, 63, 121.
    if (name == "i")
    {
        return {"i", 28, 6, 60, {0}};
    }
    if (name == "ii")
    {
        return {"ii", 112, 6, 60, {0}};
    }
    if (name == "iii")
    {
        return {"iii", 224, 1, 60, {0, 2, 4}};
    }
    if (name == "iv")
    {
        return {"iv", 448, 1, 120, {0, 4, 62}};
    }
    NS_ABORT_MSG("Unknown pattern " << name << " (use i, ii, iii, iv)");
    return {};
}

struct Window
{
    uint64_t first;
    uint64_t last;
};

/** RA slots a UE that becomes ready at slot k may choose from (eq. 11). */
Window
RaWindow(const Pattern& p, uint64_t k)
{
    const uint64_t pos = (k - 1) % p.t;
    const uint64_t base = k - pos;
    for (uint32_t off : p.frameOffsets)
    {
        if (pos >= off && pos < off + p.j)
        {
            return {k, base + off + p.j - 1};
        }
    }
    for (uint32_t off : p.frameOffsets)
    {
        if (base + off > k)
        {
            return {base + off, base + off + p.j - 1};
        }
    }
    const uint64_t start = base + p.t + p.frameOffsets.front();
    return {start, start + p.j - 1};
}

bool
IsRaSlot(const Pattern& p, uint64_t s)
{
    const uint64_t pos = (s - 1) % p.t;
    for (uint32_t off : p.frameOffsets)
    {
        if (pos >= off && pos < off + p.j)
        {
            return true;
        }
    }
    return false;
}

struct Totals
{
    uint64_t ues{0};
    uint64_t successes{0};
    uint64_t failures{0};
    uint64_t transmissions{0};
    uint64_t collidedTransmissions{0};
    double sumDelaySlots{0.0};
    uint64_t maxSuccessSlot{0};
    std::vector<uint64_t> successByAttempt;
    std::map<uint64_t, uint64_t> successBySlot;
};

class BeamRaSimulation
{
  public:
    BeamRaSimulation(const Pattern& pattern, uint32_t ueCount, uint32_t nptMax, uint32_t wbo)
        : m_p(pattern),
          m_m(ueCount),
          m_nptMax(nptMax),
          m_wbo(wbo),
          m_deltaFs(0.125 / 6.0 * 1e12),
          m_channelCount(pattern.r, 0)
    {
        m_totals.successByAttempt.assign(nptMax + 1, 0);
        m_slotRv = CreateObject<UniformRandomVariable>();
        m_channelRv = CreateObject<UniformRandomVariable>();
        m_backoffRv = CreateObject<UniformRandomVariable>();
        m_slotRv->SetStream(0);
        m_channelRv->SetStream(1);
        m_backoffRv->SetStream(2);
    }

    void RunSample()
    {
        m_pending.clear();
        for (uint32_t ue = 0; ue < m_m; ++ue)
        {
            Ready(ue, 1, 1);
        }
        m_totals.ues += m_m;
        Simulator::Run();
        Simulator::Destroy();
        NS_ABORT_MSG_IF(!m_pending.empty(), "UEs left pending after a sample");
    }

    const Totals& GetTotals() const
    {
        return m_totals;
    }

  private:
    struct Tx
    {
        uint32_t ue;
        uint32_t attempt;
        uint32_t channel;
    };

    /** UE becomes ready at slot k for its `attempt`-th transmission. */
    void Ready(uint32_t ue, uint32_t attempt, uint64_t k)
    {
        const Window w = RaWindow(m_p, k);
        const uint64_t slot =
            w.first + m_slotRv->GetInteger(0, static_cast<uint32_t>(w.last - w.first));
        NS_ASSERT(IsRaSlot(m_p, slot));
        auto it = m_pending.find(slot);
        if (it == m_pending.end())
        {
            it = m_pending.emplace(slot, std::vector<Tx>{}).first;
            const Time at = FemtoSeconds(std::llround(static_cast<double>(slot - 1) * m_deltaFs));
            Simulator::Schedule(at - Simulator::Now(), &BeamRaSimulation::ProcessSlot, this, slot);
        }
        it->second.push_back({ue, attempt, 0});
    }

    void ProcessSlot(uint64_t slot)
    {
        auto node = m_pending.extract(slot);
        std::vector<Tx>& txs = node.mapped();
        for (Tx& tx : txs)
        {
            tx.channel = m_channelRv->GetInteger(0, m_p.r - 1);
            ++m_channelCount[tx.channel];
        }
        m_totals.transmissions += txs.size();
        for (const Tx& tx : txs)
        {
            if (m_channelCount[tx.channel] == 1)
            {
                ++m_totals.successes;
                ++m_totals.successByAttempt[tx.attempt];
                ++m_totals.successBySlot[slot];
                m_totals.sumDelaySlots += static_cast<double>(slot);
                m_totals.maxSuccessSlot = std::max(m_totals.maxSuccessSlot, slot);
                continue;
            }
            ++m_totals.collidedTransmissions;
            if (tx.attempt >= m_nptMax)
            {
                ++m_totals.failures;
                continue;
            }
            const uint64_t counter = m_backoffRv->GetInteger(0, m_wbo - 1);
            Ready(tx.ue, tx.attempt + 1, slot + 1 + counter);
        }
        for (const Tx& tx : txs)
        {
            m_channelCount[tx.channel] = 0;
        }
    }

    Pattern m_p;
    uint32_t m_m;
    uint32_t m_nptMax;
    uint32_t m_wbo;
    double m_deltaFs;
    std::vector<uint32_t> m_channelCount;
    std::map<uint64_t, std::vector<Tx>> m_pending;
    Ptr<UniformRandomVariable> m_slotRv;
    Ptr<UniformRandomVariable> m_channelRv;
    Ptr<UniformRandomVariable> m_backoffRv;
    Totals m_totals;
};

bool
SelfTest()
{
    bool ok = true;
    auto check = [&ok](bool cond, const std::string& what) {
        std::cout << (cond ? "PASS " : "FAIL ") << what << "\n";
        ok = ok && cond;
    };
    const Pattern iii = GetPattern("iii");
    const Pattern iv = GetPattern("iv");
    const Pattern ii = GetPattern("ii");
    check(IsRaSlot(iii, 1) && IsRaSlot(iii, 3) && IsRaSlot(iii, 5) && IsRaSlot(iii, 61) &&
              !IsRaSlot(iii, 2) && !IsRaSlot(iii, 7),
          "pattern (iii) RA slots 1,3,5,61 (Fig. 5c)");
    check(IsRaSlot(iv, 1) && IsRaSlot(iv, 5) && IsRaSlot(iv, 63) && IsRaSlot(iv, 121) &&
              !IsRaSlot(iv, 59),
          "pattern (iv) RA slots 1,5,63,121 (Fig. 5d)");
    Window w = RaWindow(ii, 3);
    check(w.first == 3 && w.last == 6, "pattern (ii) ready at slot 3 -> slots 3..6");
    w = RaWindow(ii, 7);
    check(w.first == 61 && w.last == 66, "pattern (ii) ready at slot 7 -> slots 61..66");
    w = RaWindow(iv, 64);
    check(w.first == 121 && w.last == 121, "pattern (iv) ready at slot 64 -> slot 121");

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(1);
    BeamRaSimulation single(ii, 1, 5, 120);
    single.RunSample();
    const Totals& t1 = single.GetTotals();
    check(t1.successes == 1 && t1.transmissions == 1 && t1.maxSuccessSlot <= 6,
          "single UE succeeds on first attempt inside first frame");

    BeamRaSimulation heavy(iii, 2000, 5, 120);
    for (int s = 0; s < 20; ++s)
    {
        heavy.RunSample();
    }
    const Totals& t2 = heavy.GetTotals();
    check(t2.successes + t2.failures == t2.ues, "conservation: success + failure = M");
    uint64_t byAttempt = 0;
    for (uint64_t v : t2.successByAttempt)
    {
        byAttempt += v;
    }
    check(byAttempt == t2.successes, "success-by-attempt sums to successes");
    // I_max for (iii), N=5, W=120 by eq. (1) is 705 slots.
    check(t2.maxSuccessSlot <= 705, "no success after I_max (eq. 1)");
    return ok;
}

} // namespace

int
main(int argc, char* argv[])
{
    Time::SetResolution(Time::FS);

    std::string pattern = "ii";
    uint32_t ueCount = 1000;
    uint32_t nptMax = 5;
    uint32_t wbo = 120;
    uint32_t samples = 1000;
    uint32_t seed = 20261124;
    uint32_t run = 1;
    std::string outputFile = "beam-ra-summary.csv";
    std::string histFile;
    bool selfTest = false;

    CommandLine cmd(__FILE__);
    cmd.AddValue("pattern", "Beam mapping pattern: i, ii, iii, iv (Table I)", pattern);
    cmd.AddValue("ueCount", "M, UEs arriving one-shot at slot 1", ueCount);
    cmd.AddValue("nptMax", "Preamble transmission bound N_PTmax", nptMax);
    cmd.AddValue("wbo", "Backoff window W_BO in time-slots", wbo);
    cmd.AddValue("samples", "Independent one-shot samples in this run", samples);
    cmd.AddValue("seed", "ns-3 RngSeed", seed);
    cmd.AddValue("run", "ns-3 RngRun", run);
    cmd.AddValue("outputFile", "Summary CSV (one row appended per run)", outputFile);
    cmd.AddValue("histFile", "Optional CSV of successes per slot and per attempt", histFile);
    cmd.AddValue("selfTest", "Run built-in checks and exit", selfTest);
    cmd.Parse(argc, argv);

    if (selfTest)
    {
        return SelfTest() ? 0 : 1;
    }
    NS_ABORT_MSG_IF(ueCount == 0 || nptMax == 0 || wbo == 0 || samples == 0,
                    "ueCount, nptMax, wbo and samples must be positive");

    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);
    const Pattern p = GetPattern(pattern);
    BeamRaSimulation sim(p, ueCount, nptMax, wbo);
    for (uint32_t s = 0; s < samples; ++s)
    {
        sim.RunSample();
    }
    const Totals& t = sim.GetTotals();
    const double deltaMs = 0.125 / 6.0;
    const double ps = static_cast<double>(t.successes) / static_cast<double>(t.ues);
    const double psPerTx = static_cast<double>(t.successes) / static_cast<double>(t.transmissions);
    const double daMs = t.successes ? t.sumDelaySlots / t.successes * deltaMs : NAN;
    const double collision =
        static_cast<double>(t.collidedTransmissions) / static_cast<double>(t.transmissions);

    std::ifstream probe(outputFile);
    const bool writeHeader = !probe.good() || probe.peek() == std::ifstream::traits_type::eof();
    probe.close();
    std::ofstream out(outputFile, std::ios::app);
    if (writeHeader)
    {
        out << "pattern,R,J,T,ue_count,npt_max,wbo,seed,run,samples,ues,successes,failures,"
               "transmissions,collided_transmissions,ps,ps_per_tx,collision_prob,da_ms,"
               "max_success_slot\n";
    }
    out << std::setprecision(10) << p.name << ',' << p.r << ',' << p.j << ',' << p.t << ','
        << ueCount << ',' << nptMax << ',' << wbo << ',' << seed << ',' << run << ',' << samples
        << ',' << t.ues << ',' << t.successes << ',' << t.failures << ',' << t.transmissions
        << ',' << t.collidedTransmissions << ',' << ps << ',' << psPerTx << ',' << collision
        << ',' << daMs << ',' << t.maxSuccessSlot << '\n';

    if (!histFile.empty())
    {
        std::ifstream hprobe(histFile);
        const bool hHeader = !hprobe.good() || hprobe.peek() == std::ifstream::traits_type::eof();
        hprobe.close();
        std::ofstream h(histFile, std::ios::app);
        if (hHeader)
        {
            h << "pattern,ue_count,run,kind,index,count\n";
        }
        for (const auto& [slot, count] : t.successBySlot)
        {
            h << p.name << ',' << ueCount << ',' << run << ",slot," << slot << ',' << count
              << '\n';
        }
        for (uint32_t n = 1; n <= nptMax; ++n)
        {
            h << p.name << ',' << ueCount << ',' << run << ",attempt," << n << ','
              << t.successByAttempt[n] << '\n';
        }
    }
    return 0;
}
