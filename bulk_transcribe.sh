#!/bin/bash

# Configuration
WHISPER_DIR="$HOME/software/whisper.cpp"
MODEL_PATH="models/ggml-large-v3-turbo.bin"
INPUT_DIR="/mnt/gpx"
OUTPUT_DIR="/mnt/voice_memos"
COUNTER_FILE="$OUTPUT_DIR/.last_counter"
HASH_CACHE="$OUTPUT_DIR/.file_hashes"

# Optional features (set to empty string to disable)
OPENVINO_SETUP="/nvme/openvino/runtime/setupvars.sh"  # Set to "" to disable OpenVINO
VAD_MODEL_PATH="models/ggml-silero-v5.1.2.bin"       # Set to "" to disable VAD
OLLAMA_BASE_URL="http://localhost:11434"              # Set to "" to disable LLM extraction
OLLAMA_MODEL="llama3.2:3b"

# Whisper configuration
WHISPER_MODE="cli"  # "cli" for whisper-cli, "server" for whisper-server
WHISPER_SERVER_URL="http://localhost:8080"  # URL if using server mode
OPENVINO_DEVICE="GPU"  # GPU, CPU, or AUTO (only affects OpenVINO encoder)
WHISPER_LANGUAGE="auto"  # auto, en, es, fr, etc.
WHISPER_EXTRA_FLAGS=""  # Additional whisper flags, e.g., "--no-timestamps --ml 0"

# Supported audio formats
AUDIO_FORMATS="mp3|MP3|wav|WAV|flac|FLAC"

# Batch processing limits
BATCH_WARNING_THRESHOLD=100  # Warn if more than this many files

# Initialize counter
if [ -f "$COUNTER_FILE" ]; then
    COUNTER=$(cat "$COUNTER_FILE")
else
    COUNTER=0
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR" || { echo "Failed to create output directory"; exit 1; }

# Create hash cache if it doesn't exist
touch "$HASH_CACHE"

# Setup logging
LOG_FILE="$OUTPUT_DIR/transcription_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

# Trap for clean shutdown
trap 'echo "Interrupted. Saving state..."; echo "$COUNTER" > "$COUNTER_FILE"; exit 130' INT TERM

# Source OpenVINO setup if enabled
if [ -n "$OPENVINO_SETUP" ] && [ -f "$OPENVINO_SETUP" ]; then
    echo "Setting up OpenVINO environment..."
    source "$OPENVINO_SETUP"
else
    echo "OpenVINO not configured or setup script not found"
fi

# Verify whisper directory exists
if [ ! -d "$WHISPER_DIR" ]; then
    echo "Error: Whisper directory not found: $WHISPER_DIR"
    exit 1
fi

# Verify whisper-cli exists
if [ ! -x "$WHISPER_DIR/build/bin/whisper-cli" ]; then
    echo "Error: whisper-cli not found or not executable at $WHISPER_DIR/build/bin/whisper-cli"
    exit 1
fi

echo "Starting improved bulk transcription with duplicate detection..."
echo "Current counter: $COUNTER"
echo "Log file: $LOG_FILE"
echo

# Function to get file hash (fast, size + samples from beginning, middle, end)
get_file_signature() {
    local file="$1"
    local size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
    
    if [ -z "$size" ] || [ "$size" -eq 0 ]; then
        echo "empty_file"
        return
    fi
    
    # Sample beginning, middle, and end (1KB each)
    local head_hash=$(dd if="$file" bs=1024 count=1 2>/dev/null | md5sum | cut -d' ' -f1)
    local mid_hash=""
    local tail_hash=""
    
    if [ "$size" -gt 2048 ]; then
        mid_hash=$(dd if="$file" bs=1024 skip=$((size/2048)) count=1 2>/dev/null | md5sum | cut -d' ' -f1)
    fi
    
    if [ "$size" -gt 1024 ]; then
        tail_hash=$(dd if="$file" bs=1024 skip=$((size/1024-1)) count=1 2>/dev/null | md5sum | cut -d' ' -f1)
    fi
    
    echo "${size}_${head_hash}_${mid_hash}_${tail_hash}"
}

# Function to extract datetime from transcript
extract_datetime_from_transcript() {
    local txt_file="$1"
    local srt_file="${txt_file%.txt}.srt"
    
    if [ ! -f "$txt_file" ]; then
        return 1
    fi
    
    # First try explicit pattern matching on entire transcript
    local explicit_match=$(grep -iE "(today is|the time is|it's|it is).*(january|february|march|april|may|june|july|august|september|october|november|december|[0-9]{1,2}:[0-9]{2}|[0-9]{1,2} (am|pm)|[0-9]{1,2} o'clock|20[0-9]{2})" "$txt_file" | tail -1)
    
    # Check if we got a useful match (not just "it is" without a proper time/date)
    if [ -n "$explicit_match" ]; then
        # Try to extract a structured format from the match
        local time_only=$(echo "$explicit_match" | grep -oE "([0-9]{1,2}:[0-9]{2}(\s*(am|pm|AM|PM))?|[0-9]{1,2}\s*o'clock)" | tail -1)
        local date_pattern=$(echo "$explicit_match" | grep -oE "(january|february|march|april|may|june|july|august|september|october|november|december)\s+[0-9]{1,2}" | tail -1)
        
        # If we found a clear time but no date, format it for LLM
        if [ -n "$time_only" ] && [ -z "$date_pattern" ]; then
            # Convert to 24h format if needed
            local formatted_time=$(echo "$time_only" | awk '{
                # Handle "o\'clock" format
                if (match($0, /([0-9]+) o.clock/)) {
                    hour = substr($0, RSTART, RLENGTH)
                    gsub(/[^0-9]/, "", hour)
                    printf "%02d00", hour
                } else {
                    # Handle HH:MM format
                    time = $1
                    ampm = tolower($2)
                    split(time, parts, ":")
                    hour = parts[1]
                    min = parts[2]
                    if (ampm == "pm" && hour != 12) hour += 12
                    if (ampm == "am" && hour == 12) hour = 0
                    printf "%02d%02d", hour, min
                }
            }')
            
            if [[ "$formatted_time" =~ ^[0-9]{4}$ ]]; then
                echo "LLM_EXTRACTED: $formatted_time"
                return 0
            fi
        fi
        
        # If pattern match found something but couldn't extract structured format,
        # show it but continue to LLM
        echo "PATTERN_MATCH: $explicit_match"
    fi
    
    # Try LLM extraction if ollama is available
    if [ -n "$OLLAMA_BASE_URL" ] && command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
        extract_datetime_with_llm "$txt_file"
    fi
}

# Function to use local LLM for datetime extraction
extract_datetime_with_llm() {
    local txt_file="$1"
    local transcript_content=$(cat "$txt_file")
    
    # Skip if transcript is too long (avoid API limits)
    if [ ${#transcript_content} -gt 4000 ]; then
        # Use last 3000 characters for LLM analysis
        transcript_content=$(tail -c 3000 "$txt_file")
    fi
    
    local prompt="Extract date and time from this voice memo. Look for phrases like 'today is', 'the time is', 'it's currently', etc.

Rules:
- If full date and time found: YYYY-MM-DD_HHMM
- If only date: YYYY-MM-DD
- If only time: HHMM
- If nothing found: NONE
- Use 24-hour format for time
- For relative dates like 'today' or 'yesterday', return NONE

Transcript: $transcript_content

Response (just the format, nothing else):"

    # Try ollama API call
    local response=$(curl -s -X POST "${OLLAMA_BASE_URL}/api/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$OLLAMA_MODEL\",
            \"prompt\": \"$prompt\",
            \"stream\": false,
            \"options\": {
                \"temperature\": 0.1,
                \"num_predict\": 50
            }
        }" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        local extracted=$(echo "$response" | jq -r '.response' 2>/dev/null | tr -d '\n' | grep -oE '([0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{4}|NONE)' | head -1)
        if [ -n "$extracted" ] && [ "$extracted" != "NONE" ]; then
            echo "LLM_EXTRACTED: $extracted"
            return 0
        fi
    fi
    
    return 1
}

# Function to estimate recording start time from transcript timestamp
estimate_start_time() {
    local transcript_file="$1"
    local srt_file="$2"
    local datetime_str="$3"
    
    # Handle both full datetime (YYYY-MM-DD_HHMM) and time-only (HHMM) formats
    local date_part=""
    local time_part=""
    
    if [[ "$datetime_str" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}$ ]]; then
        # Full datetime
        date_part="${datetime_str%_*}"  # YYYY-MM-DD
        time_part="${datetime_str#*_}"  # HHMM
    elif [[ "$datetime_str" =~ ^[0-9]{4}$ ]]; then
        # Time only
        time_part="$datetime_str"  # HHMM
        # For time-only, we'll use today's date as a working date
        date_part=$(date +%Y-%m-%d)
    else
        echo ""  # Return empty for other formats
        return
    fi
    
    # Extract date and time components
    local date_part="${datetime_str%_*}"  # YYYY-MM-DD
    local time_part="${datetime_str#*_}"  # HHMM
    local hours="${time_part:0:2}"
    local minutes="${time_part:2:2}"
    
    # Find when the datetime was spoken in the SRT file
    # We need to search for the original text that triggered the datetime extraction
    local spoken_time=""
    
    if [ -f "$srt_file" ]; then
        # Search for timestamp patterns in SRT, looking for the last occurrence
        # This is a bit tricky because we need to correlate the extracted datetime
        # with where it appears in the SRT
        
        # Get the last few subtitle blocks that might contain time references
        local srt_content=$(cat "$srt_file")
        
        # Extract SRT timestamp for lines containing time patterns
        # Format: HH:MM:SS,mmm --> HH:MM:SS,mmm
        local matches=$(echo "$srt_content" | grep -B2 -E "(time is|it's|it is)( currently)?.*(${hours}:${minutes}|$((10#$hours % 12)):${minutes})" | grep -E "^[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}" | tail -1)
        
        if [ -n "$matches" ]; then
            # Extract the start timestamp (HH:MM:SS)
            spoken_time=$(echo "$matches" | cut -d' ' -f1 | cut -d',' -f1)
        else
            # Fallback: assume datetime is mentioned near the end (last 30 seconds)
            # Get the last timestamp in the file
            local last_timestamp=$(grep -E "^[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}" "$srt_file" | tail -1 | cut -d' ' -f1 | cut -d',' -f1)
            if [ -n "$last_timestamp" ]; then
                # Assume datetime was spoken 5 seconds before end
                spoken_time="$last_timestamp"
            fi
        fi
    fi
    
    # If we couldn't find when it was spoken, can't adjust
    if [ -z "$spoken_time" ]; then
        echo ""
        return
    fi
    
    # Convert SRT timestamp to seconds
    local srt_hours=$(echo "$spoken_time" | cut -d':' -f1)
    local srt_minutes=$(echo "$spoken_time" | cut -d':' -f2)
    local srt_seconds=$(echo "$spoken_time" | cut -d':' -f3)
    local srt_total_seconds=$((10#$srt_hours * 3600 + 10#$srt_minutes * 60 + 10#$srt_seconds))
    
    # Convert spoken time to seconds since midnight
    local spoken_total_seconds=$((10#$hours * 3600 + 10#$minutes * 60))
    
    # Calculate recording start time
    local start_seconds=$((spoken_total_seconds - srt_total_seconds))
    
    # Handle negative times (recording started before midnight)
    if [ $start_seconds -lt 0 ]; then
        # Recording started yesterday
        start_seconds=$((start_seconds + 86400))  # Add 24 hours
        
        # Adjust date to yesterday
        if command -v date >/dev/null 2>&1; then
            # Try GNU date first, then BSD date
            date_part=$(date -d "$date_part -1 day" +%Y-%m-%d 2>/dev/null || \
                       date -v-1d -jf "%Y-%m-%d" "$date_part" +%Y-%m-%d 2>/dev/null || \
                       echo "$date_part")  # Fallback: keep original date
        fi
    fi
    
    # Convert back to hours and minutes
    local start_hours=$((start_seconds / 3600))
    local start_minutes=$(((start_seconds % 3600) / 60))
    
    # Format the adjusted datetime
    local adjusted_time=$(printf "%02d%02d" "$start_hours" "$start_minutes")
    
    # Return in appropriate format
    if [[ "$datetime_str" =~ ^[0-9]{4}$ ]]; then
        # Time-only input, return time-only output
        echo "$adjusted_time"
    else
        # Full datetime input, return full datetime
        echo "${date_part}_${adjusted_time}"
    fi
}

# Function to generate next counter (handles rollover)
get_next_counter() {
    local current="$1"
    
    if [ $current -lt 9999 ]; then
        echo $((current + 1))
    else
        # Roll over to alphanumeric: a0001, a0002, ..., a9999, b0001, etc.
        if [ -f "${COUNTER_FILE}.alpha" ]; then
            local alpha_prefix=$(cat "${COUNTER_FILE}.alpha")
        else
            local alpha_prefix="a"
            echo "$alpha_prefix" > "${COUNTER_FILE}.alpha"
        fi
        
        local alpha_counter_file="${COUNTER_FILE}.${alpha_prefix}"
        if [ -f "$alpha_counter_file" ]; then
            local alpha_num=$(cat "$alpha_counter_file")
        else
            local alpha_num=0
        fi
        
        if [ $alpha_num -lt 9999 ]; then
            local new_alpha_num=$((alpha_num + 1))
            echo "$new_alpha_num" > "$alpha_counter_file"
            # Return special marker to indicate alpha counter
            echo "ALPHA:${alpha_prefix}:${new_alpha_num}"
        else
            # Move to next letter
            local next_alpha=$(echo "$alpha_prefix" | tr 'a-y' 'b-z')
            if [ "$next_alpha" = "$alpha_prefix" ]; then
                echo "Warning: Reached maximum memo count (z9999)!" >&2
                echo "9999"
            else
                echo "$next_alpha" > "${COUNTER_FILE}.alpha"
                echo "1" > "${COUNTER_FILE}.${next_alpha}"
                echo "ALPHA:${next_alpha}:1"
            fi
        fi
    fi
}

# Function to format output name
format_output_name() {
    local counter_info="$1"
    local datetime="$2"
    
    local prefix="memo"
    
    # Check if this is an alpha counter
    if [[ "$counter_info" == ALPHA:* ]]; then
        IFS=':' read -r _ alpha_prefix alpha_num <<< "$counter_info"
        prefix="memo_${alpha_prefix}$(printf "%04d" $alpha_num)"
    else
        prefix="memo_$(printf "%04d" $counter_info)"
    fi
    
    if [ -n "$datetime" ]; then
        # Handle different datetime formats:
        # Full: memo_0042_2025-06-21_1430
        # Date only: memo_0042_2025-06-21
        # Time only: memo_0042_T1430 (T prefix to indicate time-only)
        if [[ "$datetime" =~ ^[0-9]{4}$ ]]; then
            # Time only - add T prefix for clarity
            echo "${prefix}_T${datetime}"
        else
            # Date or date+time
            echo "${prefix}_${datetime}"
        fi
    else
        # Format: memo_0043
        echo "$prefix"
    fi
}

# Build whisper command
build_whisper_command() {
    local input_file="$1"
    local output_prefix="$2"
    
    local cmd="./build/bin/whisper-cli"
    cmd="$cmd -m \"$MODEL_PATH\""
    
    # Add VAD if configured
    if [ -n "$VAD_MODEL_PATH" ]; then
        cmd="$cmd --vad --vad-model \"$VAD_MODEL_PATH\""
    fi
    
    # Add device configuration
    if [ -n "$OPENVINO_SETUP" ] && [ -n "$OPENVINO_DEVICE" ]; then
        cmd="$cmd --ov-e-device $OPENVINO_DEVICE"
    fi
    
    # Add language if not auto
    if [ "$WHISPER_LANGUAGE" != "auto" ]; then
        cmd="$cmd -l $WHISPER_LANGUAGE"
    fi
    
    # Add extra flags
    if [ -n "$WHISPER_EXTRA_FLAGS" ]; then
        cmd="$cmd $WHISPER_EXTRA_FLAGS"
    fi
    
    # Add input/output
    cmd="$cmd -f \"$input_file\" -otxt -oj -osrt -of \"$output_prefix\""
    
    echo "$cmd"
}

# Function to transcribe using whisper-server
transcribe_with_server() {
    local input_file="$1"
    local output_prefix="$2"
    
    # Check if server is reachable
    if ! curl -s -f "$WHISPER_SERVER_URL/health" >/dev/null 2>&1; then
        echo "Error: whisper-server not reachable at $WHISPER_SERVER_URL"
        return 1
    fi
    
    # Send file to server
    local response=$(curl -s -X POST \
        -F "file=@$input_file" \
        -F "language=$WHISPER_LANGUAGE" \
        -F "output_format=all" \
        "$WHISPER_SERVER_URL/transcribe")
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to transcribe with server"
        return 1
    fi
    
    # Parse response and save outputs
    # This assumes the server returns JSON with text, srt, and json fields
    echo "$response" | jq -r '.text' > "${output_prefix}.txt"
    echo "$response" | jq -r '.srt' > "${output_prefix}.srt"
    echo "$response" | jq -r '.json' > "${output_prefix}.json"
    
    return 0
}

# Collect all audio files with metadata
declare -A file_signatures
declare -a files_to_process

echo "Scanning for audio files and detecting duplicates..."
echo "Looking in: $INPUT_DIR"
echo "File patterns: $AUDIO_FORMATS"

# Find all audio files, sort by path for consistent ordering
while IFS= read -r -d '' file; do
    signature=$(get_file_signature "$file")
    
    # Check if we've seen this signature before
    if grep -q "^$signature " "$HASH_CACHE"; then
        existing_name=$(grep "^$signature " "$HASH_CACHE" | cut -d' ' -f2-)
        echo "DUPLICATE FOUND: $file (matches $existing_name)"
        continue
    fi
    
    # Check against current batch
    if [[ -n "${file_signatures[$signature]}" ]]; then
        echo "DUPLICATE FOUND: $file (matches ${file_signatures[$signature]})"
        continue
    fi
    
    # Record this file
    file_signatures[$signature]="$file"
    files_to_process+=("$file")
    
done < <(find "$INPUT_DIR" -type f \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.flac" \) -print0 | sort -z)

echo "Found ${#files_to_process[@]} unique audio files to process"

# Warn if large batch
if [ ${#files_to_process[@]} -gt $BATCH_WARNING_THRESHOLD ]; then
    echo
    echo "Warning: Found ${#files_to_process[@]} files to process. This may take a long time."
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

echo

# Process each unique file
current_file=0
for file in "${files_to_process[@]}"; do
    # Get file info for display
    relative_path=${file#$INPUT_DIR/}
    current_file=$((current_file + 1))
    
    # Increment counter FIRST (before any potential failures)
    COUNTER=$(get_next_counter $COUNTER)
    
    # Save counter immediately to ensure consistency
    if [[ "$COUNTER" == ALPHA:* ]]; then
        # Alpha counter is already saved in get_next_counter
        echo "9999" > "$COUNTER_FILE"
    else
        echo "$COUNTER" > "$COUNTER_FILE"
    fi
    
    # Initial output name (we'll potentially update this after transcription)
    output_name=$(format_output_name "$COUNTER" "")
    
    echo "Processing [$current_file/${#files_to_process[@]}]: $relative_path"
    echo "Output name: $output_name"
    
    # Transcribe using appropriate method
    if [ "$WHISPER_MODE" = "server" ]; then
        echo "Using whisper-server at $WHISPER_SERVER_URL"
        transcribe_with_server "$file" "$OUTPUT_DIR/$output_name"
        transcribe_result=$?
    else
        # Build and run whisper command
        cd "$WHISPER_DIR"
        whisper_cmd=$(build_whisper_command "$file" "$OUTPUT_DIR/$output_name")
        echo "Command: $whisper_cmd"
        
        eval "$whisper_cmd"
        transcribe_result=$?
    fi
    
    if [ $transcribe_result -eq 0 ]; then
        echo "✓ Successfully transcribed"
        
        # Try to extract datetime from transcript
        transcript_file="$OUTPUT_DIR/${output_name}.txt"
        srt_file="$OUTPUT_DIR/${output_name}.srt"
        datetime_line=$(extract_datetime_from_transcript "$transcript_file")
        
        if [ -n "$datetime_line" ]; then
            echo "📅 Found datetime: $datetime_line"
            
            # If we got a structured datetime from LLM or pattern match
            if [[ "$datetime_line" == "LLM_EXTRACTED: "* ]]; then
                extracted_dt="${datetime_line#LLM_EXTRACTED: }"
                
                # Try to estimate actual recording start time
                if [[ "$extracted_dt" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}$ ]] || [[ "$extracted_dt" =~ ^[0-9]{4}$ ]]; then
                    if [ -f "$srt_file" ]; then
                        echo "⏰ Estimating recording start time..."
                        adjusted_dt=$(estimate_start_time "$transcript_file" "$srt_file" "$extracted_dt")
                        if [ -n "$adjusted_dt" ]; then
                            echo "📍 Adjusted to recording start: $adjusted_dt"
                            extracted_dt="$adjusted_dt"
                        fi
                    fi
                fi
                
                new_output_name=$(format_output_name "$COUNTER" "$extracted_dt")
                echo "🤖 Renaming to: $new_output_name"
                
                # Rename all output files
                for ext in txt json srt; do
                    if [ -f "$OUTPUT_DIR/${output_name}.${ext}" ]; then
                        mv "$OUTPUT_DIR/${output_name}.${ext}" "$OUTPUT_DIR/${new_output_name}.${ext}"
                    fi
                done
                
                output_name="$new_output_name"
                
            elif [[ "$datetime_line" == "PATTERN_MATCH: "* ]]; then
                # For pattern matches, we need to extract structured datetime
                # This would require additional parsing logic
                echo "📝 Pattern match found, but needs parsing for filename"
                # For now, keep original filename
            fi
        fi
        
        # Record the file signature as processed
        signature=$(get_file_signature "$file")
        echo "$signature $output_name" >> "$HASH_CACHE"
        
    else
        echo "✗ Failed to transcribe: $file"
        echo "   (Kept as $output_name for consistency with source file order)"
    fi
    
    echo "---"
done

# Summary statistics
echo
echo "Bulk transcription complete!"
echo "Processed: ${#files_to_process[@]} files"
echo "Final counter: $COUNTER"
echo "Log saved to: $LOG_FILE"
echo
echo "Configuration used:"
echo "  Whisper model: $MODEL_PATH"
echo "  VAD: $([ -n "$VAD_MODEL_PATH" ] && echo "Enabled" || echo "Disabled")"
echo "  OpenVINO: $([ -n "$OPENVINO_SETUP" ] && echo "Enabled" || echo "Disabled")"
echo "  LLM extraction: $([ -n "$OLLAMA_BASE_URL" ] && echo "Enabled" || echo "Disabled")"
echo
echo "Note: Check the transcripts for spoken timestamps that could be used"
echo "to improve filename dating in future runs."
