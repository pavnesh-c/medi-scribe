#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://127.0.0.1:5000/api/v1"

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# Test health check
echo "Testing health check..."
curl -s "${BASE_URL}/health" | grep -q "ok"
print_result $? "Health check"

# Test upload session initialization
echo "Testing upload session initialization..."
SESSION_ID=$(curl -s -X POST "${BASE_URL}/upload/init" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "test_session_123",
        "file_name": "test_audio.wav",
        "total_size": 1024,
        "total_chunks": 2
    }' | jq -r '.id')
print_result $? "Upload session initialization"

# Test chunk upload
echo "Testing chunk upload..."
# Create a test audio file and split it into chunks
dd if=/dev/urandom of=test_audio.wav bs=512 count=2 2>/dev/null
split -b 512 test_audio.wav chunk_

# Upload first chunk
curl -s -X POST "${BASE_URL}/upload/chunk" \
    -F "session_id=${SESSION_ID}" \
    -F "chunk_number=0" \
    -F "chunk=@chunk_aa" | grep -q "ok"
print_result $? "First chunk upload"

# Upload second chunk
curl -s -X POST "${BASE_URL}/upload/chunk" \
    -F "session_id=${SESSION_ID}" \
    -F "chunk_number=1" \
    -F "chunk=@chunk_ab" | grep -q "ok"
print_result $? "Second chunk upload"

# Clean up test files
rm -f test_audio.wav chunk_*

# Test recording upload (now using the combined file)
echo "Testing recording upload..."
RECORDING_ID=$(curl -s -X POST "${BASE_URL}/recording/upload" \
    -F "session_id=${SESSION_ID}" \
    -F "file=@test_audio.wav" | jq -r '.id')
print_result $? "Recording upload"

# Test transcription start
echo "Testing transcription start..."
curl -s -X POST "${BASE_URL}/transcription/start" \
    -H "Content-Type: application/json" \
    -d "{\"recording_id\": \"${RECORDING_ID}\"}" | grep -q "ok"
print_result $? "Transcription start"

# Test transcription status
echo "Testing transcription status..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS=$(curl -s "${BASE_URL}/transcription/${RECORDING_ID}" | jq -r '.status')
    if [ "$STATUS" = "completed" ]; then
        print_result 0 "Transcription completed"
        break
    elif [ "$STATUS" = "failed" ]; then
        print_result 1 "Transcription failed"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    print_result 1 "Transcription timeout"
fi

# Test SOAP note generation
echo "Testing SOAP note generation..."
SOAP_ID=$(curl -s -X POST "${BASE_URL}/soap/generate" \
    -H "Content-Type: application/json" \
    -d "{\"recording_id\": \"${RECORDING_ID}\"}" | jq -r '.id')
print_result $? "SOAP note generation"

# Test SOAP note retrieval
echo "Testing SOAP note retrieval..."
curl -s "${BASE_URL}/soap/${SOAP_ID}" | grep -q "id"
print_result $? "SOAP note retrieval"

# Test upload session deletion
echo "Testing upload session deletion..."
curl -s -X DELETE "${BASE_URL}/upload/${SESSION_ID}" | grep -q "ok"
print_result $? "Upload session deletion"

echo -e "\n${GREEN}All tests completed successfully!${NC}" 