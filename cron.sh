#!/bin/bash
/usr/bin/curl -sk -X POST "https://157.151.215.192/scheduler/run" \
  -H "X-Scheduler-Key: 3bcee90aed169553459c1eae695828bfd00873585b8110a7b64490a74540da9c" \
  --max-time 120 --fail >> /home/ubuntu/LexiPulse/cron.log 2>&1
