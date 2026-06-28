# 📘 WeeklyOrganizer Spec — CleanSlate PC Assistant

This document defines the behavior of the `WeeklyOrganizerNode` inside the CleanSlate PC Assistant.

## 1. Trigger Context
The weekly organizer is automated to run periodically (e.g. triggered via Pub/Sub or CLI scheduler commands).

## 2. Core Behaviors

### 2.1 User Control Check
- **Rule**: Weekly automation runs only when enabled by the user in `~/.cleanslate/config.json`.
- **Disabled-Case Summary Behavior**:
  - If the flag `weekly_automation_enabled` is set to `False`, the node performs an early exit.
  - An audit log entry is written with `result="skipped"` and `reason="Weekly automation is disabled."`.
  - Emits a `WeeklySummary` payload with `automation_ran=False` and `human_readable_report="Weekly automation disabled. No actions performed."` and routes to `disabled`.

### 2.2 Safe Mode Execution
- **Rules**:
  - When enabled, the organizer forces `safe_mode=True`.
  - Disallows destructive deletions (`allow_deletes=False`) and compressions (`allow_compress=False`).
  - Allows only file moves (`allow_moves=True`) and archives (`allow_archives=True`).
  - Utilizes the pre-approved folder scope policy.
  - Automatically bypasses interactive Human-in-the-loop (HITL) checkpoints.
