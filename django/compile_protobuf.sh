#!/bin/sh
# Compiles the protobuf definitions.

PROTO_PATH="./peering_coord/api"

python3 -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. $PROTO_PATH/info.proto
python3 -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. $PROTO_PATH/peering.proto
