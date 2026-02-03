# Server Timeout/Cancel Implementation (2026-02-03)

- Added request timeout handling for `/prompt` with `timeoutMs` (default 120s).
- Added in-flight tracking with `requestId` and `/cancel` endpoint to abort a request.
- Added client disconnect handling to terminate the child process.
