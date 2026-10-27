package driver

import (
	"compress/gzip"
	"encoding/csv"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/sarchlab/akita/v3/sim"
)

type MigrationTracer struct {
	mu   sync.Mutex
	file *os.File
	gz   *gzip.Writer
	w    *csv.Writer
}

func NewMigrationTracer(dir string) *MigrationTracer {
	err := os.MkdirAll(dir, 0o755)
	if err != nil {
		panic(err)
	}

	f, err := os.Create(filepath.Join(dir, "mig.csv.gz"))
	if err != nil {
		panic(err)
	}

	t := &MigrationTracer{file: f, gz: gzip.NewWriter(f)}
	t.w = csv.NewWriter(t.gz)
	t.write([]string{
		"t_req_ns", "t_start_ns", "t_drained_ns", "t_shot_ns",
		"t_copied_ns", "t_restarted_ns", "t_end_ns",
		"vpn", "src", "dst", "accessing", "t_serviced_ns",
	})

	return t
}

func (t *MigrationTracer) Close() {
	t.mu.Lock()
	defer t.mu.Unlock()

	t.w.Flush()
	if err := t.gz.Close(); err != nil {
		panic(err)
	}
	if err := t.file.Close(); err != nil {
		panic(err)
	}
}

func (t *MigrationTracer) write(row []string) {
	if err := t.w.Write(row); err != nil {
		panic(err)
	}
}

type migrationStamps struct {
	req, start, serviced, drained, shot, restarted sim.VTimeInSec
	pages                                          []migratedPage
	numCopied                                      int
}

type migratedPage struct {
	vAddr, dst uint64
	copied     sim.VTimeInSec
}

func ns(t sim.VTimeInSec) string {
	return strconv.FormatFloat(float64(t)*1e9, 'f', 1, 64)
}

func (t *MigrationTracer) record(
	s *migrationStamps,
	end sim.VTimeInSec,
	log2PageSize uint64,
	src uint64,
	accessingGPUs []uint64,
) {
	t.mu.Lock()
	defer t.mu.Unlock()

	acc := make([]string, len(accessingGPUs))
	for i, g := range accessingGPUs {
		acc[i] = strconv.FormatUint(g, 10)
	}

	for _, p := range s.pages {
		t.write([]string{
			ns(s.req), ns(s.start), ns(s.drained), ns(s.shot),
			ns(p.copied), ns(s.restarted), ns(end),
			strconv.FormatUint(p.vAddr>>log2PageSize, 10),
			strconv.FormatUint(src, 10),
			strconv.FormatUint(p.dst, 10),
			strings.Join(acc, ";"),
			ns(s.serviced),
		})
	}
}
