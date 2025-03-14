// Modify the Comp struct to add the prefetcher
type Comp struct {
	*sim.TickingComponent
	sim.MiddlewareHolder

	topPort     sim.Port
	bottomPort  sim.Port
	controlPort sim.Port

	dirStageBuffer           sim.Buffer
	dirToBankBuffers         []sim.Buffer
	writeBufferToBankBuffers []sim.Buffer
	mshrStageBuffer          sim.Buffer
	writeBufferBuffer        sim.Buffer

	topParser   *topParser
	writeBuffer *writeBufferStage
	dirStage    *directoryStage
	bankStages  []*bankStage
	mshrStage   *mshrStage
	flusher     *flusher

	storage             *mem.Storage
	addressToPortMapper mem.AddressToPortMapper
	directory           cache.Directory
	mshr                cache.MSHR
	log2BlockSize       uint64
	numReqPerCycle      int

	state                cacheState
	inFlightTransactions []*transaction
	evictingList         map[uint64]bool
	
	// Stride prefetcher
	prefetcher *StridePrefetcher
}
