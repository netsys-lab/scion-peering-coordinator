// Code generated by protoc-gen-go. DO NOT EDIT.
// versions:
// 	protoc-gen-go v1.26.0
// 	protoc        v3.6.1
// source: api/info.proto

package api

import (
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	reflect "reflect"
	sync "sync"
)

const (
	// Verify that this generated code is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	// Verify that runtime/protoimpl is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

type Owner struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// Unique owner name.
	Name string `protobuf:"bytes,1,opt,name=name,proto3" json:"name,omitempty"`
	// Long descriptive owner name.
	LongName string `protobuf:"bytes,2,opt,name=long_name,json=longName,proto3" json:"long_name,omitempty"`
	// ASes owned by the owner.
	Asns []string `protobuf:"bytes,3,rep,name=asns,proto3" json:"asns,omitempty"`
}

func (x *Owner) Reset() {
	*x = Owner{}
	if protoimpl.UnsafeEnabled {
		mi := &file_api_info_proto_msgTypes[0]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *Owner) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*Owner) ProtoMessage() {}

func (x *Owner) ProtoReflect() protoreflect.Message {
	mi := &file_api_info_proto_msgTypes[0]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use Owner.ProtoReflect.Descriptor instead.
func (*Owner) Descriptor() ([]byte, []int) {
	return file_api_info_proto_rawDescGZIP(), []int{0}
}

func (x *Owner) GetName() string {
	if x != nil {
		return x.Name
	}
	return ""
}

func (x *Owner) GetLongName() string {
	if x != nil {
		return x.LongName
	}
	return ""
}

func (x *Owner) GetAsns() []string {
	if x != nil {
		return x.Asns
	}
	return nil
}

type GetOwnerRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// (Optional) Name of the owner.
	Name string `protobuf:"bytes,1,opt,name=name,proto3" json:"name,omitempty"`
	// (Optional) An AS owned by the owner to get.
	Asn string `protobuf:"bytes,2,opt,name=asn,proto3" json:"asn,omitempty"`
}

func (x *GetOwnerRequest) Reset() {
	*x = GetOwnerRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_api_info_proto_msgTypes[1]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *GetOwnerRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*GetOwnerRequest) ProtoMessage() {}

func (x *GetOwnerRequest) ProtoReflect() protoreflect.Message {
	mi := &file_api_info_proto_msgTypes[1]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use GetOwnerRequest.ProtoReflect.Descriptor instead.
func (*GetOwnerRequest) Descriptor() ([]byte, []int) {
	return file_api_info_proto_rawDescGZIP(), []int{1}
}

func (x *GetOwnerRequest) GetName() string {
	if x != nil {
		return x.Name
	}
	return ""
}

func (x *GetOwnerRequest) GetAsn() string {
	if x != nil {
		return x.Asn
	}
	return ""
}

type SearchOwnerRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// String contained in the name of the owner. Matching is case insensitive.
	LongName string `protobuf:"bytes,1,opt,name=long_name,json=longName,proto3" json:"long_name,omitempty"`
}

func (x *SearchOwnerRequest) Reset() {
	*x = SearchOwnerRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_api_info_proto_msgTypes[2]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *SearchOwnerRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*SearchOwnerRequest) ProtoMessage() {}

func (x *SearchOwnerRequest) ProtoReflect() protoreflect.Message {
	mi := &file_api_info_proto_msgTypes[2]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use SearchOwnerRequest.ProtoReflect.Descriptor instead.
func (*SearchOwnerRequest) Descriptor() ([]byte, []int) {
	return file_api_info_proto_rawDescGZIP(), []int{2}
}

func (x *SearchOwnerRequest) GetLongName() string {
	if x != nil {
		return x.LongName
	}
	return ""
}

var File_api_info_proto protoreflect.FileDescriptor

var file_api_info_proto_rawDesc = []byte{
	0x0a, 0x0e, 0x61, 0x70, 0x69, 0x2f, 0x69, 0x6e, 0x66, 0x6f, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f,
	0x12, 0x09, 0x63, 0x6f, 0x6f, 0x72, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x22, 0x4c, 0x0a, 0x05, 0x4f,
	0x77, 0x6e, 0x65, 0x72, 0x12, 0x12, 0x0a, 0x04, 0x6e, 0x61, 0x6d, 0x65, 0x18, 0x01, 0x20, 0x01,
	0x28, 0x09, 0x52, 0x04, 0x6e, 0x61, 0x6d, 0x65, 0x12, 0x1b, 0x0a, 0x09, 0x6c, 0x6f, 0x6e, 0x67,
	0x5f, 0x6e, 0x61, 0x6d, 0x65, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x08, 0x6c, 0x6f, 0x6e,
	0x67, 0x4e, 0x61, 0x6d, 0x65, 0x12, 0x12, 0x0a, 0x04, 0x61, 0x73, 0x6e, 0x73, 0x18, 0x03, 0x20,
	0x03, 0x28, 0x09, 0x52, 0x04, 0x61, 0x73, 0x6e, 0x73, 0x22, 0x37, 0x0a, 0x0f, 0x47, 0x65, 0x74,
	0x4f, 0x77, 0x6e, 0x65, 0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x12, 0x0a, 0x04,
	0x6e, 0x61, 0x6d, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09, 0x52, 0x04, 0x6e, 0x61, 0x6d, 0x65,
	0x12, 0x10, 0x0a, 0x03, 0x61, 0x73, 0x6e, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x03, 0x61,
	0x73, 0x6e, 0x22, 0x31, 0x0a, 0x12, 0x53, 0x65, 0x61, 0x72, 0x63, 0x68, 0x4f, 0x77, 0x6e, 0x65,
	0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x1b, 0x0a, 0x09, 0x6c, 0x6f, 0x6e, 0x67,
	0x5f, 0x6e, 0x61, 0x6d, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09, 0x52, 0x08, 0x6c, 0x6f, 0x6e,
	0x67, 0x4e, 0x61, 0x6d, 0x65, 0x32, 0x86, 0x01, 0x0a, 0x04, 0x49, 0x6e, 0x66, 0x6f, 0x12, 0x3a,
	0x0a, 0x08, 0x47, 0x65, 0x74, 0x4f, 0x77, 0x6e, 0x65, 0x72, 0x12, 0x1a, 0x2e, 0x63, 0x6f, 0x6f,
	0x72, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x47, 0x65, 0x74, 0x4f, 0x77, 0x6e, 0x65, 0x72, 0x52,
	0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x10, 0x2e, 0x63, 0x6f, 0x6f, 0x72, 0x64, 0x2e, 0x61,
	0x70, 0x69, 0x2e, 0x4f, 0x77, 0x6e, 0x65, 0x72, 0x22, 0x00, 0x12, 0x42, 0x0a, 0x0b, 0x53, 0x65,
	0x61, 0x72, 0x63, 0x68, 0x4f, 0x77, 0x6e, 0x65, 0x72, 0x12, 0x1d, 0x2e, 0x63, 0x6f, 0x6f, 0x72,
	0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x53, 0x65, 0x61, 0x72, 0x63, 0x68, 0x4f, 0x77, 0x6e, 0x65,
	0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x10, 0x2e, 0x63, 0x6f, 0x6f, 0x72, 0x64,
	0x2e, 0x61, 0x70, 0x69, 0x2e, 0x4f, 0x77, 0x6e, 0x65, 0x72, 0x22, 0x00, 0x30, 0x01, 0x42, 0x38,
	0x5a, 0x36, 0x67, 0x69, 0x74, 0x68, 0x75, 0x62, 0x2e, 0x63, 0x6f, 0x6d, 0x2f, 0x6e, 0x65, 0x74,
	0x73, 0x79, 0x73, 0x2d, 0x6c, 0x61, 0x62, 0x2f, 0x73, 0x63, 0x69, 0x6f, 0x6e, 0x2d, 0x70, 0x65,
	0x65, 0x72, 0x69, 0x6e, 0x67, 0x2d, 0x63, 0x6f, 0x6f, 0x72, 0x64, 0x69, 0x6e, 0x61, 0x74, 0x6f,
	0x72, 0x2f, 0x67, 0x6f, 0x2f, 0x61, 0x70, 0x69, 0x62, 0x06, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x33,
}

var (
	file_api_info_proto_rawDescOnce sync.Once
	file_api_info_proto_rawDescData = file_api_info_proto_rawDesc
)

func file_api_info_proto_rawDescGZIP() []byte {
	file_api_info_proto_rawDescOnce.Do(func() {
		file_api_info_proto_rawDescData = protoimpl.X.CompressGZIP(file_api_info_proto_rawDescData)
	})
	return file_api_info_proto_rawDescData
}

var file_api_info_proto_msgTypes = make([]protoimpl.MessageInfo, 3)
var file_api_info_proto_goTypes = []interface{}{
	(*Owner)(nil),              // 0: coord.api.Owner
	(*GetOwnerRequest)(nil),    // 1: coord.api.GetOwnerRequest
	(*SearchOwnerRequest)(nil), // 2: coord.api.SearchOwnerRequest
}
var file_api_info_proto_depIdxs = []int32{
	1, // 0: coord.api.Info.GetOwner:input_type -> coord.api.GetOwnerRequest
	2, // 1: coord.api.Info.SearchOwner:input_type -> coord.api.SearchOwnerRequest
	0, // 2: coord.api.Info.GetOwner:output_type -> coord.api.Owner
	0, // 3: coord.api.Info.SearchOwner:output_type -> coord.api.Owner
	2, // [2:4] is the sub-list for method output_type
	0, // [0:2] is the sub-list for method input_type
	0, // [0:0] is the sub-list for extension type_name
	0, // [0:0] is the sub-list for extension extendee
	0, // [0:0] is the sub-list for field type_name
}

func init() { file_api_info_proto_init() }
func file_api_info_proto_init() {
	if File_api_info_proto != nil {
		return
	}
	if !protoimpl.UnsafeEnabled {
		file_api_info_proto_msgTypes[0].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*Owner); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_api_info_proto_msgTypes[1].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*GetOwnerRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_api_info_proto_msgTypes[2].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*SearchOwnerRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_api_info_proto_rawDesc,
			NumEnums:      0,
			NumMessages:   3,
			NumExtensions: 0,
			NumServices:   1,
		},
		GoTypes:           file_api_info_proto_goTypes,
		DependencyIndexes: file_api_info_proto_depIdxs,
		MessageInfos:      file_api_info_proto_msgTypes,
	}.Build()
	File_api_info_proto = out.File
	file_api_info_proto_rawDesc = nil
	file_api_info_proto_goTypes = nil
	file_api_info_proto_depIdxs = nil
}
