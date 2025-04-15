package runner

import (
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/sarchlab/akita/v3/mem/cache/writearound"
	"github.com/sarchlab/akita/v3/mem/mem"
	"github.com/sarchlab/akita/v3/sim"
	"github.com/sarchlab/akita/v3/tracing"
)

type AddressTracer struct {
	sync.Mutex
	records       map[string][]addressRecord
	outputDir     string
	caches        map[string]*writearound.Cache
	engine        sim.Engine
	dumpFrequency time.Duration
	lastDumpTime  time.Time
}

type addressRecord struct {
	Time    sim.VTimeInSec
	Address uint64
	Size    uint64
	IsRead  bool
	PID     uint64
	Source  string
}

func (t *AddressTracer) EndTask(task tracing.Task) {
	fmt.Print("EndTask\n")
}
func (t *AddressTracer) StepTask(task tracing.Task) {
	fmt.Print("StepTask\n")
}

func NewAddressTracer(engine sim.Engine, outputDir string) *AddressTracer {
	if engine == nil {
		panic("assert failed: engine must not be nil")
	}

	if outputDir == "" {
		panic("assert failed: outputDir must not be empty")
	}

	err := os.MkdirAll(outputDir, 0755)
	if err != nil {
		panic(fmt.Sprintf("failed to create output directory: %v", err))
	}

	// Assert that directory was created successfully
	if _, err := os.Stat(outputDir); os.IsNotExist(err) {
		panic(fmt.Sprintf("assert failed: output directory was not created: %v", err))
	}

	tracer := &AddressTracer{
		records:       make(map[string][]addressRecord),
		outputDir:     outputDir,
		caches:        make(map[string]*writearound.Cache),
		engine:        engine,
		dumpFrequency: 5 * time.Second,
		lastDumpTime:  time.Now(),
	}

	// Assert that map initialization was successful
	if tracer.records == nil {
		panic("assert failed: records map initialization failed")
	}
	if tracer.caches == nil {
		panic("assert failed: caches map initialization failed")
	}

	return tracer
}

func (t *AddressTracer) RegisterCache(cache *writearound.Cache) {
	if cache == nil {
		panic("assert failed: cannot register nil cache")
	}

	if cache.Name() == "" {
		panic("assert failed: cache must have a non-empty name")
	}

	t.Lock()
	defer t.Unlock()

	// Assert that the cache isn't already registered
	if _, exists := t.caches[cache.Name()]; exists {
		panic(fmt.Sprintf("assert failed: cache %s is already registered", cache.Name()))
	}

	t.caches[cache.Name()] = cache

	// Assert that cache was successfully added
	if _, exists := t.caches[cache.Name()]; !exists {
		panic(fmt.Sprintf("assert failed: cache %s was not registered properly", cache.Name()))
	}
}

func (t *AddressTracer) StartTask(task tracing.Task) {
	if task.Kind != "req_in" {
		return
	}

	msg, ok := task.Detail.(sim.Msg)
	if !ok {
		return
	}

	isRead := false
	var address uint64
	var size uint64
	var pid uint64
	var reqTime sim.VTimeInSec

	if readReq, ok := msg.(*mem.ReadReq); ok {
		if readReq == nil {
			panic("assert failed: readReq is nil after type assertion")
		}
		address = readReq.GetAddress()
		size = readReq.GetByteSize()
		pid = uint64(readReq.GetPID())
		reqTime = readReq.SendTime
		isRead = true
	} else if writeReq, ok := msg.(*mem.WriteReq); ok {
		if writeReq == nil {
			panic("assert failed: writeReq is nil after type assertion")
		}
		address = writeReq.GetAddress()
		size = writeReq.GetByteSize()
		pid = uint64(writeReq.GetPID())
		reqTime = writeReq.SendTime
	} else {
		return
	}

	// Assert address and size are valid
	if size == 0 {
		panic("assert failed: request size cannot be zero")
	}

	source := "unknown"
	if msg.Meta().Src != nil {
		srcName := msg.Meta().Src.Name()

		// Assert that source name is not empty
		if srcName == "" {
			panic("assert failed: source name cannot be empty")
		}

		if strings.Contains(srcName, "CU") {
			parts := strings.Split(srcName, ".")
			for _, part := range parts {
				if strings.HasPrefix(part, "CU") {
					source = part
					break
				}
			}
			if source == "unknown" {
				source = srcName
			}
		} else {
			source = srcName
		}
	}

	t.Lock()
	defer t.Unlock()

	record := addressRecord{
		Time:    reqTime,
		Address: address,
		Size:    size,
		PID:     pid,
		Source:  source,
		IsRead:  isRead,
	}

	cacheName := task.Where
	if cacheName == "" {
		panic("assert failed: cache name cannot be empty")
	}

	if _, exists := t.records[cacheName]; !exists {
		t.records[cacheName] = make([]addressRecord, 0)

		// Assert that the new slice was created successfully
		if _, exists := t.records[cacheName]; !exists {
			panic(fmt.Sprintf("assert failed: failed to create record slice for cache %s", cacheName))
		}
	}

	recordsLenBefore := len(t.records[cacheName])
	t.records[cacheName] = append(t.records[cacheName], record)

	// Assert that the record was successfully appended
	if len(t.records[cacheName]) != recordsLenBefore+1 {
		panic("assert failed: record was not appended correctly")
	}

	if time.Since(t.lastDumpTime) > t.dumpFrequency {
		t.DumpToFile()
		t.lastDumpTime = time.Now()
	}
}

func (t *AddressTracer) DumpToFile() {
	t.Lock()
	defer t.Unlock()

	// Assert that records map is initialized
	if t.records == nil {
		panic("assert failed: records map is nil")
	}

	// Assert that outputDir exists
	if _, err := os.Stat(t.outputDir); os.IsNotExist(err) {
		panic(fmt.Sprintf("assert failed: output directory %s does not exist", t.outputDir))
	}

	for cacheName, records := range t.records {
		if len(records) == 0 {
			return
		}

		// Assert that cacheName is not empty
		if cacheName == "" {
			panic("assert failed: cache name cannot be empty when dumping to file")
		}

		filename := fmt.Sprintf("%s/%s_addresses.csv", t.outputDir, cacheName)
		fileExists := false
		if _, err := os.Stat(filename); err == nil {
			fileExists = true
		}

		f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			panic(fmt.Sprintf("assert failed: error opening file %s: %v", filename, err))
		}

		// Assert file is open
		if f == nil {
			panic(fmt.Sprintf("assert failed: file %s was not opened correctly", filename))
		}

		if !fileExists {
			_, err := f.WriteString("Time, Address, Size, IsRead, PID, Source\n")
			if err != nil {
				f.Close()
				panic(fmt.Sprintf("assert failed: error writing headers to file %s: %v", filename, err))
			}
		}

		recordsWritten := 0
		for _, record := range records {
			isReadInt := 0
			if record.IsRead {
				isReadInt = 1
			}

			line := fmt.Sprintf("%f, 0x%x, %d, %d, %d, %s\n",
				float64(record.Time), record.Address, record.Size, isReadInt, record.PID, record.Source)

			bytesWritten, err := f.WriteString(line)
			if err != nil {
				f.Close()
				panic(fmt.Sprintf("assert failed: error writing to file %s: %v", filename, err))
			}

			// Assert that the line was written completely
			if bytesWritten == 0 {
				f.Close()
				panic(fmt.Sprintf("assert failed: zero bytes written to file %s", filename))
			}

			recordsWritten++
		}

		// Assert that all records were processed
		if recordsWritten != len(records) {
			f.Close()
			panic(fmt.Sprintf("assert failed: not all records were written to file %s", filename))
		}

		err = f.Close()
		if err != nil {
			panic(fmt.Sprintf("assert failed: error closing file %s: %v", filename, err))
		}

		// Clear records after successful write
		t.records[cacheName] = make([]addressRecord, 0)

		// Assert that records were cleared
		if len(t.records[cacheName]) != 0 {
			panic(fmt.Sprintf("assert failed: records for cache %s were not cleared after dumping", cacheName))
		}
	}
}
