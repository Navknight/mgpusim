package runner

import (
	"github.com/sarchlab/akita/v3/noc/networking/nvlink"
	"github.com/sarchlab/akita/v3/noc/networking/pcie"
	"github.com/sarchlab/akita/v3/sim"
)

type gpuNetwork interface {
	addGPUSwitch() int
	plugInGPU(switchID int, ports []sim.Port)
	establishRoute()
}

type pcieNetwork struct {
	c    *pcie.Connector
	root int
}

func (n *pcieNetwork) addGPUSwitch() int {
	return n.c.AddSwitch(n.root)
}

func (n *pcieNetwork) plugInGPU(switchID int, ports []sim.Port) {
	n.c.PlugInDevice(switchID, ports)
}

func (n *pcieNetwork) establishRoute() {
	n.c.EstablishRoute()
}

type nvlinkNetwork struct {
	c        *nvlink.Connector
	root     int
	numLinks int
	gpus     []int
}

func (n *nvlinkNetwork) addGPUSwitch() int {
	sw := n.c.AddPCIeSwitch()
	n.c.ConnectSwitchesWithPCIeLink(n.root, sw)
	return sw
}

func (n *nvlinkNetwork) plugInGPU(switchID int, ports []sim.Port) {
	n.gpus = append(n.gpus, n.c.PlugInDevice(switchID, ports))
}

func (n *nvlinkNetwork) establishRoute() {
	for i := 0; i < len(n.gpus); i++ {
		for j := i + 1; j < len(n.gpus); j++ {
			n.c.ConnectDevicesWithNVLink(n.gpus[i], n.gpus[j], n.numLinks)
		}
	}
	n.c.EstablishRoute()
}
