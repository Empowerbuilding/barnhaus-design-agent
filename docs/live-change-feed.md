# Live Change-Feed Feature Plan

## Objective
Implement a live change-feed that tracks modifications in the Revit model as they happen, storing them in a rolling log. This will allow the Blueprint agent to query recent changes efficiently (e.g., "what did Michael just do") and correlate model changes with journal analysis for workflow learning.

## Bridge Side (C# - Empowerbuilding/revit-bridge)
1. **Event Subscription:** Subscribe to the `Application.DocumentChanged` event in the bridge `OnStartup`.
2. **Log Structure:** Store changes in a rolling JSONL log file at `C:\ProgramData\RevitMCP\changes.jsonl`.
   - File size will be capped or rotated daily.
   - Entry format: Timestamp, Transaction Name, Operation (Added/Modified/Deleted), Element IDs, Element Category, Element Name.
3. **Performance constraint:** The event handler must be extremely lightweight. No heavy element lookups; rely only on the event args (`GetAddedElementIds()`, `GetModifiedElementIds()`, `GetDeletedElementIds()`). If resolving names is too slow, defer to the agent.
4. **New Command Endpoint:** Add `get_recent_changes` command to the Bridge DLL API.
   - Parameters: `since_timestamp` (optional) or `last_n` (default 50).
   - Returns: Parsed entries from the `changes.jsonl` log.

## Agent Side (Python - barnhaus-design-agent)
1. **New CLI Command:** Add `python3 run.py changes` to fetch and display the recent changes.
2. **Integration:** Use this command to provide real-time workflow context when analyzing journals. Store the correlation data in `training_data/WORKFLOWS.md` during sessions.
