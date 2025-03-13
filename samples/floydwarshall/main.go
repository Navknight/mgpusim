package main

import (
	"flag"

	"github.com/sarchlab/mgpusim/v3/benchmarks/amdappsdk/floydwarshall"
	"github.com/sarchlab/mgpusim/v3/samples/runner"
)

var numNodes = flag.Int("node", 16, "The number of nodes in the graph")
var numIterations = flag.Int("iter", 0,
	`The number of iterations to run. If this value is set to 0 or a number
	larger than the number of nodes, it will be reset to the number of nodes.`)

func main() {
	flag.Parse()

	r := new(runner.Runner).ParseFlag().Init()
	
	// Enable cache hit rate reporting
	r.ReportCacheHitRate = true
	
	benchmark := floydwarshall.NewBenchmark(r.Driver())
	benchmark.NumNodes = uint32(*numNodes)
	benchmark.NumIterations = uint32(*numIterations)

	r.AddBenchmark(benchmark)

	r.Run()
	
	// The built-in cache statistics will be automatically collected and reported
	// by the runner's reporting system via the metricsCollector
}
