package main

import (
	"flag"
	"log"
	"os"
	"os/exec"
	"time"

	"gopkg.in/yaml.v3"
)

var (
	configFile  string
	config      ClientConfig
	connections []*Connection
)

type ConnectionConfig struct {
	Coord      string `yaml:"coord"`
	ClientName string `yaml:"clientName"`
	Secret     string `yaml:"secret"`
	Policies   string `yaml:"policies"`
	Interfaces []struct {
		Vlan        string `yaml:"vlan"`
		Ip          string `yaml:"ip"`
		FirstPort   uint16 `yaml:"firstPort"`
		LastPort    uint16 `yaml:"lastPort"`
		FirstLinkId uint32 `yaml:"firstLinkId"`
		LastLinkId  uint32 `yaml:"lastLinkId"`
	} `yaml:"interfaces"`
}

type ClientConfig struct {
	Asn            string             `yaml:"asn"`
	AsConfigPath   string             `yaml:"asConfigPath"`
	AsConfigScript string             `yaml:"asConfigScript"`
	asConfigDelay  int                `yaml:"asConfigDelay"`
	CtrlSocket     string             `yaml:"ctrlSocket"`
	Connections    []ConnectionConfig `yaml:"connections"`
}

type Policy struct {
	Vlan      string `yaml:"vlan"`
	Accept    bool   `yaml:"accept"`
	PeerAsn   string `yaml:"peerAsn,omitempty"`
	PeerOwner string `yaml:"peerOwner,omitempty"`
	PeerIsd   string `yaml:"peerIsd,omitempty"`
}

func main() {
	// Parse command line args
	flag.StringVar(&configFile, "c", "./config.yaml", "The client configuration file.")
	flag.Parse()

	// Parse configuration and policies
	config = parseConfig(configFile)
	for i, _ := range config.Connections {
		connections = append(connections,
			NewConnection(&config.Connections[i]))
	}

	// Connect to coordinator
	for _, conn := range connections {
		conn.Connect()
		defer conn.Disconnect()
	}

	// Periodically update links
	var topofile = config.AsConfigPath + "topology.yaml"
	for {
		restart := false
		for _, conn := range connections {
			if conn.InstallLinks(topofile) {
				restart = true
			}
		}
		if restart {
			cmd := exec.Command(config.AsConfigScript)
			cmd.Start()
			err := cmd.Wait()
			if err != nil {
				log.Printf("Restarting AS failed.")
			}
			restart = false
		}
		time.Sleep(time.Duration(config.asConfigDelay) * time.Second)
	}
}

func parseConfig(configFile string) ClientConfig {
	data, err := os.ReadFile(configFile)
	if err != nil {
		log.Fatalf("Error reading configuration file %s", configFile)
	}

	config := ClientConfig{}
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		log.Fatalf("Invalid configuration:\n%s\n", string(data))
	}

	return config
}

func parsePolicies(policyFile string) []Policy {
	data, err := os.ReadFile(policyFile)
	if err != nil {
		log.Fatalf("Error reading policy file %s", policyFile)
	}

	policies := make([]Policy, 0, 16)
	err = yaml.Unmarshal(data, &policies)
	if err != nil {
		log.Fatalf("Invalid policy file format:\n%v\n%s\n", err, string(data))
	}

	return policies
}
