#!/bin/sh
# Compiles the protobuf definitions.
# The info.proto and peering.proto files in ./api are linked from django/peering_coord/api .

protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    --proto_path=. ./api/info.proto

protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    --proto_path=. ./api/peering.proto
