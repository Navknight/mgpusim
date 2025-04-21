#!/usr/bin/env python3
"""
Stride Prefetcher Log Analyzer

This script analyzes stride prefetcher log files to extract insights about
the prefetcher's behavior, with support for analyzing multiple log files
for comparison between different prefetcher configurations.
"""

import re
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict, Counter
import glob
import pandas as pd


def parse_log_file(filename):
    """Parse the stride prefetcher log file and extract relevant events."""
    events = []
    degree = None
    
    try:
        # Try to extract degree from filename
        match = re.search(r"stride_prefetcher_deg(\d+)", os.path.basename(filename))
        if match:
            degree = int(match.group(1))
    except:
        pass
    
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # Extract timestamp and message
                parts = line.strip().split(' ', 2)
                if len(parts) < 3:
                    continue
                
                timestamp = ' '.join(parts[:2])
                message = parts[2] if len(parts) > 2 else ""
                
                # Check for NEW_PREFETCHER message to extract degree
                if message.startswith("NEW_PREFETCHER"):
                    match = re.search(r"Degree:(\d+)", message)
                    if match:
                        degree = int(match.group(1))
                        events.append({
                            'timestamp': timestamp,
                            'type': 'new_prefetcher',
                            'degree': degree,
                            'line_num': line_num
                        })
                        continue
                
                # Parse different types of log messages
                if message.startswith("RA "):  # Record Access
                    match = re.search(r"RA PID:(\d+) ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'record_access',
                            'pid': int(match.group(1)),
                            'addr': int(match.group(2), 16),
                            'line_num': line_num
                        })
                
                elif message.startswith("TP "):  # Try Prefetch
                    match = re.search(r"TP PID:(\d+) ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'try_prefetch',
                            'pid': int(match.group(1)),
                            'addr': int(match.group(2), 16),
                            'line_num': line_num
                        })
                
                elif message.startswith("STRIDE_MATCH "):
                    match = re.search(r"STRIDE_MATCH CONF:(\d+) STRIDE:(-?\d+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'stride_match',
                            'confidence': int(match.group(1)),
                            'stride': int(match.group(2)),
                            'line_num': line_num
                        })
                
                elif message.startswith("STRIDE_MISMATCH "):
                    match = re.search(r"STRIDE_MISMATCH CONF:(\d+) STRIDE:(-?\d+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'stride_mismatch',
                            'confidence': int(match.group(1)),
                            'stride': int(match.group(2)),
                            'line_num': line_num
                        })
                
                elif message.startswith("PREFETCH_ISSUED "):
                    match = re.search(r"PREFETCH_ISSUED ADDR:([0-9a-fx]+)( DEGREE:(\d+))?", message)
                    if match:
                        event_data = {
                            'timestamp': timestamp,
                            'type': 'prefetch_issued',
                            'addr': int(match.group(1), 16),
                            'line_num': line_num
                        }
                        if match.group(3):
                            event_data['degree_step'] = int(match.group(3))
                        events.append(event_data)
                
                elif message.startswith("ISSUE_PREFETCH "):
                    match = re.search(r"ISSUE_PREFETCH PID:(\d+) ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'issue_prefetch',
                            'pid': int(match.group(1)),
                            'addr': int(match.group(2), 16),
                            'line_num': line_num
                        })
                
                elif "CACHE_HIT" in message:
                    match = re.search(r"CACHE_HIT ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'cache_hit',
                            'addr': int(match.group(1), 16),
                            'line_num': line_num
                        })
                
                elif "MSHR_HIT" in message:
                    match = re.search(r"MSHR_HIT ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'mshr_hit',
                            'addr': int(match.group(1), 16),
                            'line_num': line_num
                        })
                
                elif "MSHR_FULL" in message:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'mshr_full',
                        'line_num': line_num
                    })
                
                elif "NO_VICTIM" in message:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'no_victim',
                        'line_num': line_num
                    })
                
                elif message.startswith("SEND_SUCCESS "):
                    match = re.search(r"SEND_SUCCESS ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'send_success',
                            'addr': int(match.group(1), 16),
                            'line_num': line_num
                        })
                
                elif message.startswith("SEND_FAIL "):
                    match = re.search(r"SEND_FAIL ADDR:([0-9a-fx]+) ERR:(.*)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'send_fail',
                            'addr': int(match.group(1), 16),
                            'error': match.group(2),
                            'line_num': line_num
                        })
                
                elif "NEW_SI" in message:
                    match = re.search(r"NEW_SI PID:(\d+) PAGE:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'new_stride_info',
                            'pid': int(match.group(1)),
                            'page': int(match.group(2), 16),
                            'line_num': line_num
                        })
                
                elif "UPDATE_ADDR" in message:
                    match = re.search(r"UPDATE_ADDR LAST:([0-9a-fx]+) PREV:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'update_addr',
                            'last': int(match.group(1), 16),
                            'prev': int(match.group(2), 16),
                            'line_num': line_num
                        })
                
                elif "NO_CONFIDENCE_SKIP_PREFETCH" in message:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'no_confidence',
                        'line_num': line_num
                    })
                
                elif message.startswith("PREFETCH_TRANS "):
                    match = re.search(r"PREFETCH_TRANS ADDR:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'prefetch_trans',
                            'addr': int(match.group(1), 16),
                            'line_num': line_num
                        })
                
                elif "PAGE_BOUNDARY_BREAK" in message:
                    match = re.search(r"PAGE_BOUNDARY_BREAK ADDR:([0-9a-fx]+) PAGE:([0-9a-fx]+) NEXT_PAGE:([0-9a-fx]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'page_boundary_break',
                            'addr': int(match.group(1), 16),
                            'page': int(match.group(2), 16),
                            'next_page': int(match.group(3), 16),
                            'line_num': line_num
                        })
                
                elif "PREFETCH_HIT" in message:
                    match = re.search(r"PREFETCH_HIT Total:(\d+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'prefetch_hit',
                            'total': int(match.group(1)),
                            'line_num': line_num
                        })
                
                elif "PREFETCH_COMPLETE" in message:
                    match = re.search(r"PREFETCH_COMPLETE Total:(\d+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'prefetch_complete',
                            'total': int(match.group(1)),
                            'line_num': line_num
                        })
                
                elif "FINAL_STATS" in message:
                    match = re.search(r"FINAL_STATS PrefetchHits:(\d+) PrefetchMisses:(\d+) TotalPrefetches:(\d+) SuccessfulPrefetches:(\d+) CompletedPrefetches:(\d+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'final_stats',
                            'prefetch_hits': int(match.group(1)),
                            'prefetch_misses': int(match.group(2)),
                            'total_prefetches': int(match.group(3)),
                            'successful_prefetches': int(match.group(4)),
                            'completed_prefetches': int(match.group(5)),
                            'line_num': line_num
                        })
                
                elif "FINAL_METRICS" in message:
                    match = re.search(r"FINAL_METRICS Accuracy:([\d\.]+)% SuccessRate:([\d\.]+)% InCacheCount:([\d\.]+)", message)
                    if match:
                        events.append({
                            'timestamp': timestamp,
                            'type': 'final_metrics',
                            'accuracy': float(match.group(1)),
                            'success_rate': float(match.group(2)),
                            'in_cache_count': float(match.group(3)),
                            'line_num': line_num
                        })
                
                elif "ENABLED" in message:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'enabled',
                        'line_num': line_num
                    })
                
                elif "DISABLED" in message:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'disabled',
                        'line_num': line_num
                    })
            except Exception as e:
                print(f"Error parsing line {line_num} in {filename}: {line.strip()}")
                print(f"Error details: {e}")
    
    return events, degree


def analyze_events(events, degree):
    """Analyze the parsed events and generate statistics."""
    stats = {
        'degree': degree,
        'total_record_access': 0,
        'total_try_prefetch': 0,
        'stride_matches': 0,
        'stride_mismatches': 0,
        'prefetch_issued': 0,
        'cache_hits': 0,
        'mshr_hits': 0,
        'mshr_full': 0,
        'no_victim': 0,
        'send_success': 0,
        'send_fail': 0,
        'new_stride_info': 0,
        'no_confidence': 0,
        'page_boundary_breaks': 0,
        'prefetch_hits': 0,
        'prefetch_complete': 0,
        'stride_values': defaultdict(int),
        'confidence_levels': defaultdict(int),
        'prefetch_success_rate': 0,
        'prefetch_hit_rate': 0,
        'pages_tracked': set(),
        'pids_tracked': set(),
        'degree_distribution': defaultdict(int),
        'prefetch_failures': {
            'cache_hit': 0,
            'mshr_hit': 0,
            'mshr_full': 0,
            'no_victim': 0,
            'no_confidence': 0,
            'send_fail': 0,
            'page_boundary': 0
        }
    }
    
    # Check for final stats if available
    final_stats = next((e for e in events if e['type'] == 'final_stats'), None)
    final_metrics = next((e for e in events if e['type'] == 'final_metrics'), None)
    
    if final_stats:
        stats['prefetch_hits'] = final_stats['prefetch_hits']
        stats['prefetch_misses'] = final_stats['prefetch_misses']
        stats['total_prefetches'] = final_stats['total_prefetches']
        stats['successful_prefetches'] = final_stats['successful_prefetches']
        stats['completed_prefetches'] = final_stats['completed_prefetches']
    
    if final_metrics:
        stats['accuracy'] = final_metrics['accuracy']
        stats['success_rate'] = final_metrics['success_rate']
        stats['in_cache_count'] = final_metrics['in_cache_count']
    
    # Process all events
    for event in events:
        event_type = event['type']
        
        # Count different types of events
        if event_type == 'record_access':
            stats['total_record_access'] += 1
            if 'pid' in event:
                stats['pids_tracked'].add(event['pid'])
        elif event_type == 'try_prefetch':
            stats['total_try_prefetch'] += 1
        elif event_type == 'stride_match':
            stats['stride_matches'] += 1
            stats['stride_values'][event['stride']] += 1
            stats['confidence_levels'][event['confidence']] += 1
        elif event_type == 'stride_mismatch':
            stats['stride_mismatches'] += 1
            stats['confidence_levels'][event['confidence']] += 1
        elif event_type == 'prefetch_issued':
            stats['prefetch_issued'] += 1
            if 'degree_step' in event:
                stats['degree_distribution'][event['degree_step']] += 1
        elif event_type == 'cache_hit':
            stats['cache_hits'] += 1
            stats['prefetch_failures']['cache_hit'] += 1
        elif event_type == 'mshr_hit':
            stats['mshr_hits'] += 1
            stats['prefetch_failures']['mshr_hit'] += 1
        elif event_type == 'mshr_full':
            stats['mshr_full'] += 1
            stats['prefetch_failures']['mshr_full'] += 1
        elif event_type == 'no_victim':
            stats['no_victim'] += 1
            stats['prefetch_failures']['no_victim'] += 1
        elif event_type == 'send_success':
            stats['send_success'] += 1
        elif event_type == 'send_fail':
            stats['send_fail'] += 1
            stats['prefetch_failures']['send_fail'] += 1
        elif event_type == 'new_stride_info':
            stats['new_stride_info'] += 1
            if 'pid' in event and 'page' in event:
                stats['pages_tracked'].add((event['pid'], event['page']))
        elif event_type == 'no_confidence':
            stats['no_confidence'] += 1
            stats['prefetch_failures']['no_confidence'] += 1
        elif event_type == 'page_boundary_break':
            stats['page_boundary_breaks'] += 1
            stats['prefetch_failures']['page_boundary'] += 1
        elif event_type == 'prefetch_hit':
            # Individual prefetch hit events if not using final stats
            if not final_stats:
                stats['prefetch_hits'] = event['total']
        elif event_type == 'prefetch_complete':
            # Individual prefetch complete events if not using final stats
            if not final_stats:
                stats['prefetch_complete'] = event['total']
    
    # Calculate derived metrics if not already available from final stats
    if not final_metrics:
        # Calculate prefetch success rate
        if stats['prefetch_issued'] > 0:
            stats['success_rate'] = stats['send_success'] / stats['prefetch_issued'] * 100
        
        # Calculate prefetch hit rate
        if stats['successful_prefetches'] > 0:
            stats['accuracy'] = stats['prefetch_hits'] / stats['successful_prefetches'] * 100
    
    # Calculate stride pattern match rate
    total_stride_events = stats['stride_matches'] + stats['stride_mismatches']
    if total_stride_events > 0:
        stats['stride_match_rate'] = stats['stride_matches'] / total_stride_events * 100
    else:
        stats['stride_match_rate'] = 0
    
    return stats


def analyze_multiple_logs(log_files):
    """Analyze multiple log files and compare their results."""
    results = []
    
    for log_file in log_files:
        print(f"Analyzing {log_file}...")
        events, degree = parse_log_file(log_file)
        
        if events:
            stats = analyze_events(events, degree)
            stats['filename'] = os.path.basename(log_file)
            results.append(stats)
            print(f"  Found {len(events)} events with degree {degree}")
        else:
            print(f"  No events found in {log_file}")
    
    return results


def generate_comparison_visualizations(results, output_prefix):
    """Generate visualizations comparing different prefetcher configurations."""
    if not results:
        print("No results to visualize")
        return
    
    # Sort results by degree
    results = sorted(results, key=lambda x: x.get('degree', 0))
    
    # Create comparison dataframe
    df = pd.DataFrame(results)
    
    # 1. Compare prefetch accuracy and success rate
    plt.figure(figsize=(12, 6))
    x = [str(r.get('degree', 'N/A')) for r in results]
    
    accuracy = [r.get('accuracy', 0) for r in results]
    success_rate = [r.get('success_rate', 0) for r in results]
    
    bar_width = 0.35
    r1 = np.arange(len(results))
    r2 = [x + bar_width for x in r1]
    
    plt.bar(r1, accuracy, width=bar_width, label='Accuracy (%)', color='#3B82F6')
    plt.bar(r2, success_rate, width=bar_width, label='Success Rate (%)', color='#10B981')
    
    plt.xlabel('Prefetcher Degree')
    plt.ylabel('Percentage (%)')
    plt.title('Prefetch Accuracy and Success Rate by Degree')
    plt.xticks([r + bar_width/2 for r in range(len(results))], x)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_prefix}_accuracy_comparison.png")
    
    # 2. Compare prefetch hits and total prefetches
    plt.figure(figsize=(12, 6))
    
    prefetch_hits = [r.get('prefetch_hits', 0) for r in results]
    total_prefetches = [r.get('total_prefetches', 0) for r in results]
    successful_prefetches = [r.get('successful_prefetches', 0) for r in results]
    
    plt.plot(x, prefetch_hits, 'o-', label='Prefetch Hits', color='#3B82F6')
    plt.plot(x, successful_prefetches, 's-', label='Successful Prefetches', color='#10B981')
    plt.plot(x, total_prefetches, '^-', label='Total Prefetches', color='#EF4444')
    
    plt.xlabel('Prefetcher Degree')
    plt.ylabel('Count')
    plt.title('Prefetch Counts by Degree')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_prefix}_prefetch_counts_comparison.png")
    
    # 3. Compare prefetch failure reasons across degrees
    plt.figure(figsize=(14, 8))
    
    failure_categories = ['cache_hit', 'mshr_hit', 'mshr_full', 'no_victim', 'no_confidence', 'send_fail', 'page_boundary']
    failure_data = {}
    
    for category in failure_categories:
        failure_data[category] = []
        for r in results:
            if 'prefetch_failures' in r and category in r['prefetch_failures']:
                failure_data[category].append(r['prefetch_failures'][category])
            else:
                failure_data[category].append(0)
    
    bottom = np.zeros(len(results))
    for category in failure_categories:
        plt.bar(x, failure_data[category], bottom=bottom, label=category)
        bottom += np.array(failure_data[category])
    
    plt.xlabel('Prefetcher Degree')
    plt.ylabel('Count')
    plt.title('Prefetch Failure Reasons by Degree')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_prefix}_failure_reasons_comparison.png")
    
    # 4. Normalize stride match rate and prefetch metrics
    plt.figure(figsize=(12, 6))
    
    stride_match_rate = [r.get('stride_match_rate', 0) for r in results]
    
    plt.plot(x, stride_match_rate, 'o-', label='Stride Match Rate (%)', color='#8B5CF6')
    plt.plot(x, accuracy, 's-', label='Prefetch Accuracy (%)', color='#3B82F6')
    plt.plot(x, success_rate, '^-', label='Prefetch Success Rate (%)', color='#10B981')
    
    plt.xlabel('Prefetcher Degree')
    plt.ylabel('Percentage (%)')
    plt.title('Prefetcher Effectiveness Metrics by Degree')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_prefix}_effectiveness_comparison.png")
    
    # 5. Generate a summary table as an image
    plt.figure(figsize=(14, len(results) * 0.8 + 1))
    plt.axis('off')
    
    col_labels = ['Degree', 'Accuracy (%)', 'Success Rate (%)', 'Prefetch Hits', 
                'Successful', 'Total Prefetches', 'Stride Match Rate (%)']
    table_data = []
    
    for r in results:
        row = [
            str(r.get('degree', 'N/A')),
            f"{r.get('accuracy', 0):.2f}",
            f"{r.get('success_rate', 0):.2f}",
            str(r.get('prefetch_hits', 0)),
            str(r.get('successful_prefetches', 0)),
            str(r.get('total_prefetches', 0)),
            f"{r.get('stride_match_rate', 0):.2f}"
        ]
        table_data.append(row)
    
    table = plt.table(cellText=table_data, colLabels=col_labels, loc='center',
                    cellLoc='center', colColours=['#f0f0f0'] * len(col_labels))
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    plt.title('Prefetcher Performance Summary', y=0.9)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_summary_table.png", bbox_inches='tight')


def analyze_single_log(events, degree, output_prefix):
    """Analyze and visualize metrics for a single log file."""
    stats = analyze_events(events, degree)
    
    # 1. Stride distribution
    plt.figure(figsize=(12, 6))
    strides = sorted(stats['stride_values'].items())
    plt.bar([str(stride[0]) for stride in strides], [stride[1] for stride in strides])
    plt.title(f'Stride Pattern Distribution (Degree={degree})')
    plt.xlabel('Stride Value')
    plt.ylabel('Frequency')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_stride_distribution.png")
    
    # 2. Confidence level distribution
    plt.figure(figsize=(10, 6))
    conf_levels = sorted(stats['confidence_levels'].items())
    plt.bar([str(conf[0]) for conf in conf_levels], [conf[1] for conf in conf_levels])
    plt.title(f'Confidence Level Distribution (Degree={degree})')
    plt.xlabel('Confidence Level')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_confidence_distribution.png")
    
    # 3. Prefetch failure reasons
    plt.figure(figsize=(12, 6))
    failure_reasons = stats['prefetch_failures']
    plt.bar(failure_reasons.keys(), failure_reasons.values())
    plt.title(f'Prefetch Failure Reasons (Degree={degree})')
    plt.xlabel('Reason')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_prefetch_failures.png")
    
    # 4. Degree distribution (if available)
    if any(stats['degree_distribution'].values()):
        plt.figure(figsize=(10, 6))
        degree_dist = sorted(stats['degree_distribution'].items())
        plt.bar([str(d[0]) for d in degree_dist], [d[1] for d in degree_dist])
        plt.title(f'Prefetch Degree Distribution (Max Degree={degree})')
        plt.xlabel('Degree Step')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_degree_distribution.png")
    
    # 5. Summary statistics pie chart
    plt.figure(figsize=(12, 12))
    
    # First pie: Prefetch outcomes
    plt.subplot(2, 1, 1)
    outcome_labels = ['Success', 'Cache Hit', 'MSHR Hit', 'MSHR Full', 'No Victim', 'No Confidence', 'Page Boundary']
    outcome_values = [
        stats['send_success'],
        stats['prefetch_failures']['cache_hit'],
        stats['prefetch_failures']['mshr_hit'],
        stats['prefetch_failures']['mshr_full'],
        stats['prefetch_failures']['no_victim'],
        stats['prefetch_failures']['no_confidence'],
        stats['prefetch_failures']['page_boundary']
    ]
    
    # Filter out zero values
    non_zero_labels = []
    non_zero_values = []
    for label, value in zip(outcome_labels, outcome_values):
        if value > 0:
            non_zero_labels.append(label)
            non_zero_values.append(value)
    
    if non_zero_values:
        plt.pie(non_zero_values, labels=non_zero_labels, autopct='%1.1f%%')
        plt.title(f'Prefetch Outcomes (Degree={degree})')
    
    # Second pie: Stride pattern match/mismatch
    plt.subplot(2, 1, 2)
    pattern_labels = ['Stride Matches', 'Stride Mismatches']
    pattern_values = [stats['stride_matches'], stats['stride_mismatches']]
    
    if sum(pattern_values) > 0:
        plt.pie(pattern_values, labels=pattern_labels, autopct='%1.1f%%', 
                colors=['#10B981', '#EF4444'])
        plt.title(f'Stride Pattern Recognition (Degree={degree})')
    
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_summary_statistics.png")
    
    return stats


def print_statistics(stats):
    """Print the analyzed statistics to the console."""
    degree = stats.get('degree', 'N/A')
    print(f"\n===== Stride Prefetcher Analysis (Degree={degree}) =====")
    
    print("\n--- Basic Metrics ---")
    print(f"Total Record Access events: {stats['total_record_access']}")
    print(f"Total Try Prefetch events: {stats['total_try_prefetch']}")
    print(f"Stride Matches: {stats['stride_matches']}")
    print(f"Stride Mismatches: {stats['stride_mismatches']}")
    print(f"Stride Match Rate: {stats.get('stride_match_rate', 0):.2f}%")
    
    print("\n--- Prefetch Performance ---")
    print(f"Total Prefetches Attempted: {stats.get('total_prefetches', 0)}")
    print(f"Successful Prefetches: {stats.get('successful_prefetches', 0)}")
    print(f"Prefetch Hits: {stats.get('prefetch_hits', 0)}")
    print(f"Prefetch Success Rate: {stats.get('success_rate', 0):.2f}%")
    print(f"Prefetch Accuracy: {stats.get('accuracy', 0):.2f}%")
    print(f"Prefetched Blocks in Cache: {stats.get('in_cache_count', 0)}")
    
    print("\n--- Tracking Information ---")
    print(f"Unique Pages Tracked: {len(stats['pages_tracked'])}")
    print(f"Unique PIDs Tracked: {len(stats['pids_tracked'])}")
    
    print("\n--- Stride Pattern Distribution (Top 5) ---")
    for stride, count in sorted(stats['stride_values'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  Stride {stride}: {count} occurrences")
    
    print("\n--- Prefetch Failure Reasons ---")
    for reason, count in stats['prefetch_failures'].items():
        if count > 0:
            print(f"  {reason}: {count} occurrences")
    
    print("\n--- Confidence Levels ---")
    for conf, count in sorted(stats['confidence_levels'].items()):
        print(f"  Level {conf}: {count} occurrences")


def analyze_temporal_patterns(events, output_prefix, degree):
    """Analyze temporal patterns in prefetcher behavior."""
    # Track confidence level changes over time
    
    # Group events by time buckets (every 100 events)
    bucket_size = min(100, max(1, len(events) // 20))  # Adjust bucket size based on event count
    total_buckets = len(events) // bucket_size + (1 if len(events) % bucket_size else 0)
    
    bucket_stats = []
    for i in range(total_buckets):
        start_idx = i * bucket_size
        end_idx = min((i + 1) * bucket_size, len(events))
        bucket_events = events[start_idx:end_idx]
        
        # Get stats for this bucket
        stride_matches = sum(1 for e in bucket_events if e['type'] == 'stride_match')
        stride_mismatches = sum(1 for e in bucket_events if e['type'] == 'stride_mismatch')
        prefetch_issued = sum(1 for e in bucket_events if e['type'] == 'prefetch_issued')
        send_success = sum(1 for e in bucket_events if e['type'] == 'send_success')
        prefetch_hits = sum(1 for e in bucket_events if e['type'] == 'prefetch_hit')
        
        # Calculate match ratio and prefetch success rate
        match_ratio = 0
        if stride_matches + stride_mismatches > 0:
            match_ratio = stride_matches / (stride_matches + stride_mismatches) * 100
        
        prefetch_success_rate = 0
        if prefetch_issued > 0:
            prefetch_success_rate = send_success / prefetch_issued * 100
        
        bucket_stats.append({
            'bucket': i,
            'match_ratio': match_ratio,
            'prefetch_success_rate': prefetch_success_rate,
            'stride_matches': stride_matches,
            'stride_mismatches': stride_mismatches,
            'prefetch_issued': prefetch_issued,
            'send_success': send_success,
            'prefetch_hits': prefetch_hits
        })
    
    # Plot temporal patterns
    plt.figure(figsize=(12, 6))
    
    buckets = [stat['bucket'] for stat in bucket_stats]
    match_ratios = [stat['match_ratio'] for stat in bucket_stats]
    success_rates = [stat['prefetch_success_rate'] for stat in bucket_stats]
    
    plt.plot(buckets, match_ratios, 'b-', label='Stride Match Ratio (%)')
    plt.plot(buckets, success_rates, 'r-', label='Prefetch Success Rate (%)')
    
    plt.title(f'Temporal Patterns in Prefetcher Behavior (Degree={degree})')
    plt.xlabel(f'Time Bucket (each ~{bucket_size} events)')
    plt.ylabel('Percentage (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_temporal_patterns.png")
    
    return bucket_stats


def main():
    parser = argparse.ArgumentParser(description='Analyze stride prefetcher logs')
    parser.add_argument('logfiles', nargs='+', help='Path(s) to stride prefetcher log file(s)')
    parser.add_argument('--output', '-o', default='prefetcher', help='Prefix for output files')
    parser.add_argument('--compare', '-c', action='store_true', help='Compare multiple log files')
    parser.add_argument('--pattern', '-p', help='Pattern to find log files (e.g., "prefetcher_logs/*.log")')
    args = parser.parse_args()
    
    log_files = args.logfiles
    
    # If pattern is specified, use it to find log files
    if args.pattern:
        pattern_files = glob.glob(args.pattern)
        if pattern_files:
            log_files.extend(pattern_files)
            log_files = list(set(log_files))  # Remove duplicates
    
    if not log_files:
        print("No log files specified or found with pattern.")
        return
    
    print(f"Found {len(log_files)} log file(s) to analyze.")
    
    # Determine if we should compare or analyze individually
    if args.compare or len(log_files) > 1:
        # Analyze and compare multiple files
        results = analyze_multiple_logs(log_files)
        
        if results:
            generate_comparison_visualizations(results, args.output)
            
            print("\n===== Comparison Summary =====")
            print(f"{'Degree':<8} {'Accuracy':<10} {'Success Rate':<15} {'Prefetch Hits':<15} {'Total Prefetches':<15}")
            print("-" * 70)
            
            for r in sorted(results, key=lambda x: x.get('degree', 0)):
                degree = r.get('degree', 'N/A')
                accuracy = r.get('accuracy', 0)
                success_rate = r.get('success_rate', 0)
                prefetch_hits = r.get('prefetch_hits', 0)
                total_prefetches = r.get('total_prefetches', 0)
                
                print(f"{degree:<8} {accuracy:<10.2f} {success_rate:<15.2f} {prefetch_hits:<15} {total_prefetches:<15}")
            
            print(f"\nVisualization files have been saved with prefix: {args.output}")
        else:
            print("No valid results found for comparison.")
    else:
        # Analyze a single file
        log_file = log_files[0]
        print(f"Analyzing single log file: {log_file}")
        
        events, degree = parse_log_file(log_file)
        
        if not events:
            print("No events found in the log file. Make sure the format is correct.")
            return
        
        print(f"Parsed {len(events)} events from the log file.")
        
        # Analyze the events
        stats = analyze_single_log(events, degree, args.output)
        
        # Print statistics
        print_statistics(stats)
        
        # Analyze temporal patterns
        bucket_stats = analyze_temporal_patterns(events, args.output, degree)
        
        print(f"\nVisualization files have been saved with prefix: {args.output}")


if __name__ == "__main__":
    main()