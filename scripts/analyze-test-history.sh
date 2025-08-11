#!/bin/bash
# Comprehensive Test History Analysis - Past Week

set -e

LOG_DIR="/Users/jasonasbahr/Development/Aeonia/Server/gaia/logs/tests/pytest"
ANALYSIS_DIR="/Users/jasonasbahr/Development/Aeonia/Server/gaia/logs/test-analysis"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "📊 Comprehensive Test History Analysis"
echo "🔍 Analyzing all logs from: $LOG_DIR"
echo "📁 Results will be saved to: $ANALYSIS_DIR/$TIMESTAMP"

mkdir -p "$ANALYSIS_DIR/$TIMESTAMP"

# Create analysis script
cat > "$ANALYSIS_DIR/$TIMESTAMP/analyze_history.py" << 'EOF'
#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from collections import defaultdict, Counter
import glob

def parse_filename_date(filename):
    """Extract date from test-run-YYYYMMDD-HHMMSS.log"""
    match = re.search(r'test-run-(\d{8})-(\d{6})\.log', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except:
            return None
    return None

def extract_test_summary(log_file):
    """Extract test summary from log file"""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Look for final summary line
        summary_patterns = [
            r'=+ (\d+) failed, (\d+) passed(?:, (\d+) skipped)?.*in ([\d.]+)s',
            r'=+ (\d+) passed(?:, (\d+) skipped)?.*in ([\d.]+)s',  # All passed
            r'=+ (\d+) failed.*in ([\d.]+)s',  # Only failures
        ]
        
        for pattern in summary_patterns:
            matches = re.findall(pattern, content)
            if matches:
                match = matches[-1]  # Take the last (final) summary
                if len(match) >= 2:
                    if 'failed' in pattern:
                        if len(match) >= 4:  # failed, passed, skipped, time
                            failed = int(match[0])
                            passed = int(match[1])
                            skipped = int(match[2]) if match[2] else 0
                            time_sec = float(match[3])
                        elif len(match) >= 2:  # failed, time
                            failed = int(match[0])
                            passed = 0
                            skipped = 0
                            time_sec = float(match[1])
                    else:  # Only passed
                        failed = 0
                        passed = int(match[0])
                        skipped = int(match[1]) if len(match) > 1 and match[1] else 0
                        time_sec = float(match[-1])
                    
                    return {
                        'failed': failed,
                        'passed': passed, 
                        'skipped': skipped,
                        'total': failed + passed + skipped,
                        'duration_sec': time_sec,
                        'status': 'completed'
                    }
        
        # Check for incomplete runs
        if 'Test run started' in content:
            if 'Test run completed' not in content:
                return {'status': 'incomplete', 'failed': 0, 'passed': 0, 'skipped': 0, 'total': 0, 'duration_sec': 0}
        
        return None
        
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'failed': 0, 'passed': 0, 'skipped': 0, 'total': 0, 'duration_sec': 0}

def analyze_test_patterns(log_file):
    """Extract specific test patterns and failures"""
    patterns = {
        'integration_full': 'tests/integration -v',
        'integration_web': 'tests/integration/web',
        'unit_tests': 'tests/unit',
        'e2e_tests': 'tests/e2e',
        'specific_file': r'tests/[^/]+\.py',
        'browser_tests': 'test_full_web_browser.py'
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        detected_patterns = []
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, content):
                detected_patterns.append(pattern_name)
        
        # Extract specific failures
        failure_matches = re.findall(r'FAILED ([^:]+::[^:]+::[^\s]+)', content)
        
        return {
            'test_patterns': detected_patterns,
            'specific_failures': failure_matches[:10]  # Top 10 failures
        }
        
    except:
        return {'test_patterns': [], 'specific_failures': []}

def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # Find all test log files
    log_files = glob.glob(os.path.join(log_dir, "test-run-*.log"))
    
    print(f"Found {len(log_files)} test log files")
    
    # Parse all logs
    results = []
    for log_file in log_files:
        filename = os.path.basename(log_file)
        date = parse_filename_date(filename)
        
        if date:
            summary = extract_test_summary(log_file)
            patterns = analyze_test_patterns(log_file)
            
            if summary:
                results.append({
                    'filename': filename,
                    'date': date,
                    'summary': summary,
                    'patterns': patterns
                })
    
    # Sort by date
    results.sort(key=lambda x: x['date'])
    
    # Analysis
    print(f"\n📊 TEST HISTORY ANALYSIS ({len(results)} runs)")
    print("=" * 100)
    
    # Group by day
    daily_stats = defaultdict(list)
    for result in results:
        day = result['date'].strftime('%Y-%m-%d')
        daily_stats[day].append(result)
    
    print(f"\n📅 DAILY BREAKDOWN:")
    print("-" * 100)
    for day in sorted(daily_stats.keys()):
        day_results = daily_stats[day]
        completed_runs = [r for r in day_results if r['summary']['status'] == 'completed']
        
        if completed_runs:
            avg_failed = sum(r['summary']['failed'] for r in completed_runs) / len(completed_runs)
            avg_passed = sum(r['summary']['passed'] for r in completed_runs) / len(completed_runs)
            avg_total = sum(r['summary']['total'] for r in completed_runs) / len(completed_runs)
            
            failure_range = f"{min(r['summary']['failed'] for r in completed_runs)}-{max(r['summary']['failed'] for r in completed_runs)}"
            
            print(f"{day}: {len(day_results)} runs, {len(completed_runs)} completed")
            print(f"    Avg: {avg_failed:.1f} failed, {avg_passed:.1f} passed, {avg_total:.1f} total")
            print(f"    Range: {failure_range} failures")
        else:
            print(f"{day}: {len(day_results)} runs (all incomplete/errors)")
        print()
    
    # Identify consistent patterns
    print(f"\n🎯 CONSISTENCY ANALYSIS:")
    print("-" * 100)
    
    completed_runs = [r for r in results if r['summary']['status'] == 'completed']
    if completed_runs:
        # Group by test pattern and total count
        pattern_groups = defaultdict(list)
        for result in completed_runs:
            # Create signature based on test patterns and total count
            patterns = sorted(result['patterns']['test_patterns'])
            total = result['summary']['total']
            signature = f"{','.join(patterns)}:{total}"
            pattern_groups[signature].append(result)
        
        print("Test run signatures (pattern:total_tests):")
        for signature, runs in sorted(pattern_groups.items(), key=lambda x: len(x[1]), reverse=True):
            if len(runs) >= 2:  # Only show signatures with multiple runs
                failures = [r['summary']['failed'] for r in runs]
                failure_counts = Counter(failures)
                
                print(f"\n  {signature} ({len(runs)} runs):")
                print(f"    Failure counts: {dict(failure_counts)}")
                
                if len(set(failures)) == 1:
                    print(f"    ✅ PERFECTLY CONSISTENT: Always {failures[0]} failures")
                else:
                    print(f"    ❌ INCONSISTENT: {min(failures)}-{max(failures)} failures")
    
    # Recent trend analysis
    print(f"\n📈 RECENT TRENDS (Last 10 completed runs):")
    print("-" * 100)
    recent_completed = [r for r in results if r['summary']['status'] == 'completed'][-10:]
    
    for result in recent_completed:
        date_str = result['date'].strftime('%m-%d %H:%M')
        summary = result['summary']
        patterns = ', '.join(result['patterns']['test_patterns'][:2])
        
        status_icon = "✅" if summary['failed'] == 0 else f"❌({summary['failed']})"
        
        print(f"  {date_str}: {status_icon} {summary['passed']:3d}P {summary['failed']:2d}F {summary['total']:3d}T | {patterns}")
    
    # Failure frequency analysis
    print(f"\n🔥 FAILURE FREQUENCY:")
    print("-" * 100)
    
    all_failures = []
    for result in completed_runs:
        all_failures.extend(result['patterns']['specific_failures'])
    
    if all_failures:
        failure_counts = Counter(all_failures)
        print("Most frequent failing tests:")
        for failure, count in failure_counts.most_common(10):
            print(f"  {count:2d}x {failure}")
    
    # Summary statistics
    print(f"\n📊 SUMMARY STATISTICS:")
    print("-" * 100)
    
    if completed_runs:
        all_failures = [r['summary']['failed'] for r in completed_runs]
        all_totals = [r['summary']['total'] for r in completed_runs]
        
        print(f"Total completed test runs: {len(completed_runs)}")
        print(f"Date range: {min(r['date'] for r in completed_runs).strftime('%Y-%m-%d')} to {max(r['date'] for r in completed_runs).strftime('%Y-%m-%d')}")
        print(f"Failure count range: {min(all_failures)} to {max(all_failures)}")
        print(f"Average failures per run: {sum(all_failures)/len(all_failures):.1f}")
        print(f"Test count range: {min(all_totals)} to {max(all_totals)}")
        print(f"Most common failure count: {Counter(all_failures).most_common(1)[0]}")
        
        # Stability assessment
        unique_failure_counts = len(set(all_failures))
        if unique_failure_counts == 1:
            print("🎯 ASSESSMENT: Tests are PERFECTLY STABLE")
        elif unique_failure_counts <= 3:
            print("✅ ASSESSMENT: Tests are MOSTLY STABLE")
        else:
            print("❌ ASSESSMENT: Tests are UNSTABLE/FLAKY")

if __name__ == '__main__':
    main()
EOF

chmod +x "$ANALYSIS_DIR/$TIMESTAMP/analyze_history.py"

echo "🔄 Running analysis..."
cd "$ANALYSIS_DIR/$TIMESTAMP"
python3 analyze_history.py "$LOG_DIR" | tee analysis_report.txt

echo ""
echo "✅ Analysis complete!"
echo "📄 Full report saved to: $ANALYSIS_DIR/$TIMESTAMP/analysis_report.txt"