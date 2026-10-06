/*
 * A2 ns-3 setup proof: two-node point-to-point topology running the built-in
 * 3GPP HTTP traffic model.
 */

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using namespace ns3;

namespace
{

std::ofstream g_packetCsv;
std::ofstream g_objectCsv;
std::ofstream g_pageCsv;
std::ofstream g_delayCsv;

uint64_t g_rxBytes = 0;
uint32_t g_rxPackets = 0;

void
WritePacketEvent(const std::string& direction, const std::string& event, Ptr<const Packet> packet)
{
    g_packetCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds() << ","
                << direction << "," << event << "," << packet->GetSize() << "\n";
}

void
ClientTxMainObjectRequest(Ptr<const Packet> packet)
{
    WritePacketEvent("uplink", "main_request", packet);
}

void
ClientTxEmbeddedObjectRequest(Ptr<const Packet> packet)
{
    WritePacketEvent("uplink", "embedded_request", packet);
}

void
ClientRxMainObjectPacket(Ptr<const Packet> packet)
{
    g_rxBytes += packet->GetSize();
    g_rxPackets++;
    WritePacketEvent("downlink", "main_object_packet", packet);
}

void
ClientRxEmbeddedObjectPacket(Ptr<const Packet> packet)
{
    g_rxBytes += packet->GetSize();
    g_rxPackets++;
    WritePacketEvent("downlink", "embedded_object_packet", packet);
}

void
ServerMainObject(uint32_t size)
{
    g_objectCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds()
                << ",main," << size << "\n";
}

void
ServerEmbeddedObject(uint32_t size)
{
    g_objectCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds()
                << ",embedded," << size << "\n";
}

void
ClientRxPage(Ptr<const ThreeGppHttpClient> client, const Time& time, uint32_t objects, uint32_t bytes)
{
    (void)client;
    g_pageCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds() << ","
              << time.GetSeconds() << "," << objects << "," << bytes << "\n";
}

void
ClientRxDelay(const Time& delay, const Address& from)
{
    (void)from;
    g_delayCsv << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds() << ","
               << delay.GetSeconds() << "\n";
}

void
StopAfterPages(const std::string& oldState, const std::string& newState)
{
    static uint32_t pages = 0;
    (void)oldState;
    if (newState == "READING")
    {
        pages++;
        if (pages >= 8)
        {
            Simulator::Stop();
        }
    }
}

} // namespace

int
main(int argc, char* argv[])
{
    double simTime = 240.0;
    std::string dataRate = "10Mbps";
    std::string linkDelay = "10ms";
    std::string outputDir = "../A2-ns3-setup/results";

    CommandLine cmd(__FILE__);
    cmd.AddValue("simTime", "Maximum simulation time in seconds.", simTime);
    cmd.AddValue("dataRate", "Point-to-point link data rate.", dataRate);
    cmd.AddValue("linkDelay", "Point-to-point propagation delay.", linkDelay);
    cmd.AddValue("outputDir", "Directory for CSV and PCAP output.", outputDir);
    cmd.Parse(argc, argv);

    Config::SetGlobal("RngSeed", UintegerValue(20261013));
    Config::SetGlobal("RngRun", UintegerValue(7));

    std::filesystem::create_directories(outputDir);

    g_packetCsv.open(outputDir + "/a2_packet_trace.csv");
    g_objectCsv.open(outputDir + "/a2_object_sizes.csv");
    g_pageCsv.open(outputDir + "/a2_page_loads.csv");
    g_delayCsv.open(outputDir + "/a2_object_delays.csv");

    g_packetCsv << "time_s,direction,event,size_bytes\n";
    g_objectCsv << "time_s,object_type,size_bytes\n";
    g_pageCsv << "time_s,page_load_s,objects,bytes\n";
    g_delayCsv << "time_s,delay_s\n";

    NodeContainer nodes;
    nodes.Create(2);

    PointToPointHelper pointToPoint;
    pointToPoint.SetDeviceAttribute("DataRate", StringValue(dataRate));
    pointToPoint.SetChannelAttribute("Delay", StringValue(linkDelay));
    NetDeviceContainer devices = pointToPoint.Install(nodes);

    InternetStackHelper stack;
    stack.Install(nodes);

    Ipv4AddressHelper address;
    address.SetBase("10.13.0.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = address.Assign(devices);

    constexpr uint16_t port = 80;
    Address serverAddress(InetSocketAddress(interfaces.GetAddress(1), port));
    ThreeGppHttpServerHelper serverHelper(serverAddress);
    ApplicationContainer serverApps = serverHelper.Install(nodes.Get(1));
    serverApps.Start(Seconds(0.2));
    serverApps.Stop(Seconds(simTime));

    ThreeGppHttpClientHelper clientHelper(serverAddress);
    ApplicationContainer clientApps = clientHelper.Install(nodes.Get(0));
    clientApps.Start(Seconds(1.0));
    clientApps.Stop(Seconds(simTime));

    Ptr<ThreeGppHttpServer> server = serverApps.Get(0)->GetObject<ThreeGppHttpServer>();
    Ptr<ThreeGppHttpClient> client = clientApps.Get(0)->GetObject<ThreeGppHttpClient>();

    server->TraceConnectWithoutContext("MainObject", MakeCallback(&ServerMainObject));
    server->TraceConnectWithoutContext("EmbeddedObject", MakeCallback(&ServerEmbeddedObject));
    client->TraceConnectWithoutContext("TxMainObjectRequest",
                                       MakeCallback(&ClientTxMainObjectRequest));
    client->TraceConnectWithoutContext("TxEmbeddedObjectRequest",
                                       MakeCallback(&ClientTxEmbeddedObjectRequest));
    client->TraceConnectWithoutContext("RxMainObjectPacket", MakeCallback(&ClientRxMainObjectPacket));
    client->TraceConnectWithoutContext("RxEmbeddedObjectPacket",
                                       MakeCallback(&ClientRxEmbeddedObjectPacket));
    client->TraceConnectWithoutContext("RxPage", MakeCallback(&ClientRxPage));
    client->TraceConnectWithoutContext("RxDelay", MakeCallback(&ClientRxDelay));
    client->TraceConnectWithoutContext("StateTransition", MakeCallback(&StopAfterPages));

    pointToPoint.EnablePcapAll(outputDir + "/a2_three_gpp_http", true);

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    const double elapsed = Simulator::Now().GetSeconds() - 1.0;
    const double throughputMbps = elapsed > 0.0 ? (g_rxBytes * 8.0 / elapsed / 1e6) : 0.0;

    std::ofstream summary(outputDir + "/a2_summary.txt");
    summary << "ns-3 A2 3GPP HTTP run\n";
    summary << "RngSeed: 20261013\n";
    summary << "RngRun: 7\n";
    summary << "Topology: 2 nodes, point-to-point, " << dataRate << ", " << linkDelay << "\n";
    summary << "Simulation stop time: " << Simulator::Now().GetSeconds() << " s\n";
    summary << "Received downlink application bytes: " << g_rxBytes << "\n";
    summary << "Received downlink packets traced by HTTP client: " << g_rxPackets << "\n";
    summary << "Average downlink application throughput: " << throughputMbps << " Mbps\n";

    std::cout << "A2 3GPP HTTP run completed\n";
    std::cout << "Output directory: " << outputDir << "\n";
    std::cout << "Received bytes: " << g_rxBytes << "\n";
    std::cout << "Average downlink application throughput: " << throughputMbps << " Mbps\n";

    Simulator::Destroy();
    return 0;
}
