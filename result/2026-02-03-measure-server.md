# Execution Result (2026-02-03)

## Command
`powershell -ExecutionPolicy Bypass -File scripts\measure_server.ps1 -HealthTimeoutSec 5 -PromptTimeoutSec 10 -ShutdownTimeoutSec 5`

## Output
```
SERVER_PID 6168
HEALTH_OK in 756ms
{"status":"ok","initialized":true,"coreAvailable":true}
PROMPT_FAIL in 10087ms
The request was aborted: The operation has timed out.
```

## Notes
- The environment timed out the outer command (~11.6s), but the script produced output.
- The prompt call timed out at 10s; a longer timeout is required to confirm prompt success.
