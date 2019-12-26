package main

import (
	"flag"
	"log"
	"math/rand"

	"gitlab.com/akita/akita"
	"gitlab.com/akita/mgpusim/driver"
	"gitlab.com/akita/mgpusim/samples/runner"
)

type Benchmark struct {
	driver  *driver.Driver
	context *driver.Context
	gpu     int

	ByteSize uint64
	data     []byte
	retData  []byte

	useUnifiedMemory bool
}

func NewBenchmark(driver *driver.Driver) *Benchmark {
	b := new(Benchmark)
	b.driver = driver
	b.context = driver.Init()
	return b
}

func (b *Benchmark) SelectGPU(gpus []int) {
	if len(gpus) > 1 {
		panic("memory copy benchmark only support a single GPU")
	}
	b.gpu = gpus[0]
}

// Use Unified Memory
func (b *Benchmark) SetUnifiedMemory() {
	b.useUnifiedMemory = true
}

func (b *Benchmark) Run() {
	b.driver.SelectGPU(b.context, b.gpu)

	b.data = make([]byte, b.ByteSize)
	b.retData = make([]byte, b.ByteSize)
	for i := uint64(0); i < b.ByteSize; i++ {
		b.data[i] = byte(rand.Int())
	}
	gpuData := b.driver.AllocateMemory(b.context, b.ByteSize)

	if b.useUnifiedMemory {
		gpuData = b.driver.AllocateUnifiedMemory(b.context, b.ByteSize)
	}
	b.driver.MemCopyH2D(b.context, gpuData, b.data)
	b.driver.MemCopyD2H(b.context, b.retData, gpuData)
}

func (b *Benchmark) Verify() {
	for i := uint64(0); i < b.ByteSize; i++ {
		if b.data[i] != b.retData[i] {
			log.Panicf("error at %d, expected %02x, but get %02x",
				i, b.data[i], b.retData[i])
		}
	}
	log.Printf("Passed!")
}

func run() akita.VTimeInSec {
	runner := new(runner.Runner).ParseFlag().Init()

	benchmark := NewBenchmark(runner.GPUDriver)
	benchmark.ByteSize = 1048576

	runner.AddBenchmark(benchmark)

	runner.Run()

	return runner.Engine.CurrentTime()
}

func main() {
	flag.Parse()

	time1 := run()
	time2 := run()

	if time1 != time2 {
		panic("memory copy is not deterministic")
	}
}
