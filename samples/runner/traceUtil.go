package runner

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type MergedAddressRecord struct {
	Time      float64
	Address   uint64
	Size      uint64
	IsRead    bool
	PID       uint64
	Source    string
	CacheName string
}

func MergeAddressTraces(inputDir, outputFile string) error {
	files, err := filepath.Glob(filepath.Join(inputDir, "*_addresses.csv"))
	if err != nil {
		return fmt.Errorf("failed to find trace files: %v", err)
	}

	if len(files) == 0 {
		return fmt.Errorf("no trace files found in %s", inputDir)
	}

	var allRecords []MergedAddressRecord
	for _, file := range files {
		cacheName := filepath.Base(file)
		cacheName = strings.TrimSuffix(cacheName, "_addresses.csv")

		records, err := readAddressRecords(file, cacheName)
		if err != nil {
			return fmt.Errorf("failes to read %s: %v", file, err)
		}

		allRecords = append(allRecords, records...)
	}

	sort.Slice(allRecords, func(i, j int) bool {
		return allRecords[i].Time < allRecords[j].Time
	})

	return writeAddressRecords(outputFile, allRecords)
}

func readAddressRecords(filename, cacheName string) ([]MergedAddressRecord, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)

	if _, err := reader.Read(); err != nil {
		return nil, err
	}

	var records []MergedAddressRecord
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}

		// Parse fields
		time, err := strconv.ParseFloat(row[0], 64)
		if err != nil {
			return nil, err
		}

		addr, err := strconv.ParseUint(strings.TrimPrefix(row[1], "0x"), 16, 64)
		if err != nil {
			return nil, err
		}

		size, err := strconv.ParseUint(row[2], 10, 64)
		if err != nil {
			return nil, err
		}

		isReadInt, err := strconv.ParseUint(row[3], 10, 64)
		if err != nil {
			return nil, err
		}
		isRead := isReadInt != 0

		pid, err := strconv.ParseUint(row[4], 10, 64)
		if err != nil {
			return nil, err
		}

		source := "Unknown"
		if len(row) > 5 {
			source = row[5]
		}

		records = append(records, MergedAddressRecord{
			Time:      time,
			Address:   addr,
			Size:      size,
			IsRead:    isRead,
			PID:       pid,
			Source:    source,
			CacheName: cacheName,
		})
	}

	return records, nil
}

func writeAddressRecords(filename string, records []MergedAddressRecord) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	if err := writer.Write([]string{"Time", "Address", "Size", "IsRead", "PID", "Source", "CacheName"}); err != nil {
		return err
	}

	for _, record := range records {
		isReadStr := "0"
		if record.IsRead {
			isReadStr = "1"
		}

		addrStr := fmt.Sprintf("0x%x", record.Address)

		if err := writer.Write([]string{
			fmt.Sprintf("%f", record.Time),
			addrStr,
			fmt.Sprintf("%d", record.Size),
			isReadStr,
			fmt.Sprintf("%d", record.PID),
			record.Source,
			record.CacheName,
		}); err != nil {
			return err
		}
	}

	return nil
}
