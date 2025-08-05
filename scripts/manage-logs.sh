#!/bin/bash
# Log management utility for GAIA platform

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log directories
LOG_BASE="logs"
TEST_LOGS="$LOG_BASE/tests"
DOCKER_LOGS="$LOG_BASE/docker"
SERVICE_LOGS="$LOG_BASE/services"
PERF_LOGS="$LOG_BASE/performance"

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  show [type]      Show recent logs (type: test, docker, service, perf, all)"
    echo "  clean [days]     Clean logs older than N days (default: 7)"
    echo "  archive [name]   Archive all logs to a zip file"
    echo "  tail [type]      Tail the latest log of specified type"
    echo "  size             Show log directory sizes"
    echo "  path [type]      Show log directory path"
    echo ""
    echo "Examples:"
    echo "  $0 show test           # Show recent test logs"
    echo "  $0 clean 30            # Clean logs older than 30 days"
    echo "  $0 tail test           # Tail latest test log"
    echo "  $0 archive pre-deploy  # Archive logs before deployment"
}

# Function to ensure log directories exist
ensure_log_dirs() {
    mkdir -p "$TEST_LOGS/pytest"
    mkdir -p "$TEST_LOGS/e2e"
    mkdir -p "$DOCKER_LOGS"
    mkdir -p "$SERVICE_LOGS"
    mkdir -p "$PERF_LOGS"
}

# Function to show recent logs
show_logs() {
    local log_type=$1
    
    case $log_type in
        test)
            echo -e "${BLUE}Recent test logs:${NC}"
            ls -lt "$TEST_LOGS"/**/*.log 2>/dev/null | head -10
            ;;
        docker)
            echo -e "${BLUE}Recent Docker logs:${NC}"
            ls -lt "$DOCKER_LOGS"/*.log 2>/dev/null | head -10
            ;;
        service)
            echo -e "${BLUE}Recent service logs:${NC}"
            ls -lt "$SERVICE_LOGS"/*.log 2>/dev/null | head -10
            ;;
        perf)
            echo -e "${BLUE}Recent performance logs:${NC}"
            ls -lt "$PERF_LOGS"/*.log 2>/dev/null | head -10
            ;;
        all|*)
            echo -e "${BLUE}Recent logs (all types):${NC}"
            ls -lt "$LOG_BASE"/**/*.log 2>/dev/null | head -20
            ;;
    esac
}

# Function to clean old logs
clean_logs() {
    local days=${1:-7}
    
    echo -e "${YELLOW}Cleaning logs older than $days days...${NC}"
    
    # Find and remove old logs
    find "$LOG_BASE" -name "*.log" -type f -mtime +$days -exec rm {} \; 2>/dev/null
    
    # Count remaining logs
    local remaining=$(find "$LOG_BASE" -name "*.log" -type f 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Cleanup complete. $remaining log files remaining.${NC}"
}

# Function to archive logs
archive_logs() {
    local archive_name=${1:-"logs-$(date +%Y%m%d-%H%M%S)"}
    local archive_path="$archive_name.zip"
    
    echo -e "${BLUE}Creating archive: $archive_path${NC}"
    
    # Create zip archive
    zip -r "$archive_path" "$LOG_BASE"/**/*.log 2>/dev/null
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$archive_path" | cut -f1)
        echo -e "${GREEN}✅ Archive created: $archive_path ($size)${NC}"
    else
        echo -e "${RED}❌ Failed to create archive${NC}"
    fi
}

# Function to tail latest log
tail_log() {
    local log_type=$1
    local log_file=""
    
    case $log_type in
        test)
            log_file=$(ls -t "$TEST_LOGS"/pytest/*.log 2>/dev/null | head -1)
            ;;
        docker)
            log_file=$(ls -t "$DOCKER_LOGS"/*.log 2>/dev/null | head -1)
            ;;
        service)
            log_file=$(ls -t "$SERVICE_LOGS"/*.log 2>/dev/null | head -1)
            ;;
        perf)
            log_file=$(ls -t "$PERF_LOGS"/*.log 2>/dev/null | head -1)
            ;;
        *)
            echo -e "${RED}Unknown log type: $log_type${NC}"
            exit 1
            ;;
    esac
    
    if [ -n "$log_file" ]; then
        echo -e "${BLUE}Tailing: $log_file${NC}"
        echo "Press Ctrl+C to stop..."
        tail -f "$log_file"
    else
        echo -e "${YELLOW}No $log_type logs found${NC}"
    fi
}

# Function to show log sizes
show_sizes() {
    echo -e "${BLUE}Log directory sizes:${NC}"
    echo ""
    
    if [ -d "$TEST_LOGS" ]; then
        local test_size=$(du -sh "$TEST_LOGS" 2>/dev/null | cut -f1)
        echo "Test logs:        $test_size"
    fi
    
    if [ -d "$DOCKER_LOGS" ]; then
        local docker_size=$(du -sh "$DOCKER_LOGS" 2>/dev/null | cut -f1)
        echo "Docker logs:      $docker_size"
    fi
    
    if [ -d "$SERVICE_LOGS" ]; then
        local service_size=$(du -sh "$SERVICE_LOGS" 2>/dev/null | cut -f1)
        echo "Service logs:     $service_size"
    fi
    
    if [ -d "$PERF_LOGS" ]; then
        local perf_size=$(du -sh "$PERF_LOGS" 2>/dev/null | cut -f1)
        echo "Performance logs: $perf_size"
    fi
    
    echo ""
    local total_size=$(du -sh "$LOG_BASE" 2>/dev/null | cut -f1)
    echo -e "${GREEN}Total: $total_size${NC}"
}

# Function to show log path
show_path() {
    local log_type=$1
    
    case $log_type in
        test)
            echo "$TEST_LOGS"
            ;;
        docker)
            echo "$DOCKER_LOGS"
            ;;
        service)
            echo "$SERVICE_LOGS"
            ;;
        perf)
            echo "$PERF_LOGS"
            ;;
        all|*)
            echo "$LOG_BASE"
            ;;
    esac
}

# Main script logic
ensure_log_dirs

case ${1:-help} in
    show)
        show_logs ${2:-all}
        ;;
    clean)
        clean_logs $2
        ;;
    archive)
        archive_logs $2
        ;;
    tail)
        tail_log ${2:-test}
        ;;
    size)
        show_sizes
        ;;
    path)
        show_path ${2:-all}
        ;;
    help|*)
        show_usage
        ;;
esac