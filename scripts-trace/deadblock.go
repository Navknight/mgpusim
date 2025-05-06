package main

import (
	"bufio"
	"encoding/csv"
	"flag"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"gonum.org/v1/plot"
	"gonum.org/v1/plot/plotter"
	"gonum.org/v1/plot/plotutil"
	"gonum.org/v1/plot/vg"
)

// WriteAroundCache configuration parameters
const (
	CacheSize     = 16 * 1024 // 16 KB for L1 cache
	BlockSize     = 64        // 64 bytes per block
	Associativity = 4         // 4-way set associative
	NumSets       = CacheSize / (BlockSize * Associativity)
	NumBanks      = 4
)

var DeadAccessCount = 1

// Cache Block States
const (
	Invalid = iota
	Valid
	Modified
	Locked
)

// Block represents a cache block
type Block struct {
	Tag           uint64   // Tag bits of the address
	SetID         int      // Set ID this block belongs to
	WayID         int      // Way ID within the set
	State         int      // Block state (Valid, Invalid, etc.)
	AccessCount   int      // Number of times the block is accessed
	ReadCount     int      // Number of pending reads
	LastUseTime   float64  // Last time the block was accessed
	IsEvicted     bool     // Whether the block has been evicted
	IsDirty       bool     // Whether the block has been modified
	DirtyMask     []bool   // Byte-level dirty mask
	WasPrefetched bool     // Whether block was prefetched
	References    []uint64 // Individual addresses accessed
	IsRead        []bool   // Whether each reference was a read
}

// Set represents a cache set
type Set struct {
	Blocks []*Block // Blocks in this set
}

// MSHR entry for tracking outstanding misses
type MSHREntry struct {
	Address      uint64
	IsWrite      bool
	PendingCount int
	ResolveTime  float64 // When the miss is expected to resolve
}

// MSHR for tracking outstanding misses
type MSHR struct {
	Entries    []*MSHREntry
	MaxEntries int
}

// WriteAroundCache represents the cache with write-around policy
type WriteAroundCache struct {
	Sets           []*Set
	MSHR           *MSHR
	AccessMap      map[uint64]*Block // For tracking blocks
	BankAccesses   []int             // Count of accesses per bank
	TotalEvictions uint64
	WasHit         []bool    // For each access, was it a hit?
	WasReadHit     []bool    // For each read, was it a hit?
	WasWriteHit    []bool    // For each write, was it a hit?
	AccTime        []float64 // Access timestamps
	Utilization    []float64 // Cache utilization over time
}

// BenchmarkResult represents the result of analyzing a benchmark
type BenchmarkResult struct {
	Name                 string
	DeadPercentage       float64
	DeadCount            int
	TotalCount           int
	AvgDeadInCache       float64
	DeadPercentages      []float64
	AccessDistribution   map[string]int
	WriteAroundMissCount int
	WriteMissCount       int
	WriteHitCount        int
	ReadMissCount        int
	ReadHitCount         int
	HitRate              float64
	ReadHitRate          float64
	WriteHitRate         float64
	BankStats            []int
}

// NewMSHR creates a new MSHR
func NewMSHR(maxEntries int) *MSHR {
	return &MSHR{
		Entries:    make([]*MSHREntry, 0, maxEntries),
		MaxEntries: maxEntries,
	}
}

// IsFull returns true if MSHR is full
func (m *MSHR) IsFull() bool {
	return len(m.Entries) >= m.MaxEntries
}

// Add adds an entry to MSHR
func (m *MSHR) Add(address uint64, isWrite bool, resolveTime float64) *MSHREntry {
	for _, entry := range m.Entries {
		if entry.Address == address {
			entry.PendingCount++
			return entry
		}
	}

	entry := &MSHREntry{
		Address:      address,
		IsWrite:      isWrite,
		PendingCount: 1,
		ResolveTime:  resolveTime,
	}
	m.Entries = append(m.Entries, entry)
	return entry
}

// Query checks if an address is already in MSHR
func (m *MSHR) Query(address uint64) *MSHREntry {
	for _, entry := range m.Entries {
		if entry.Address == address {
			return entry
		}
	}
	return nil
}

// Remove removes an entry from MSHR
func (m *MSHR) Remove(address uint64) {
	for i, entry := range m.Entries {
		if entry.Address == address {
			m.Entries = append(m.Entries[:i], m.Entries[i+1:]...)
			return
		}
	}
}

// CheckResolutions checks for MSHR entries that should be resolved
func (m *MSHR) CheckResolutions(currentTime float64, handler func(entry *MSHREntry)) {
	var remainingEntries []*MSHREntry

	for _, entry := range m.Entries {
		if entry.ResolveTime <= currentTime {
			handler(entry)
		} else {
			remainingEntries = append(remainingEntries, entry)
		}
	}

	m.Entries = remainingEntries
}

// NewWriteAroundCache creates a new cache
func NewWriteAroundCache() *WriteAroundCache {
	cache := &WriteAroundCache{
		Sets:         make([]*Set, NumSets),
		MSHR:         NewMSHR(16), // 16 MSHR entries
		AccessMap:    make(map[uint64]*Block),
		BankAccesses: make([]int, NumBanks),
	}

	for i := 0; i < NumSets; i++ {
		cache.Sets[i] = &Set{
			Blocks: make([]*Block, 0, Associativity),
		}
	}

	return cache
}

// GetSetIndex returns the set index for a given address
func GetSetIndex(addr uint64) int {
	return int((addr / BlockSize) % NumSets)
}

// GetBankIndex returns the bank index for a given block
func GetBankIndex(setID int, wayID int) int {
	blockID := setID*Associativity + wayID
	return blockID % NumBanks
}

// GetBlockAddress returns the block-aligned address for a given address
func GetBlockAddress(addr uint64) uint64 {
	return addr / BlockSize * BlockSize
}

// ProcessAccess processes a memory access with write-around policy
func (c *WriteAroundCache) ProcessAccess(time float64, addr uint64, isRead bool, size uint64) {
	// First check for any memory returns that should complete by now
	c.MSHR.CheckResolutions(time, func(entry *MSHREntry) {
		c.SimulateDataReturn(entry.ResolveTime, entry.Address)
	})

	blockAddr := GetBlockAddress(addr)
	setIndex := GetSetIndex(blockAddr)
	set := c.Sets[setIndex]

	// For tracking hit rates
	if isRead {
		c.WasReadHit = append(c.WasReadHit, false)
	} else {
		c.WasWriteHit = append(c.WasWriteHit, false)
	}
	c.WasHit = append(c.WasHit, false)
	c.AccTime = append(c.AccTime, time)

	// Check if in MSHR (in-flight miss)
	mshrEntry := c.MSHR.Query(blockAddr)
	if mshrEntry != nil {
		// Already in MSHR, just return
		c.updateUtilization(time)
		return
	}

	// Check if already in cache
	var block *Block
	var blockIndex int = -1
	for i, b := range set.Blocks {
		if b.Tag == blockAddr && b.State != Invalid {
			block = b
			blockIndex = i
			break
		}
	}

	if block != nil {
		// Cache hit
		if block.State == Locked {
			// Block is locked, treat as miss
			if !isRead {
				// For write, just forward to memory with write-around
				c.updateUtilization(time)
				return
			} else {
				// For read, track in MSHR
				// Add to MSHR with a resolve time (100 cycles later)
				c.MSHR.Add(blockAddr, false, time+100.0)
				c.updateUtilization(time)
				return
			}
		}

		// Update block info
		block.AccessCount++
		block.LastUseTime = time
		block.References = append(block.References, addr)
		block.IsRead = append(block.IsRead, isRead)

		// Mark appropriate hit statistics
		c.WasHit[len(c.WasHit)-1] = true
		if isRead {
			c.WasReadHit[len(c.WasReadHit)-1] = true
			block.ReadCount++ // Track read references
		} else {
			c.WasWriteHit[len(c.WasWriteHit)-1] = true

			// Write hit is handled by writing to cache
			block.IsDirty = true

			// Update dirty mask - simplified version
			offset := int(addr - blockAddr)
			if block.DirtyMask == nil {
				block.DirtyMask = make([]bool, BlockSize)
			}

			for i := offset; i < offset+int(size) && i < len(block.DirtyMask); i++ {
				block.DirtyMask[i] = true
			}
		}

		// Update LRU position - move to MRU position
		if blockIndex < len(set.Blocks)-1 {
			temp := block
			copy(set.Blocks[blockIndex:], set.Blocks[blockIndex+1:])
			set.Blocks[len(set.Blocks)-1] = temp
		}

		// Update bank statistics
		bankIndex := GetBankIndex(setIndex, block.WayID)
		c.BankAccesses[bankIndex]++

		c.updateUtilization(time)
		return
	}

	// Cache miss
	if isRead {
		// Handle read miss
		// First check MSHR capacity
		if c.MSHR.IsFull() {
			c.updateUtilization(time)
			return // Stall, MSHR is full
		}

		// Add to MSHR with a resolve time (100 cycles later)
		c.MSHR.Add(blockAddr, false, time+100.0)

		// Find victim if needed and allocate
		if len(set.Blocks) >= Associativity {
			// Need to evict - find LRU block
			victim := set.Blocks[0] // LRU is at position 0

			if victim.State == Locked || victim.ReadCount > 0 {
				// Can't evict, stall
				c.updateUtilization(time)
				return
			}

			// Track eviction
			victim.IsEvicted = true
			c.TotalEvictions++

			// Remove from set
			copy(set.Blocks[:], set.Blocks[1:])
			set.Blocks = set.Blocks[:len(set.Blocks)-1]
		}

		// Create new block
		wayID := len(set.Blocks)
		block = &Block{
			Tag:         blockAddr,
			SetID:       setIndex,
			WayID:       wayID,
			State:       Locked, // Block is locked until data arrives
			AccessCount: 1,
			LastUseTime: time,
			IsDirty:     false,
			DirtyMask:   make([]bool, BlockSize),
			References:  []uint64{addr},
			IsRead:      []bool{isRead},
		}

		// Add to cache and tracking map
		set.Blocks = append(set.Blocks, block)
		c.AccessMap[blockAddr] = block

		// Update bank statistics
		bankIndex := GetBankIndex(setIndex, wayID)
		c.BankAccesses[bankIndex]++
	} else {
		// Write miss with write-around policy
		// Write misses bypass the cache, data sent directly to memory
		// No block allocation, no MSHR entry

		// Just record the write-around miss for statistics
		// This is a key feature of the write-around cache design
	}

	c.updateUtilization(time)
}

// SimulateDataReturn simulates when data returns from memory to resolve a miss
func (c *WriteAroundCache) SimulateDataReturn(time float64, addr uint64) {
	blockAddr := GetBlockAddress(addr)

	setIndex := GetSetIndex(blockAddr)
	set := c.Sets[setIndex]

	// Find the block
	var block *Block
	for _, b := range set.Blocks {
		if b.Tag == blockAddr {
			block = b
			break
		}
	}

	if block != nil {
		// Update block state
		block.State = Valid
		block.ReadCount = 0 // Reset read count

		// If this was a prefetch that now completed
		if block.WasPrefetched {
			block.WasPrefetched = false
		}
	}

	// Remove from MSHR
	c.MSHR.Remove(blockAddr)
}

// Calculate cache utilization (percentage of blocks that have valid data)
func (c *WriteAroundCache) updateUtilization(time float64) {
	totalBlocks := NumSets * Associativity
	validBlocks := 0

	for _, set := range c.Sets {
		for _, block := range set.Blocks {
			if block.State != Invalid {
				validBlocks++
			}
		}
	}

	utilization := float64(validBlocks) / float64(totalBlocks) * 100.0
	c.Utilization = append(c.Utilization, utilization)
}

// FinalizeCache marks all blocks in the cache as evicted at the end of simulation
func (c *WriteAroundCache) FinalizeCache(finalTime float64) {
	// Process any pending memory returns
	c.MSHR.CheckResolutions(finalTime, func(entry *MSHREntry) {
		c.SimulateDataReturn(entry.ResolveTime, entry.Address)
	})

	// Mark all blocks in sets as evicted for tracking
	for _, set := range c.Sets {
		for _, block := range set.Blocks {
			block.IsEvicted = true
		}
	}

	// Also handle any remaining entries in MSHR
	for _, entry := range c.MSHR.Entries {
		c.SimulateDataReturn(finalTime, entry.Address)
	}
}

// CalculateDeadBlockPercentage calculates the percentage of dead blocks
func (c *WriteAroundCache) CalculateDeadBlockPercentage() (float64, int, int) {
	totalEvicted := 0
	deadBlocks := 0

	for _, block := range c.AccessMap {
		if block.IsEvicted {
			totalEvicted++
			if block.AccessCount <= DeadAccessCount {
				deadBlocks++
			}
		}
	}

	percentage := 0.0
	if totalEvicted > 0 {
		percentage = float64(deadBlocks) / float64(totalEvicted) * 100.0
	}

	return percentage, deadBlocks, totalEvicted
}

// GetBlockAccessDistribution returns the histogram of block accesses
func (c *WriteAroundCache) GetBlockAccessDistribution() map[string]int {
	maxAccess := 0
	for _, block := range c.AccessMap {
		if block.AccessCount > maxAccess {
			maxAccess = block.AccessCount
		}
	}

	// Create histogram buckets
	buckets := make([]int, maxAccess+1)
	for _, block := range c.AccessMap {
		if block.IsEvicted {
			buckets[block.AccessCount]++
		}
	}

	// Create summarized distribution for higher access counts
	ranges := []struct {
		min int
		max int
		key string
	}{
		{1, 1, "1"},
		{2, 2, "2"},
		{3, 5, "3-5"},
		{6, 10, "6-10"},
		{11, 20, "11-20"},
		{21, 50, "21-50"},
		{51, 100, "51-100"},
		{101, math.MaxInt, "101+"},
	}

	result := make(map[string]int)

	for _, r := range ranges {
		count := 0
		for i := r.min; i <= r.max && i <= maxAccess; i++ {
			count += buckets[i]
		}

		if count > 0 {
			result[r.key] = count
		}
	}

	return result
}

// CalculateAverageDeadBlocksInCache calculates the percentage of blocks in the cache that are dead
func (c *WriteAroundCache) CalculateAverageDeadBlocksInCache() (float64, []float64) {
	// This is an approximation since we don't have perfect time-based snapshots
	// We'll sample at each unique timestamp in the trace

	timestamps := make(map[float64]bool)
	for _, time := range c.AccTime {
		timestamps[time] = true
	}

	// Convert to sorted slice
	timeList := make([]float64, 0, len(timestamps))
	for t := range timestamps {
		timeList = append(timeList, t)
	}
	sort.Float64s(timeList)

	// For each timestamp, calculate the dead block percentage
	deadPercentages := make([]float64, 0, len(timeList))
	totalPercentage := 0.0

	for _, time := range timeList {
		deadCount := 0
		totalCount := 0

		for _, set := range c.Sets {
			for _, block := range set.Blocks {
				if block.LastUseTime <= time && block.State != Invalid {
					totalCount++
					// A block is potentially dead if it hasn't been accessed again
					future := false
					for _, b := range c.AccessMap {
						if b.Tag == block.Tag && b.SetID == block.SetID && b.LastUseTime > time {
							future = true
							break
						}
					}
					if !future {
						deadCount++
					}
				}
			}
		}

		percentage := 0.0
		if totalCount > 0 {
			percentage = float64(deadCount) / float64(totalCount) * 100.0
		}

		deadPercentages = append(deadPercentages, percentage)
		totalPercentage += percentage
	}

	avgPercentage := 0.0
	if len(deadPercentages) > 0 {
		avgPercentage = totalPercentage / float64(len(deadPercentages))
	}

	return avgPercentage, deadPercentages
}

// CalculateHitRates returns detailed hit rate statistics
func (c *WriteAroundCache) CalculateHitRates() (float64, float64, float64, int, int, int, int) {
	totalAccesses := len(c.WasHit)
	hitCount := 0

	readCount := len(c.WasReadHit)
	readHitCount := 0

	writeCount := len(c.WasWriteHit)
	writeHitCount := 0

	for _, wasHit := range c.WasHit {
		if wasHit {
			hitCount++
		}
	}

	for _, wasHit := range c.WasReadHit {
		if wasHit {
			readHitCount++
		}
	}

	for _, wasHit := range c.WasWriteHit {
		if wasHit {
			writeHitCount++
		}
	}

	hitRate := 0.0
	if totalAccesses > 0 {
		hitRate = float64(hitCount) / float64(totalAccesses) * 100.0
	}

	readHitRate := 0.0
	if readCount > 0 {
		readHitRate = float64(readHitCount) / float64(readCount) * 100.0
	}

	writeHitRate := 0.0
	if writeCount > 0 {
		writeHitRate = float64(writeHitCount) / float64(writeCount) * 100.0
	}

	return hitRate, readHitRate, writeHitRate, readHitCount, readCount - readHitCount, writeHitCount, writeCount - writeHitCount
}

// AnalyzeTraceFile analyzes a single trace file and returns the results
func AnalyzeTraceFile(filePath string, deadThreshold int) (*BenchmarkResult, error) {
	// Set the dead access count threshold for this analysis
	DeadAccessCount = deadThreshold

	// Open trace file
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("error opening file: %v", err)
	}
	defer file.Close()

	// Get benchmark name from file path
	benchmarkName := filepath.Base(filepath.Dir(filePath))

	reader := csv.NewReader(bufio.NewReader(file))

	// Skip header if present
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("error reading header: %v", err)
	}

	// Check if this is a header or data row
	isHeader := true
	for _, field := range header {
		if strings.Contains(field, "0x") {
			isHeader = false
			break
		}
	}

	// Create cache simulator
	cache := NewWriteAroundCache()
	sourceMap := make(map[uint64]string) // Map block addresses to sources

	// Process trace
	var lineCount uint64 = 0
	var lastTime float64 = 0

	processRow := func(row []string) error {
		lineCount++

		if len(row) < 5 {
			return fmt.Errorf("invalid row format at line %d", lineCount)
		}

		// Parse time
		time, err := strconv.ParseFloat(row[0], 64)
		if err != nil {
			return fmt.Errorf("invalid time format at line %d: %v", lineCount, err)
		}
		lastTime = time

		// Parse address
		addrStr := strings.TrimPrefix(row[1], "0x")
		addr, err := strconv.ParseUint(addrStr, 16, 64)
		if err != nil {
			return fmt.Errorf("invalid address format at line %d: %v", lineCount, err)
		}

		// Parse size
		size, err := strconv.ParseUint(row[2], 10, 64)
		if err != nil {
			return fmt.Errorf("invalid size at line %d: %v", lineCount, err)
		}

		// Parse if read or write
		isRead, err := strconv.ParseInt(row[3], 10, 64)
		if err != nil {
			return fmt.Errorf("invalid read/write flag at line %d: %v", lineCount, err)
		}

		// Get source
		source := row[4]
		sourceMap[GetBlockAddress(addr)] = source

		// Process the access
		cache.ProcessAccess(time, addr, isRead == 1, size)

		return nil
	}

	// If the first row wasn't a header, process it
	if !isHeader {
		if err := processRow(header); err != nil {
			return nil, err
		}
	}

	// Process the rest of the rows
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("error reading trace: %v", err)
		}

		if err := processRow(row); err != nil {
			return nil, err
		}
	}

	// Finalize cache to mark all blocks as evicted
	cache.FinalizeCache(lastTime)

	// Calculate dead block percentage
	percentage, deadCount, totalCount := cache.CalculateDeadBlockPercentage()

	// Calculate average dead blocks in cache at any time
	avgDeadInCache, deadPercentages := cache.CalculateAverageDeadBlocksInCache()

	// Get access distribution
	accessDistribution := cache.GetBlockAccessDistribution()

	// Calculate hit rates
	hitRate, readHitRate, writeHitRate, readHits, readMisses, writeHits, writeMisses := cache.CalculateHitRates()

	// Create result
	result := &BenchmarkResult{
		Name:                 benchmarkName,
		DeadPercentage:       percentage,
		DeadCount:            deadCount,
		TotalCount:           totalCount,
		AvgDeadInCache:       avgDeadInCache,
		DeadPercentages:      deadPercentages,
		AccessDistribution:   accessDistribution,
		WriteAroundMissCount: writeMisses,
		WriteMissCount:       writeMisses,
		WriteHitCount:        writeHits,
		ReadMissCount:        readMisses,
		ReadHitCount:         readHits,
		HitRate:              hitRate,
		ReadHitRate:          readHitRate,
		WriteHitRate:         writeHitRate,
		BankStats:            cache.BankAccesses,
	}

	return result, nil
}

// PrintBenchmarkResult prints the analysis results for a benchmark
func PrintBenchmarkResult(result *BenchmarkResult) {
	fmt.Printf("\nBenchmark: %s\n", result.Name)
	fmt.Printf("=====================================\n")
	fmt.Printf("Dead block percentage: %.2f%%\n", result.DeadPercentage)
	fmt.Printf("Dead blocks (accessed <= %d time(s)): %d\n", DeadAccessCount, result.DeadCount)
	fmt.Printf("Total evicted blocks: %d\n", result.TotalCount)
	fmt.Printf("Average percentage of dead blocks in the cache: %.2f%%\n", result.AvgDeadInCache)

	fmt.Printf("\nHit Rate Statistics:\n")
	fmt.Printf("Overall hit rate: %.2f%%\n", result.HitRate)
	fmt.Printf("Read hit rate: %.2f%%\n", result.ReadHitRate)
	fmt.Printf("Write hit rate: %.2f%%\n", result.WriteHitRate)
	fmt.Printf("Read hits/misses: %d / %d\n", result.ReadHitCount, result.ReadMissCount)
	fmt.Printf("Write hits/misses: %d / %d\n", result.WriteHitCount, result.WriteMissCount)
	fmt.Printf("Write-Around misses: %d\n", result.WriteAroundMissCount)

	fmt.Printf("\nBank Statistics:\n")
	for i, accesses := range result.BankStats {
		fmt.Printf("Bank %d: %d accesses\n", i, accesses)
	}

	// Print access distribution
	fmt.Println("\nAccess Count Distribution:")
	fmt.Println("Access Range | Block Count | Percentage")
	fmt.Println("----------------------------------------")

	// Sort the ranges for consistent output
	ranges := []string{"1", "2", "3-5", "6-10", "11-20", "21-50", "51-100", "101+"}
	for _, r := range ranges {
		if count, ok := result.AccessDistribution[r]; ok {
			percentage := float64(count) / float64(result.TotalCount) * 100.0
			fmt.Printf("%12s | %11d | %9.2f%%\n", r, count, percentage)
		}
	}
}

// GenerateDeadBlocksBarChart generates a bar chart of dead block percentages
func GenerateDeadBlocksBarChart(results []*BenchmarkResult, outputPath string) error {
	p := plot.New()

	p.Title.Text = "Dead Block Percentages by Benchmark"
	p.Y.Label.Text = "Percentage (%)"
	p.X.Label.Text = "Benchmark"

	// Create the bars
	groupNames := make([]string, len(results))
	values := make(plotter.Values, len(results))

	for i, result := range results {
		groupNames[i] = result.Name
		values[i] = result.DeadPercentage
	}

	// Create the bar chart
	bars, err := plotter.NewBarChart(values, vg.Points(20))
	if err != nil {
		return fmt.Errorf("error creating bar chart: %v", err)
	}

	bars.LineStyle.Width = vg.Length(0)
	bars.Color = plotutil.Color(0)

	p.Add(bars)

	// Set the X axis labels
	p.NominalX(groupNames...)

	// Save the plot
	if err := p.Save(8*vg.Inch, 6*vg.Inch, outputPath); err != nil {
		return fmt.Errorf("error saving chart: %v", err)
	}

	return nil
}

// GenerateHitRateBarChart generates a bar chart of hit rates
func GenerateHitRateBarChart(results []*BenchmarkResult, outputPath string) error {
	p := plot.New()

	p.Title.Text = "Cache Hit Rates by Benchmark"
	p.Y.Label.Text = "Hit Rate (%)"
	p.X.Label.Text = "Benchmark"

	// Create the bars for different hit rates
	groupNames := make([]string, len(results))
	overallValues := make(plotter.Values, len(results))
	readValues := make(plotter.Values, len(results))
	writeValues := make(plotter.Values, len(results))

	for i, result := range results {
		groupNames[i] = result.Name
		overallValues[i] = result.HitRate
		readValues[i] = result.ReadHitRate
		writeValues[i] = result.WriteHitRate
	}

	// Width of each bar
	width := vg.Points(20)

	// Create the bar charts
	overallBars, err := plotter.NewBarChart(overallValues, width)
	if err != nil {
		return fmt.Errorf("error creating overall bars chart: %v", err)
	}
	overallBars.LineStyle.Width = vg.Length(0)
	overallBars.Color = plotutil.Color(0)
	overallBars.Offset = -width

	readBars, err := plotter.NewBarChart(readValues, width)
	if err != nil {
		return fmt.Errorf("error creating read bars chart: %v", err)
	}
	readBars.LineStyle.Width = vg.Length(0)
	readBars.Color = plotutil.Color(1)
	readBars.Offset = 0

	writeBars, err := plotter.NewBarChart(writeValues, width)
	if err != nil {
		return fmt.Errorf("error creating write bars chart: %v", err)
	}
	writeBars.LineStyle.Width = vg.Length(0)
	writeBars.Color = plotutil.Color(2)
	writeBars.Offset = width

	p.Add(overallBars, readBars, writeBars)
	p.Legend.Add("Overall", overallBars)
	p.Legend.Add("Read", readBars)
	p.Legend.Add("Write", writeBars)

	// Set the X axis labels
	p.NominalX(groupNames...)

	// Save the plot
	if err := p.Save(10*vg.Inch, 6*vg.Inch, outputPath); err != nil {
		return fmt.Errorf("error saving chart: %v", err)
	}

	return nil
}

// GenerateBankDistributionChart generates a bar chart of bank access distribution
func GenerateBankDistributionChart(results []*BenchmarkResult, outputPath string) error {
	p := plot.New()

	p.Title.Text = "Bank Access Distribution"
	p.Y.Label.Text = "Percentage of Accesses (%)"
	p.X.Label.Text = "Bank"

	// We'll use the first benchmark for bank distribution
	if len(results) == 0 {
		return fmt.Errorf("no results to generate bank distribution")
	}

	result := results[0]
	bankNames := make([]string, len(result.BankStats))
	values := make(plotter.Values, len(result.BankStats))

	totalAccesses := 0
	for _, count := range result.BankStats {
		totalAccesses += count
	}

	for i, count := range result.BankStats {
		bankNames[i] = fmt.Sprintf("Bank %d", i)
		if totalAccesses > 0 {
			values[i] = float64(count) / float64(totalAccesses) * 100.0
		} else {
			values[i] = 0
		}
	}

	// Create the bar chart
	bars, err := plotter.NewBarChart(values, vg.Points(20))
	if err != nil {
		return fmt.Errorf("error creating bar chart: %v", err)
	}

	bars.LineStyle.Width = vg.Length(0)
	bars.Color = plotutil.Color(0)

	p.Add(bars)

	// Set the X axis labels
	p.NominalX(bankNames...)

	// Save the plot
	if err := p.Save(8*vg.Inch, 6*vg.Inch, outputPath); err != nil {
		return fmt.Errorf("error saving chart: %v", err)
	}

	return nil
}

// Generate a CSV summary of the results
func GenerateCSVSummary(results []*BenchmarkResult, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("error creating CSV file: %v", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	header := []string{
		"Benchmark",
		"Dead Block Percentage",
		"Dead Count",
		"Total Count",
		"Avg Dead In Cache",
		"Overall Hit Rate",
		"Read Hit Rate",
		"Write Hit Rate",
		"Read Hits",
		"Read Misses",
		"Write Hits",
		"Write Misses",
		"Write-Around Misses",
		"Bank0",
		"Bank1",
		"Bank2",
		"Bank3",
		"Access Count 1",
		"Access Count 2",
		"Access Count 3-5",
		"Access Count 6-10",
		"Access Count 11-20",
		"Access Count 21-50",
		"Access Count 51-100",
		"Access Count 101+",
	}

	if err := writer.Write(header); err != nil {
		return fmt.Errorf("error writing CSV header: %v", err)
	}

	// Write data rows
	for _, result := range results {
		row := []string{
			result.Name,
			fmt.Sprintf("%.2f", result.DeadPercentage),
			fmt.Sprintf("%d", result.DeadCount),
			fmt.Sprintf("%d", result.TotalCount),
			fmt.Sprintf("%.2f", result.AvgDeadInCache),
			fmt.Sprintf("%.2f", result.HitRate),
			fmt.Sprintf("%.2f", result.ReadHitRate),
			fmt.Sprintf("%.2f", result.WriteHitRate),
			fmt.Sprintf("%d", result.ReadHitCount),
			fmt.Sprintf("%d", result.ReadMissCount),
			fmt.Sprintf("%d", result.WriteHitCount),
			fmt.Sprintf("%d", result.WriteMissCount),
			fmt.Sprintf("%d", result.WriteAroundMissCount),
		}

		// Add bank statistics
		for _, bank := range result.BankStats {
			row = append(row, fmt.Sprintf("%d", bank))
		}

		// Add access distribution
		ranges := []string{"1", "2", "3-5", "6-10", "11-20", "21-50", "51-100", "101+"}
		for _, r := range ranges {
			count, ok := result.AccessDistribution[r]
			if ok {
				row = append(row, fmt.Sprintf("%d", count))
			} else {
				row = append(row, "0")
			}
		}

		if err := writer.Write(row); err != nil {
			return fmt.Errorf("error writing CSV row: %v", err)
		}
	}

	return nil
}

func main() {
	// Parse command line flags
	benchmarkDir := flag.String("dir", "", "Path to the directory containing benchmark folders")
	outputDir := flag.String("output", "results", "Path to the directory to store results")
	deadThreshold := flag.Int("threshold", 1, "Access count threshold to consider a block dead (default: 1)")
	flag.Parse()

	if *benchmarkDir == "" {
		fmt.Println("Please specify a benchmark directory using the -dir flag")
		flag.Usage()
		os.Exit(1)
	}

	// Create output directory if it doesn't exist
	if err := os.MkdirAll(*outputDir, 0755); err != nil {
		fmt.Printf("Error creating output directory: %v\n", err)
		os.Exit(1)
	}

	// Find all benchmarks in the directory
	entries, err := os.ReadDir(*benchmarkDir)
	if err != nil {
		fmt.Printf("Error reading benchmark directory: %v\n", err)
		os.Exit(1)
	}

	// Store results for all benchmarks
	var results []*BenchmarkResult

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		benchmarkPath := filepath.Join(*benchmarkDir, entry.Name())

		// Look for trace.csv in the benchmark directory
		tracePath := filepath.Join(benchmarkPath, "merged.csv")
		if _, err := os.Stat(tracePath); os.IsNotExist(err) {
			fmt.Printf("Warning: No merged.csv found in %s\n", benchmarkPath)
			continue
		}

		fmt.Printf("Analyzing benchmark: %s\n", entry.Name())
		result, err := AnalyzeTraceFile(tracePath, *deadThreshold)
		if err != nil {
			fmt.Printf("Error analyzing %s: %v\n", entry.Name(), err)
			continue
		}

		// Print individual results
		PrintBenchmarkResult(result)
		results = append(results, result)
	}

	if len(results) == 0 {
		fmt.Println("No benchmarks were successfully analyzed.")
		os.Exit(1)
	}

	// Generate combined visualizations
	fmt.Println("\nGenerating combined visualizations...")

	// Generate charts
	if err := GenerateDeadBlocksBarChart(results, filepath.Join(*outputDir, "dead_blocks_chart.png")); err != nil {
		fmt.Printf("Error generating dead blocks chart: %v\n", err)
	}

	if err := GenerateHitRateBarChart(results, filepath.Join(*outputDir, "hit_rate_chart.png")); err != nil {
		fmt.Printf("Error generating hit rate chart: %v\n", err)
	}

	if err := GenerateBankDistributionChart(results, filepath.Join(*outputDir, "bank_distribution_chart.png")); err != nil {
		fmt.Printf("Error generating bank distribution chart: %v\n", err)
	}

	// Generate CSV summary
	if err := GenerateCSVSummary(results, filepath.Join(*outputDir, "benchmark_summary.csv")); err != nil {
		fmt.Printf("Error generating CSV summary: %v\n", err)
	}

	fmt.Println("Analysis complete. Results saved to:", *outputDir)
}
