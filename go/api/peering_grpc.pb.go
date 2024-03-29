// Code generated by protoc-gen-go-grpc. DO NOT EDIT.

package api

import (
	context "context"
	empty "github.com/golang/protobuf/ptypes/empty"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.32.0 or later.
const _ = grpc.SupportPackageIsVersion7

// PeeringClient is the client API for Peering service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type PeeringClient interface {
	// Persistent channel for push-notifications from the coordinator to the clients.
	StreamChannel(ctx context.Context, opts ...grpc.CallOption) (Peering_StreamChannelClient, error)
	// Set the UDP port range used for SCION overlay connections.
	SetPortRange(ctx context.Context, in *PortRange, opts ...grpc.CallOption) (*empty.Empty, error)
	// List policies of the AS making the request.
	ListPolicies(ctx context.Context, in *ListPolicyRequest, opts ...grpc.CallOption) (Peering_ListPoliciesClient, error)
	// Create a new policy.
	// Returns the newly create policy.
	CreatePolicy(ctx context.Context, in *Policy, opts ...grpc.CallOption) (*Policy, error)
	// Delete a policy.
	DestroyPolicy(ctx context.Context, in *Policy, opts ...grpc.CallOption) (*empty.Empty, error)
	// Replace existing polices in one or all VLANs.
	// If some of the given policies fail validation, the RPC has no effect unless
	// continue_on_error is true.
	SetPolicies(ctx context.Context, in *SetPoliciesRequest, opts ...grpc.CallOption) (*SetPoliciesResponse, error)
}

type peeringClient struct {
	cc grpc.ClientConnInterface
}

func NewPeeringClient(cc grpc.ClientConnInterface) PeeringClient {
	return &peeringClient{cc}
}

func (c *peeringClient) StreamChannel(ctx context.Context, opts ...grpc.CallOption) (Peering_StreamChannelClient, error) {
	stream, err := c.cc.NewStream(ctx, &Peering_ServiceDesc.Streams[0], "/coord.api.Peering/StreamChannel", opts...)
	if err != nil {
		return nil, err
	}
	x := &peeringStreamChannelClient{stream}
	return x, nil
}

type Peering_StreamChannelClient interface {
	Send(*StreamMessageRequest) error
	Recv() (*StreamMessageResponse, error)
	grpc.ClientStream
}

type peeringStreamChannelClient struct {
	grpc.ClientStream
}

func (x *peeringStreamChannelClient) Send(m *StreamMessageRequest) error {
	return x.ClientStream.SendMsg(m)
}

func (x *peeringStreamChannelClient) Recv() (*StreamMessageResponse, error) {
	m := new(StreamMessageResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *peeringClient) SetPortRange(ctx context.Context, in *PortRange, opts ...grpc.CallOption) (*empty.Empty, error) {
	out := new(empty.Empty)
	err := c.cc.Invoke(ctx, "/coord.api.Peering/SetPortRange", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *peeringClient) ListPolicies(ctx context.Context, in *ListPolicyRequest, opts ...grpc.CallOption) (Peering_ListPoliciesClient, error) {
	stream, err := c.cc.NewStream(ctx, &Peering_ServiceDesc.Streams[1], "/coord.api.Peering/ListPolicies", opts...)
	if err != nil {
		return nil, err
	}
	x := &peeringListPoliciesClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type Peering_ListPoliciesClient interface {
	Recv() (*Policy, error)
	grpc.ClientStream
}

type peeringListPoliciesClient struct {
	grpc.ClientStream
}

func (x *peeringListPoliciesClient) Recv() (*Policy, error) {
	m := new(Policy)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *peeringClient) CreatePolicy(ctx context.Context, in *Policy, opts ...grpc.CallOption) (*Policy, error) {
	out := new(Policy)
	err := c.cc.Invoke(ctx, "/coord.api.Peering/CreatePolicy", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *peeringClient) DestroyPolicy(ctx context.Context, in *Policy, opts ...grpc.CallOption) (*empty.Empty, error) {
	out := new(empty.Empty)
	err := c.cc.Invoke(ctx, "/coord.api.Peering/DestroyPolicy", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *peeringClient) SetPolicies(ctx context.Context, in *SetPoliciesRequest, opts ...grpc.CallOption) (*SetPoliciesResponse, error) {
	out := new(SetPoliciesResponse)
	err := c.cc.Invoke(ctx, "/coord.api.Peering/SetPolicies", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// PeeringServer is the server API for Peering service.
// All implementations must embed UnimplementedPeeringServer
// for forward compatibility
type PeeringServer interface {
	// Persistent channel for push-notifications from the coordinator to the clients.
	StreamChannel(Peering_StreamChannelServer) error
	// Set the UDP port range used for SCION overlay connections.
	SetPortRange(context.Context, *PortRange) (*empty.Empty, error)
	// List policies of the AS making the request.
	ListPolicies(*ListPolicyRequest, Peering_ListPoliciesServer) error
	// Create a new policy.
	// Returns the newly create policy.
	CreatePolicy(context.Context, *Policy) (*Policy, error)
	// Delete a policy.
	DestroyPolicy(context.Context, *Policy) (*empty.Empty, error)
	// Replace existing polices in one or all VLANs.
	// If some of the given policies fail validation, the RPC has no effect unless
	// continue_on_error is true.
	SetPolicies(context.Context, *SetPoliciesRequest) (*SetPoliciesResponse, error)
	mustEmbedUnimplementedPeeringServer()
}

// UnimplementedPeeringServer must be embedded to have forward compatible implementations.
type UnimplementedPeeringServer struct {
}

func (UnimplementedPeeringServer) StreamChannel(Peering_StreamChannelServer) error {
	return status.Errorf(codes.Unimplemented, "method StreamChannel not implemented")
}
func (UnimplementedPeeringServer) SetPortRange(context.Context, *PortRange) (*empty.Empty, error) {
	return nil, status.Errorf(codes.Unimplemented, "method SetPortRange not implemented")
}
func (UnimplementedPeeringServer) ListPolicies(*ListPolicyRequest, Peering_ListPoliciesServer) error {
	return status.Errorf(codes.Unimplemented, "method ListPolicies not implemented")
}
func (UnimplementedPeeringServer) CreatePolicy(context.Context, *Policy) (*Policy, error) {
	return nil, status.Errorf(codes.Unimplemented, "method CreatePolicy not implemented")
}
func (UnimplementedPeeringServer) DestroyPolicy(context.Context, *Policy) (*empty.Empty, error) {
	return nil, status.Errorf(codes.Unimplemented, "method DestroyPolicy not implemented")
}
func (UnimplementedPeeringServer) SetPolicies(context.Context, *SetPoliciesRequest) (*SetPoliciesResponse, error) {
	return nil, status.Errorf(codes.Unimplemented, "method SetPolicies not implemented")
}
func (UnimplementedPeeringServer) mustEmbedUnimplementedPeeringServer() {}

// UnsafePeeringServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to PeeringServer will
// result in compilation errors.
type UnsafePeeringServer interface {
	mustEmbedUnimplementedPeeringServer()
}

func RegisterPeeringServer(s grpc.ServiceRegistrar, srv PeeringServer) {
	s.RegisterService(&Peering_ServiceDesc, srv)
}

func _Peering_StreamChannel_Handler(srv interface{}, stream grpc.ServerStream) error {
	return srv.(PeeringServer).StreamChannel(&peeringStreamChannelServer{stream})
}

type Peering_StreamChannelServer interface {
	Send(*StreamMessageResponse) error
	Recv() (*StreamMessageRequest, error)
	grpc.ServerStream
}

type peeringStreamChannelServer struct {
	grpc.ServerStream
}

func (x *peeringStreamChannelServer) Send(m *StreamMessageResponse) error {
	return x.ServerStream.SendMsg(m)
}

func (x *peeringStreamChannelServer) Recv() (*StreamMessageRequest, error) {
	m := new(StreamMessageRequest)
	if err := x.ServerStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func _Peering_SetPortRange_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(PortRange)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PeeringServer).SetPortRange(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/coord.api.Peering/SetPortRange",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PeeringServer).SetPortRange(ctx, req.(*PortRange))
	}
	return interceptor(ctx, in, info, handler)
}

func _Peering_ListPolicies_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(ListPolicyRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(PeeringServer).ListPolicies(m, &peeringListPoliciesServer{stream})
}

type Peering_ListPoliciesServer interface {
	Send(*Policy) error
	grpc.ServerStream
}

type peeringListPoliciesServer struct {
	grpc.ServerStream
}

func (x *peeringListPoliciesServer) Send(m *Policy) error {
	return x.ServerStream.SendMsg(m)
}

func _Peering_CreatePolicy_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Policy)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PeeringServer).CreatePolicy(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/coord.api.Peering/CreatePolicy",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PeeringServer).CreatePolicy(ctx, req.(*Policy))
	}
	return interceptor(ctx, in, info, handler)
}

func _Peering_DestroyPolicy_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Policy)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PeeringServer).DestroyPolicy(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/coord.api.Peering/DestroyPolicy",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PeeringServer).DestroyPolicy(ctx, req.(*Policy))
	}
	return interceptor(ctx, in, info, handler)
}

func _Peering_SetPolicies_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(SetPoliciesRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PeeringServer).SetPolicies(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/coord.api.Peering/SetPolicies",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PeeringServer).SetPolicies(ctx, req.(*SetPoliciesRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// Peering_ServiceDesc is the grpc.ServiceDesc for Peering service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var Peering_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "coord.api.Peering",
	HandlerType: (*PeeringServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "SetPortRange",
			Handler:    _Peering_SetPortRange_Handler,
		},
		{
			MethodName: "CreatePolicy",
			Handler:    _Peering_CreatePolicy_Handler,
		},
		{
			MethodName: "DestroyPolicy",
			Handler:    _Peering_DestroyPolicy_Handler,
		},
		{
			MethodName: "SetPolicies",
			Handler:    _Peering_SetPolicies_Handler,
		},
	},
	Streams: []grpc.StreamDesc{
		{
			StreamName:    "StreamChannel",
			Handler:       _Peering_StreamChannel_Handler,
			ServerStreams: true,
			ClientStreams: true,
		},
		{
			StreamName:    "ListPolicies",
			Handler:       _Peering_ListPolicies_Handler,
			ServerStreams: true,
		},
	},
	Metadata: "api/peering.proto",
}
