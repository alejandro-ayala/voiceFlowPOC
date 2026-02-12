#!/bin/bash
# Health check script for VoiceFlow PoC
# Exit 0 if healthy, 1 if unhealthy

# Try to call the health endpoint
# Using curl with timeout and fail-fast options
curl -f -s -o /dev/null --max-time 5 http://localhost:8000/api/v1/health/ || exit 1

# If curl succeeds, container is healthy
exit 0
