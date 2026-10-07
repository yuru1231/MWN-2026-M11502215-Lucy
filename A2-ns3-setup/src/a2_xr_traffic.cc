/*
 * A2 ns-3 setup proof: 3GPP TS 26.926 XR downlink video traffic model,
 * dual eye buffer (TS 26.926 Table 6.5.3.1-1, parameters from TR 38.838).
 *
 *   - Eye buffers:    E streams (default 2: left/right eye) sharing rate R
 *   - Frame arrival:  each eye buffer periodic at 1/F, plus jitter ~ truncated
 *                     Gaussian (TS 26.926 clause 6.5.3.2 refers to TR 38.838:
 *                     mean 0, STD 2 ms, range [-4, 4] ms; the P-trace analysis
 *                     in TS 26.926 observes STD 5 ms, range [-8, 8] ms)
 *   - Frame size:     truncated Gaussian, mean M = R * 1e6 / (E * F) / 8 bytes,
 *                     STD 10.5% of M, range [50%, 150%] of M
 *   - Each frame is split into UDP packets (max 1472-byte UDP payload, i.e.
 *     1500-byte IP packets) and sent back-to-back.
 *
 * Topology: XR server (node 0) --- point-to-point --- XR client (node 1)
 */

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

using namespace ns3;

namespace
{

constexpr uint32_t MAX_UDP_PAYLOAD = 1472; // 1500-byte IP MTU - 20 (IPv4) - 8 (UDP)

std::ofstream g_frameCsv;
std::ofstream g_rxCsv;

std::vector<uint32_t> g_frameOfSeq; // packet sequence number -> frame id
uint64_t g_txBytes = 0;
uint32_t g_txPackets = 0;
uint64_t g_rxBytes = 0;
uint32_t g_rxPackets = 0;
double g_delaySumMs = 0.0;
Time g_pcapStop;

/**
 * Generates XR video frames following the TS 26.926 / TR 38.838 frame model and
 * sends each frame as a burst of UDP packets carrying a SeqTsHeader.
 */
class XrVideoSource : public Application
{
  public:
    void Setup(Address peer,
               double fps,
               double bitRateMbps,
               uint32_t eyeBuffers,
               double jitterStdMs,
               double jitterBoundMs,
               uint32_t numPeriods)
    {
        m_peer = peer;
        m_period = Seconds(1.0 / fps);
        m_eyeBuffers = eyeBuffers;
        m_numPeriods = numPeriods;
        m_meanFrameBytes = bitRateMbps * 1e6 / (eyeBuffers * fps) / 8.0;

        m_frameSize = CreateObject<NormalRandomVariable>();
        m_frameSize->SetAttribute("Mean", DoubleValue(m_meanFrameBytes));
        m_frameSize->SetAttribute("Variance", DoubleValue(std::pow(0.105 * m_meanFrameBytes, 2)));
        m_frameSize->SetAttribute("Bound", DoubleValue(0.5 * m_meanFrameBytes));
        m_frameSize->SetStream(1);

        m_jitterMs = CreateObject<NormalRandomVariable>();
        m_jitterMs->SetAttribute("Mean", DoubleValue(0.0));
        m_jitterMs->SetAttribute("Variance", DoubleValue(jitterStdMs * jitterStdMs));
        m_jitterMs->SetAttribute("Bound", DoubleValue(jitterBoundMs));
        m_jitterMs->SetStream(2);
    }

    double GetMeanFrameBytes() const
    {
        return m_meanFrameBytes;
    }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        m_socket->Bind();
        m_socket->Connect(m_peer);

        // Nominal period k is at start + (k + 1) * period, so a negative jitter on
        // the first frame never schedules it before the application starts.
        // All eye buffers share the same render time; each frame draws its own
        // jitter and size.
        for (uint32_t k = 0; k < m_numPeriods; k++)
        {
            Time nominal = m_period * static_cast<int64_t>(k + 1);
            for (uint32_t eye = 0; eye < m_eyeBuffers; eye++)
            {
                double jitterMs = m_jitterMs->GetValue();
                uint32_t size = static_cast<uint32_t>(std::lround(m_frameSize->GetValue()));
                m_events.push_back(Simulator::Schedule(nominal + Seconds(jitterMs / 1000.0),
                                                       &XrVideoSource::SendFrame,
                                                       this,
                                                       k * m_eyeBuffers + eye,
                                                       eye,
                                                       nominal,
                                                       jitterMs,
                                                       size));
            }
        }
    }

    void StopApplication() override
    {
        for (auto& ev : m_events)
        {
            Simulator::Cancel(ev);
        }
        if (m_socket)
        {
            m_socket->Close();
        }
    }

    void SendFrame(uint32_t frameId,
                   uint32_t eye,
                   Time nominal,
                   double jitterMs,
                   uint32_t frameBytes)
    {
        SeqTsHeader probe;
        const uint32_t maxData = MAX_UDP_PAYLOAD - probe.GetSerializedSize();
        uint32_t remaining = frameBytes;
        uint32_t numPackets = 0;
        while (remaining > 0)
        {
            uint32_t chunk = std::min(remaining, maxData);
            SeqTsHeader header;
            header.SetSeq(m_seq++);
            Ptr<Packet> packet = Create<Packet>(chunk);
            packet->AddHeader(header);
            g_frameOfSeq.push_back(frameId);
            g_txBytes += packet->GetSize();
            g_txPackets++;
            m_socket->Send(packet);
            remaining -= chunk;
            numPackets++;
        }

        g_frameCsv << frameId << "," << eye << "," << std::fixed << std::setprecision(9)
                   << (m_startTime + nominal).GetSeconds() << ","
                   << Simulator::Now().GetSeconds() << "," << std::setprecision(6) << jitterMs
                   << "," << frameBytes << "," << numPackets << "\n";
    }

    Address m_peer;
    Ptr<Socket> m_socket;
    Time m_period;
    uint32_t m_eyeBuffers = 2;
    uint32_t m_numPeriods = 0;
    uint32_t m_seq = 0;
    double m_meanFrameBytes = 0.0;
    Ptr<NormalRandomVariable> m_frameSize;
    Ptr<NormalRandomVariable> m_jitterMs;
    std::vector<EventId> m_events;
};

void
ClientRx(Ptr<Socket> socket)
{
    Ptr<Packet> packet;
    while ((packet = socket->Recv()))
    {
        uint32_t size = packet->GetSize();
        SeqTsHeader header;
        packet->RemoveHeader(header);
        double delayMs = (Simulator::Now() - header.GetTs()).GetSeconds() * 1000.0;
        uint32_t seq = header.GetSeq();

        g_rxBytes += size;
        g_rxPackets++;
        g_delaySumMs += delayMs;
        g_rxCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds() << ","
                << seq << "," << g_frameOfSeq.at(seq) << "," << size << ","
                << std::setprecision(6) << delayMs << "\n";
    }
}

void
PcapSniff(Ptr<PcapFileWrapper> file, Ptr<const Packet> packet)
{
    if (Simulator::Now() < g_pcapStop)
    {
        file->Write(Simulator::Now(), packet);
    }
}

} // namespace

int
main(int argc, char* argv[])
{
    double fps = 60.0;
    double bitRateMbps = 30.0;
    uint32_t eyeBuffers = 2;
    double jitterStdMs = 2.0;
    double jitterBoundMs = 4.0;
    double duration = 60.0;
    double pcapSeconds = 2.0;
    std::string dataRate = "100Mbps";
    std::string linkDelay = "5ms";
    std::string outputDir = "../A2-ns3-setup/results";

    CommandLine cmd(__FILE__);
    cmd.AddValue("fps", "Video frame rate (frames per second).", fps);
    cmd.AddValue("bitRate", "Mean XR video bit rate in Mbps.", bitRateMbps);
    cmd.AddValue("eyeBuffers", "Number of eye buffers (2 = dual eye buffer).", eyeBuffers);
    cmd.AddValue("jitterStd", "Jitter STD in ms (TR 38.838: 2, TS 26.926 P-trace: 5).", jitterStdMs);
    cmd.AddValue("jitterBound", "Jitter truncation in ms (TR 38.838: 4, P-trace: 8).", jitterBoundMs);
    cmd.AddValue("duration", "Traffic duration in seconds.", duration);
    cmd.AddValue("pcapSeconds", "Only the first N seconds are written to the PCAP.", pcapSeconds);
    cmd.AddValue("dataRate", "Point-to-point link data rate.", dataRate);
    cmd.AddValue("linkDelay", "Point-to-point propagation delay.", linkDelay);
    cmd.AddValue("outputDir", "Directory for CSV and PCAP output.", outputDir);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(20261013);
    RngSeedManager::SetRun(1);

    std::filesystem::create_directories(outputDir);
    g_frameCsv.open(outputDir + "/xr_frames.csv");
    g_rxCsv.open(outputDir + "/xr_rx_packets.csv");
    g_frameCsv << "frame_id,eye,nominal_time_s,gen_time_s,jitter_ms,size_bytes,num_packets\n";
    g_rxCsv << "rx_time_s,seq,frame_id,udp_payload_bytes,delay_ms\n";

    NodeContainer nodes;
    nodes.Create(2);

    PointToPointHelper pointToPoint;
    pointToPoint.SetDeviceAttribute("DataRate", StringValue(dataRate));
    pointToPoint.SetChannelAttribute("Delay", StringValue(linkDelay));
    // Keep whole frame bursts (all eye buffers) in the device queue.
    pointToPoint.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize("1000p")));
    NetDeviceContainer devices = pointToPoint.Install(nodes);

    InternetStackHelper stack;
    stack.Install(nodes);

    Ipv4AddressHelper address;
    address.SetBase("10.13.0.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = address.Assign(devices);

    constexpr uint16_t port = 5000;
    Ptr<Socket> sink = Socket::CreateSocket(nodes.Get(1), UdpSocketFactory::GetTypeId());
    sink->Bind(InetSocketAddress(Ipv4Address::GetAny(), port));
    sink->SetRecvCallback(MakeCallback(&ClientRx));

    const double startTime = 1.0;
    const auto numPeriods = static_cast<uint32_t>(duration * fps);
    Ptr<XrVideoSource> source = CreateObject<XrVideoSource>();
    source->Setup(InetSocketAddress(interfaces.GetAddress(1), port),
                  fps,
                  bitRateMbps,
                  eyeBuffers,
                  jitterStdMs,
                  jitterBoundMs,
                  numPeriods);

    // Model parameters for plot_a2_distributions.py (theoretical curves).
    std::ofstream model(outputDir + "/xr_model.csv");
    model << "parameter,value\n"
          << "fps," << fps << "\n"
          << "bit_rate_mbps," << bitRateMbps << "\n"
          << "eye_buffers," << eyeBuffers << "\n"
          << "jitter_std_ms," << jitterStdMs << "\n"
          << "jitter_bound_ms," << jitterBoundMs << "\n";
    model.close();
    nodes.Get(0)->AddApplication(source);
    source->SetStartTime(Seconds(startTime));
    source->SetStopTime(Seconds(startTime + duration + 1.0));

    // PCAP of the client-side link, limited to the first pcapSeconds of traffic.
    g_pcapStop = Seconds(startTime + pcapSeconds);
    PcapHelper pcapHelper;
    Ptr<PcapFileWrapper> pcap =
        pcapHelper.CreateFile(outputDir + "/xr_video_client.pcap", std::ios::out, iana::linktype::PPP);
    devices.Get(1)->TraceConnectWithoutContext("PromiscSniffer", MakeBoundCallback(&PcapSniff, pcap));

    Simulator::Stop(Seconds(startTime + duration + 2.0));
    Simulator::Run();

    const double throughputMbps = g_rxBytes * 8.0 / duration / 1e6;
    const double meanDelayMs = g_rxPackets > 0 ? g_delaySumMs / g_rxPackets : 0.0;

    std::ofstream summary(outputDir + "/xr_summary.txt");
    summary << "ns-3 A2 3GPP TS 26.926 XR video traffic run\n";
    summary << "RngSeed: 20261013, RngRun: 1\n";
    summary << "Topology: 2 nodes, point-to-point, " << dataRate << ", " << linkDelay << "\n";
    summary << "Model: " << eyeBuffers << " eye buffer(s), " << fps << " fps, " << bitRateMbps
            << " Mbps, mean frame size " << source->GetMeanFrameBytes() << " bytes\n";
    summary << "Jitter: truncated Gaussian, STD " << jitterStdMs << " ms, range +/-"
            << jitterBoundMs << " ms\n";
    summary << "Frames generated: " << numPeriods * eyeBuffers << "\n";
    summary << "Packets sent / received: " << g_txPackets << " / " << g_rxPackets << "\n";
    summary << "UDP payload bytes sent / received: " << g_txBytes << " / " << g_rxBytes << "\n";
    summary << "Average UDP-payload throughput: " << throughputMbps << " Mbps\n";
    summary << "Average one-way packet delay: " << meanDelayMs << " ms\n";

    std::cout << "A2 XR traffic run completed, output in " << outputDir << "\n";
    std::cout << "Throughput: " << throughputMbps << " Mbps, mean packet delay: " << meanDelayMs
              << " ms\n";

    Simulator::Destroy();
    return 0;
}
