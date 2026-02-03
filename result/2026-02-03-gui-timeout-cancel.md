# GUI Timeout/Cancel Integration (2026-02-03)

- Updated `app.py` to use `/prompt/start` + `/prompt/result` flow.
- Added cancel button that calls `/cancel` with the current requestId.
- Emits requestId to chat and disables/enables controls appropriately.
