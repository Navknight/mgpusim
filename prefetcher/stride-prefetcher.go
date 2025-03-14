package writeback

import (
	"fmt"

	"github.com/sarchlab/akita/v4/mem/cache"
	"github.com/sarchlab/akita/v4/mem/vm"
)

// StridePrefetcher detects regular memory access patterns (strides)
// and prefetches data ahead of actual requests.
type StridePrefetcher struct {
	// Cache component reference
	cache *Comp

	// Maximum number of prefetch requests to issue on a miss
	degree int

	// Recent memory accesses for each process
	// Map PID -> Map page address -> stride information
	accessHistory map[vm.PID]map[uint64]*strideInfo

	// Maximum number of pages to track per process
	maxTrackedPages int
}

// strideInfo tracks information about memory access patterns for a page
type strideInfo struct {
	// Last accessed address within this page
	lastAddr uint64

	// Previous address before lastAddr
	prevAddr uint64

	// Current detected stride
	stride int64

	// Confidence level (incremented when same stride detected)
	confidence int

	// Maximum confidence level
	maxConfidence int

	// Minimum confidence required to trigger prefetching
	prefetchThreshold int
}

// NewStridePrefetcher creates a new stride prefetcher
func NewStridePrefetcher(cache *Comp, degree int) *StridePrefetcher {
	return &StridePrefetcher{
		cache:           cache,
		degree:          degree,
		accessHistory:   make(map[vm.PID]map[uint64]*strideInfo),
		maxTrackedPages: 16, // Track up to 16 pages per process
	}
}

// RecordAccess records a memory access and updates stride information
func (p *StridePrefetcher) RecordAccess(pid vm.PID, addr uint64) {
	// Get the cache line address
	lineAddr, _ := getCacheLineID(addr, p.cache.log2BlockSize)

	// Ensure we have a map for this process
	if _, ok := p.accessHistory[pid]; !ok {
		p.accessHistory[pid] = make(map[uint64]*strideInfo)
	}

	// Track at page granularity (4KB pages)
	pageAddr := lineAddr >> 12
	info, ok := p.accessHistory[pid][pageAddr]

	if !ok {
		// First access to this page, initialize stride info
		info = &strideInfo{
			lastAddr:          lineAddr,
			prevAddr:          0,
			stride:            0,
			confidence:        0,
			maxConfidence:     3,
			prefetchThreshold: 2,
		}

		// If too many pages are tracked, remove one
		if len(p.accessHistory[pid]) >= p.maxTrackedPages {
			for k := range p.accessHistory[pid] {
				delete(p.accessHistory[pid], k)
				break
			}
		}

		p.accessHistory[pid][pageAddr] = info
		return
	}

	// Skip if it's the same address as the last access
	if lineAddr == info.lastAddr {
		return
	}

	// Calculate current stride
	currentStride := int64(lineAddr) - int64(info.lastAddr)

	// Update stride detection
	if info.prevAddr != 0 {
		prevStride := int64(info.lastAddr) - int64(info.prevAddr)

		if currentStride == prevStride && currentStride != 0 {
			// Same stride detected, increase confidence
			if info.confidence < info.maxConfidence {
				info.confidence++
			}
			info.stride = currentStride
		} else {
			// Different stride, decrease confidence
			if info.confidence > 0 {
				info.confidence--
			}
			// Only update stride if confidence is reset
			if info.confidence == 0 {
				info.stride = currentStride
			}
		}
	}

	// Update address history
	info.prevAddr = info.lastAddr
	info.lastAddr = lineAddr
}

// TryPrefetch attempts to prefetch data based on stride patterns
// Returns true if any prefetch request was issued
func (p *StridePrefetcher) TryPrefetch(pid vm.PID, addr uint64) bool {
	lineAddr, _ := getCacheLineID(addr, p.cache.log2BlockSize)
	pageAddr := lineAddr >> 12

	// Check if we have stride info with sufficient confidence
	if pidMap, ok := p.accessHistory[pid]; ok {
		if info, ok := pidMap[pageAddr]; ok {
			if info.confidence >= info.prefetchThreshold && info.stride != 0 {
				madeProgress := false

				// Generate prefetch addresses
				nextAddr := lineAddr + uint64(info.stride)
				for i := 0; i < p.degree; i++ {
					// Check if the address would be in the same or adjacent page
					nextPageAddr := nextAddr >> 12
					if (nextPageAddr == pageAddr || nextPageAddr == pageAddr+1) &&
						nextAddr != lineAddr {
						// Attempt to prefetch this address
						if p.issuePrefetch(pid, nextAddr) {
							madeProgress = true
						}
						nextAddr = nextAddr + uint64(info.stride)
					} else {
						break
					}
				}

				return madeProgress
			}
		}
	}

	return false
}

// issuePrefetch issues a prefetch request for the given address
// Returns true if a prefetch request was issued
func (p *StridePrefetcher) issuePrefetch(pid vm.PID, addr uint64) bool {
	// Check if the address is already in the cache
	if p.cache.directory.Lookup(pid, addr) != nil {
		return false
	}

	// Check if there's already an MSHR entry for this address
	if p.cache.mshr.Query(pid, addr) != nil {
		return false
	}

	// Check if the MSHR is full
	if p.cache.mshr.IsFull() {
		return false
	}

	// Find a victim block
	victim := p.cache.directory.FindVictim(addr)
	if victim == nil || victim.IsLocked || victim.ReadCount > 0 {
		return false
	}

	// Don't prefetch if it would require eviction of a dirty block
	if victim.IsValid && victim.IsDirty {
		return false
	}

	// Create a prefetch transaction
	prefetchTrans := &transaction{
		action:       writeBufferFetch,
		fetchPID:     pid,
		fetchAddress: addr,
		block:        victim,
	}

	// Create an MSHR entry for the prefetch
	mshrEntry := p.cache.mshr.Add(pid, addr)
	mshrEntry.Block = victim
	mshrEntry.Requests = append(mshrEntry.Requests, prefetchTrans)
	prefetchTrans.mshrEntry = mshrEntry

	// Setup the block
	victim.IsLocked = true
	victim.Tag = addr
	victim.IsValid = true
	victim.PID = pid

	// Send to write buffer for fetching
	if p.cache.writeBufferBuffer.CanPush() {
		p.cache.writeBufferBuffer.Push(prefetchTrans)
		
		// For debugging
		fmt.Printf("%.10f, %s, prefetch request issued, addr: %08X, stride: %d\n",
			p.cache.Engine.CurrentTime(), p.cache.Name(), addr, 
			p.accessHistory[pid][addr>>12].stride)
		
		return true
	}

	// If we couldn't push to the buffer, undo the changes
	p.cache.mshr.Remove(pid, addr)
	victim.IsLocked = false
	return false
}
