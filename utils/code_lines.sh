#!/bin/bash
# Author: Clive Bostock
# Date: 2024-12-27
# Description: Counts the total number of lines in files with a specified extension from a start directory.

usage() {
    echo "Usage: $0 -d <start_directory> -e <file_extension>"
    echo "  -d: Starting directory to search from."
    echo "  -e: File extension to search for (e.g., '.txt')."
    exit 1
}

# Initialize variables
start_directory=""
file_extension=""

# Parse options
while getopts "d:e:" opt; do
    case "$opt" in
        d) start_directory="$OPTARG" ;;
        e) file_extension="$OPTARG" ;;
        *) usage ;;
    esac
done

# Check that both arguments are provided
if [[ -z "$start_directory" || -z "$file_extension" ]]; then
    usage
fi

# Validate that the directory exists
if [[ ! -d "$start_directory" ]]; then
    echo "Error: Start directory '$start_directory' does not exist."
    exit 1
fi

# Find files with the specified extension and count total lines
total_lines=0
while IFS= read -r -d '' file; do
    lines=$(wc -l < "$file")
    total_lines=$((total_lines + lines))
done < <(find "$start_directory" -type f -name "*$file_extension" -print0)

echo "Total number of lines in files with extension '$file_extension': $total_lines"

