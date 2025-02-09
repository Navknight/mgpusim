package runner

import (
	"fmt"
	"strings"
	"sync"

	"github.com/sarchlab/akita/v3/mem/mem"
	"github.com/sarchlab/akita/v3/tracing"
)

type countCacheWithAddrsTracer struct {
	sync.Mutex

	caches       []TraceableComponent
	cacheToSAMap map[string]int
	cacheAddrs   map[string]map[uint64]bool // Track which addresses are in which cache

	bottomReadCount int
	existsInSameSA  int
	existsInOtherSA int
}

func newCountCacheWithAddrsTracer(caches []TraceableComponent) *countCacheWithAddrsTracer {
	t := &countCacheWithAddrsTracer{
		caches:       caches,
		cacheToSAMap: make(map[string]int),
		cacheAddrs:   make(map[string]map[uint64]bool),
	}

	for _, cache := range caches {
		t.cacheAddrs[cache.Name()] = make(map[uint64]bool)
		parts := strings.Split(cache.Name(), ".")
		for _, part := range parts {
			if strings.HasPrefix(part, "SA[") {
				saID := part[3 : len(part)-1]
				t.cacheToSAMap[cache.Name()] = int(saID[0] - '0')
				break
			}
		}
	}

	return t
}

func (t *countCacheWithAddrsTracer) StartTask(task tracing.Task) {
	t.Lock()
	defer t.Unlock()

	switch task.What {
	case "read-hit":
		req, ok := task.Detail.(*mem.ReadReq)
		if ok {
			t.cacheAddrs[task.Where][req.Address] = true
		}
		break
	case "read-miss":
		req, ok := task.Detail.(*mem.ReadReq)
		if !ok {
			return
		}
		fmt.Println("read-miss")
		cacheName := task.Where
		currentSA := t.cacheToSAMap[cacheName]
		addr := req.Address

		t.bottomReadCount++
		existsInSameSA := false
		existsInOtherSA := false

		// Check if address exists in other caches
		for otherCache, addrs := range t.cacheAddrs {
			if otherCache == cacheName {
				continue
			}

			if addrs[addr] {
				otherSA := t.cacheToSAMap[otherCache]
				if currentSA == otherSA {
					existsInSameSA = true
				} else {
					existsInOtherSA = true
				}
			}
		}

		if existsInSameSA {
			t.existsInSameSA++
		}
		if existsInOtherSA {
			t.existsInOtherSA++
		}
		break
	default:
		fmt.Println(task.Steps)
	}
}

func (t *countCacheWithAddrsTracer) StepTask(task tracing.Task) {
	if task.What == "eviction" {
		fmt.Println("eviction")
		t.Lock()
		defer t.Unlock()

		cacheName := task.Where
		addr := task.Detail.(uint64)
		delete(t.cacheAddrs[cacheName], addr)
	}
}

func (t *countCacheWithAddrsTracer) EndTask(task tracing.Task) {}

func (t *countCacheWithAddrsTracer) GetStats() (total, sameShader, otherShader int) {
	t.Lock()
	defer t.Unlock()
	return t.bottomReadCount, t.existsInSameSA, t.existsInOtherSA
}
