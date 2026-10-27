package runner

import (
	"fmt"

	"github.com/sarchlab/akita/v3/mem/blockstats"
)

type blockStatsSetter interface {
	SetBlockStats(s *blockstats.Stats)
}

type deadBlockGroup struct {
	name  string
	stats *blockstats.Stats
}

func (r *Runner) addDeadBlockTracers() {
	if !r.ReportDeadBlocks {
		return
	}

	for i, gpu := range r.platform.GPUs {
		groups := []struct {
			what  string
			comps []TraceableComponent
		}{
			{"L1VCache", gpu.L1VCaches},
			{"L2Cache", gpu.L2Caches},
			{"L1VTLB", gpu.L1VTLBs},
			{"L2TLB", gpu.L2TLBs},
		}

		for _, g := range groups {
			s := &blockstats.Stats{Now: r.platform.Engine.CurrentTime}
			for _, c := range g.comps {
				c.(blockStatsSetter).SetBlockStats(s)
			}

			r.deadBlockGroups = append(r.deadBlockGroups, deadBlockGroup{
				name:  fmt.Sprintf("GPU[%d].%s", i+1, g.what),
				stats: s,
			})
		}
	}
}

func (r *Runner) reportDeadBlocks() {
	for _, g := range r.deadBlockGroups {
		s := g.stats
		c := r.metricsCollector

		c.Collect(g.name, "db-fills", float64(s.Fills))
		c.Collect(g.name, "db-bypassed", float64(s.Bypassed))
		c.Collect(g.name, "db-evicted", float64(s.Evicted))
		c.Collect(g.name, "db-flushed", float64(s.Flushed))
		c.Collect(g.name, "db-dead-on-arrival", float64(s.DeadOnArrival))

		for i, b := range blockstats.HitBucketNames {
			c.Collect(g.name, "db-hits-before-evict-"+b, float64(s.HitBuckets[i]))
		}

		if s.Evicted > 0 {
			n := float64(s.Evicted)
			c.Collect(g.name, "db-avg-live-ns", float64(s.LiveTime)*1e9/n)
			c.Collect(g.name, "db-avg-dead-ns", float64(s.DeadTime)*1e9/n)
		}
	}
}
