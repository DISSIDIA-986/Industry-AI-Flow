# Capstone Demo Modes

This document defines the three demo-first operation modes used by Industry AI Flow.

## Modes

1. `live_hybrid`
- Default route: `hybrid_auto`
- Cloud calls: enabled
- Replay: disabled
- Use when network/API is healthy and you want best quality.

2. `local_safe`
- Default route: `local_only`
- Cloud calls: disabled (unless admin override is enabled)
- Replay: disabled
- Use as offline-safe fallback during presentation.

3. `scripted_replay`
- Default route: `local_only`
- Cloud calls: disabled
- Replay: enabled
- Use when external dependencies are unstable and deterministic output is required.

## API

## Get current mode

`GET /api/v1/demo/mode`

Returns current mode, profile and replay catalog size.

## Update mode (admin/ops/platform_admin only)

`POST /api/v1/demo/mode`

Request body:

```json
{
  "mode": "live_hybrid",
  "allow_cloud_override": false
}
```

## Replay health

`GET /api/v1/demo/replay/health`

## Operational notes

- Workflow endpoint (`/api/v1/workflow/query`) and dispatch endpoint (`/api/v1/query/dispatch`) both honor demo mode.
- In `scripted_replay`, the system returns curated responses and skips normal model invocation.
- In `local_safe`, cloud-only requests are force-localized to prevent demo interruptions.
