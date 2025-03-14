// Modify handleReadMiss to integrate prefetcher
func (ds *directoryStage) handleReadMiss(trans *transaction) bool {
	req := trans.read
	cacheLineID, _ := getCacheLineID(req.Address, ds.cache.log2BlockSize)

	if ds.cache.mshr.IsFull() {
		return false
	}

	victim := ds.cache.directory.FindVictim(cacheLineID)
	if victim.IsLocked || victim.ReadCount > 0 {
		return false
	}

	// Record access in prefetcher
	if ds.cache.prefetcher != nil {
		ds.cache.prefetcher.RecordAccess(req.PID, req.Address)
	}

	tracing.AddTaskStep(
		tracing.MsgIDAtReceiver(trans.read, ds.cache),
		ds.cache,
		"read-miss",
	)

	var success bool
	if ds.needEviction(victim) {
		success = ds.evict(trans, victim)
	} else {
		success = ds.fetch(trans, victim)
	}

	// Try prefetching if the read miss was handled successfully
	if success && ds.cache.prefetcher != nil {
		ds.cache.prefetcher.TryPrefetch(req.PID, req.Address)
	}

	return success
}

// Modify writePartialLineMiss to integrate prefetcher
func (ds *directoryStage) writePartialLineMiss(trans *transaction) bool {
	write := trans.write
	cachelineID, _ := getCacheLineID(write.Address, ds.cache.log2BlockSize)

	if ds.cache.mshr.IsFull() {
		return false
	}

	victim := ds.cache.directory.FindVictim(cachelineID)
	if victim.IsLocked || victim.ReadCount > 0 {
		return false
	}

	// Record access in prefetcher
	if ds.cache.prefetcher != nil {
		ds.cache.prefetcher.RecordAccess(write.PID, write.Address)
	}

	var success bool
	if ds.needEviction(victim) {
		success = ds.evict(trans, victim)
	} else {
		success = ds.fetch(trans, victim)
	}

	// Try prefetching if the write miss was handled successfully
	if success && ds.cache.prefetcher != nil {
		ds.cache.prefetcher.TryPrefetch(write.PID, write.Address)
	}

	return success
}

// Also modify the hit functions to record accesses
func (ds *directoryStage) handleReadHit(
	trans *transaction,
	block *cache.Block,
) bool {
	if block.IsLocked {
		return false
	}

	// Record access in prefetcher
	if ds.cache.prefetcher != nil {
		ds.cache.prefetcher.RecordAccess(trans.read.PID, trans.read.Address)
	}

	tracing.AddTaskStep(
		tracing.MsgIDAtReceiver(trans.read, ds.cache),
		ds.cache,
		"read-hit",
	)

	return ds.readFromBank(trans, block)
}

func (ds *directoryStage) doWriteHit(
	trans *transaction,
	block *cache.Block,
) bool {
	if block.IsLocked || block.ReadCount > 0 {
		return false
	}

	// Record access in prefetcher
	if ds.cache.prefetcher != nil {
		ds.cache.prefetcher.RecordAccess(trans.write.PID, trans.write.Address)
	}

	return ds.writeToBank(trans, block)
}
