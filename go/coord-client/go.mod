module github.com/netsys-lab/scion-peering-coordinator/go/coord-client

go 1.16

require (
	github.com/netsys-lab/scion-peering-coordinator/go/api v0.0.0-00010101000000-000000000000 // indirect
	google.golang.org/grpc v1.40.0 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
	gopkg.in/yaml.v3 v3.0.0-20210107192922-496545a6307b // indirect
)

replace github.com/netsys-lab/scion-peering-coordinator/go/api => ../api
