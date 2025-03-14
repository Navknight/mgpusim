// Add these fields to the Builder struct
type Builder struct {
	// ... existing fields
	prefetcherEnabled bool
	prefetchDegree    int
	// ... existing fields
}

// Add these methods to the Builder
// WithPrefetcherEnabled enables or disables the stride prefetcher
func (b Builder) WithPrefetcherEnabled(enabled bool) Builder {
	b.prefetcherEnabled = enabled
	return b
}

// WithPrefetchDegree sets the number of addresses to prefetch at once
func (b Builder) WithPrefetchDegree(degree int) Builder {
	b.prefetchDegree = degree
	return b
}

// Modify MakeBuilder to set default values
func MakeBuilder() Builder {
	return Builder{
		freq:                1 * sim.GHz,
		wayAssociativity:    4,
		log2BlockSize:       6,
		byteSize:            512 * mem.KB,
		numMSHREntry:        16,
		numReqPerCycle:      1,
		writeBufferCapacity: 1024,
		maxInflightFetch:    128,
		maxInflightEviction: 128,
		bankLatency:         10,
		prefetcherEnabled:   false, // Prefetcher disabled by default
		prefetchDegree:      2,     // Prefetch 2 addresses at once when enabled
	}
}

// Modify the Build method to create the prefetcher if enabled
func (b Builder) Build(name string) *Comp {
	cache := new(Comp)
	cache.TickingComponent = sim.NewTickingComponent(
		name, b.engine, b.freq, cache)

	b.configureCache(cache)
	b.createPorts(cache)
	b.createInternalStages(cache)
	b.createInternalBuffers(cache)

	middleware := &middleware{Comp: cache}
	cache.AddMiddleware(middleware)

	// Create the prefetcher if enabled
	if b.prefetcherEnabled {
		cache.prefetcher = NewStridePrefetcher(cache, b.prefetchDegree)
	}

	return cache
}
