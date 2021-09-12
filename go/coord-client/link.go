package main

import (
	"log"
	"sync"
)

type LinkFlags uint8

const (
	LINK_FLAG_INSTALLED LinkFlags = 1 << iota
	LINK_FLAG_CREATE
	LINK_FLAG_DESTROY
)

const (
	LINK_TYPE_PEERING  int = 0
	LINK_TYPE_CORE     int = 1
	LINK_TYPE_PROVIDER int = 2
)

type Link struct {
	LinkType   int
	PeerAsn    string
	LocalIp    string
	LocalPort  uint16
	RemoteIp   string
	RemotePort uint16
}

type LinkData struct {
	Flags  LinkFlags
	LinkId int
}

type Links struct {
	mutex *sync.Mutex
	links map[Link]LinkData
}

func NewLinks() Links {
	return Links{mutex: &sync.Mutex{}, links: make(map[Link]LinkData)}
}

func (links Links) Add(add *Link) {
	links.mutex.Lock()
	_, exists := links.links[*add]
	if !exists {
		links.links[*add] = LinkData{Flags: LINK_FLAG_CREATE, LinkId: 0}
	}
	links.mutex.Unlock()
}

func (links Links) Remove(remove *Link) {
	links.mutex.Lock()
	data, exists := links.links[*remove]
	if exists {
		if (data.Flags & LINK_FLAG_INSTALLED) != 0 {
			data.Flags |= LINK_FLAG_DESTROY
			links.links[*remove] = data
		} else {
			delete(links.links, *remove)
		}
	}
	links.mutex.Unlock()
}

func (links Links) Install(topologyFile string) bool {
	var restart bool = false

	links.mutex.Lock()
	for link, data := range links.links {
		if (data.Flags & LINK_FLAG_INSTALLED) == 0 {
			if (data.Flags & LINK_FLAG_CREATE) != 0 {
				log.Printf("Create link: %v\n", link)
				data.Flags |= LINK_FLAG_INSTALLED
				data.Flags &= ^LINK_FLAG_CREATE
				links.links[link] = data
				restart = true
			} else {
				log.Printf("Destroy link: %v\n", link)
				delete(links.links, link)
				restart = true
			}
		}
	}
	links.mutex.Unlock()

	return restart
}
