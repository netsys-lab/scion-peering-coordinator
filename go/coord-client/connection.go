package main

import (
	"context"
	"log"

	"github.com/netsys-lab/scion-peering-coordinator/go/api"
	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
)

type Connection struct {
	Config            *ConnectionConfig
	policies          []Policy
	grpcConn          *grpc.ClientConn
	persistent_stream *api.Peering_StreamChannelClient
	arbChan           chan api.ArbitrationUpdate
	linkUpdateChan    chan api.LinkUpdate
	links             Links
}

func NewConnection(config *ConnectionConfig) *Connection {
	return &Connection{
		Config:         config,
		policies:       parsePolicies(config.Policies),
		arbChan:        make(chan api.ArbitrationUpdate, 8),
		linkUpdateChan: make(chan api.LinkUpdate, 8),
		links:          NewLinks(),
	}
}

func (conn Connection) Connect() {
	var err error
	conn.grpcConn, err = grpc.Dial(conn.Config.Coord, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("Could not connect to %s : %v", conn.Config.Coord, err)
	}

	client := api.NewPeeringClient(conn.grpcConn)
	ctx := context.Background()
	ctx = metadata.AppendToOutgoingContext(ctx,
		"asn", config.Asn,
		"client", conn.Config.ClientName,
		"token", conn.Config.Secret)

	// Open persistent stream
	stream, err := client.StreamChannel(ctx)
	conn.persistent_stream = &stream
	if err != nil {
		log.Fatalf("StreamChannel RPC failed: %v\n", err)
		return
	}
	go conn.recvPersistentStream()

	// Request write access to policies
	request := api.StreamMessageRequest{
		Request: &api.StreamMessageRequest_Arbitration{
			Arbitration: &api.ArbitrationUpdate{
				ElectionId: 100}}}
	stream.Send(&request)

	// Set port ranges
	for _, iface := range conn.Config.Interfaces {
		port_range := api.PortRange{
			InterfaceVlan: iface.Vlan,
			InterfaceIp:   iface.Ip,
			FirstPort:     uint32(iface.FirstPort),
			LastPort:      uint32(iface.LastPort),
		}
		_, err := client.SetPortRange(ctx, &port_range)
		if err != nil {
			log.Printf("SetPortRange RPC failed: %v\n", err)
		}
	}

	// Start a goroutine waiting for link updates
	go func() {
		for {
			select {
			case arb, ok := <-conn.arbChan:
				if !ok {
					return
				}
				if arb.Status == api.ArbitrationUpdate_PRIMARY {
					conn.setPolicies()
				}
			case update, ok := <-conn.linkUpdateChan:
				if !ok {
					return
				}
				if update.Local == nil && update.Remote == nil {
					log.Printf("Received incomplete link update")
					return
				}
				link := Link{
					LinkType:   int(update.LinkType),
					PeerAsn:    update.PeerAsn,
					LocalIp:    update.Local.Ip,
					LocalPort:  uint16(update.Local.Port),
					RemoteIp:   update.Remote.Ip,
					RemotePort: uint16(update.Remote.Port),
				}
				if update.Type == api.LinkUpdate_CREATE {
					conn.links.Add(&link)
				} else if update.Type == api.LinkUpdate_DESTROY {
					conn.links.Remove(&link)
				}
			}
		}
	}()
}

func (conn Connection) Disconnect() {
	if conn.persistent_stream != nil {
		(*conn.persistent_stream).CloseSend()
	}
	if conn.grpcConn != nil {
		conn.grpcConn.Close()
	}
}

func (conn Connection) InstallLinks(topologyFile string) bool {
	return conn.links.Install(topologyFile)
}

func (conn Connection) recvPersistentStream() {
	for {
		response, err := (*conn.persistent_stream).Recv()
		if err != nil {
			log.Printf("Receiving from persistent stream failed: %v\n", err)
			close(conn.arbChan)
			close(conn.linkUpdateChan)
			return
		}
		if response.GetArbitration() != nil {
			arb := response.GetArbitration()
			log.Printf("Arbitration update: %v\n", arb)
			conn.arbChan <- *arb
		} else if response.GetLinkUpdate() != nil {
			log.Printf("Link update: %v\n", response.GetLinkUpdate())
			conn.linkUpdateChan <- *response.GetLinkUpdate()
		} else if response.GetError() != nil {
			err := response.GetError()
			log.Printf("Coordinator: %s\n", err.Message)
		}
	}
}

func (conn Connection) setPolicies() {
	client := api.NewPeeringClient(conn.grpcConn)
	ctx := context.Background()
	ctx = metadata.AppendToOutgoingContext(ctx,
		"asn", config.Asn,
		"client", conn.Config.ClientName,
		"token", conn.Config.Secret)

	// Set policies
	policies := make([]*api.Policy, 0, len(conn.Config.Policies))
	for _, policy := range conn.policies {
		api_policy := api.Policy{
			Vlan:   policy.Vlan,
			Asn:    config.Asn,
			Accept: policy.Accept,
		}
		if policy.PeerAsn != "" {
			api_policy.Peer = &api.Policy_PeerAsn{PeerAsn: policy.PeerAsn}
		} else if policy.PeerOwner != "" {
			api_policy.Peer = &api.Policy_PeerOwner{PeerOwner: policy.PeerOwner}
		} else if policy.PeerIsd != "" {
			api_policy.Peer = &api.Policy_PeerIsd{PeerIsd: policy.PeerIsd}
		}
		policies = append(policies, &api_policy)
	}
	response, err := client.SetPolicies(ctx, &api.SetPoliciesRequest{Policies: policies})
	if err != nil {
		log.Printf("SetPolicies RPC failed: %v\n", err)
	} else {
		for _, msg := range response.Errors {
			log.Printf("Coordinator: %v\n", msg)
		}
	}
}
