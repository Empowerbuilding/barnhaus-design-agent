# HEARTBEAT.md - Juanito's Proactive Checks

## Every Heartbeat

### New Design Submissions (check every heartbeat)
- Query design_intake_submissions ordered by created_at desc
- Look for submissions created in the last 35 minutes
- For each new one:
  1. Post alert in Discord: "🏠 New design request: [name] — [house_shape], [sq_ft] SF, [bedrooms] bed — ready to run design brain?"
  2. Wait for Mitch to say "go" before running the brain

### Pending Approvals (check every heartbeat)
- Check for submissions where floor_plan_image_urls is set but no approval noted in memory
- Remind Mitch if a floor plan has been waiting for review for more than 2 hours

## Rules
- Don't message between 11pm - 8am CST unless urgent
- Don't run the design brain without Mitch explicitly saying to
- Keep messages short
- Always post floor plan images directly in Discord as attachments
