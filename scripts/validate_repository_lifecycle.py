"""Validate repository lifecycle evidence independently of producer code."""

# Standard Library
import datetime
import zoneinfo


#============================================
def validate_activity_lifecycle(
	activity: dict,
	mirror: dict,
	report_date: str,
	timezone_name: str,
) -> None:
	"""Require one creation event whose report-day state matches its exact timestamp."""
	if activity["is_fork"] is not mirror["is_fork"]:
		raise RuntimeError("Evidence activity fork state does not match its mirror.")
	lifecycle_events = activity.get("lifecycle_events")
	if not isinstance(lifecycle_events, list) or len(lifecycle_events) != 1:
		raise RuntimeError("Evidence activity requires one repository lifecycle event.")
	lifecycle = lifecycle_events[0]
	required = {"event_type", "occurred_at", "occurred_in_report_window", "source"}
	if not isinstance(lifecycle, dict) or set(lifecycle) != required:
		raise RuntimeError("Evidence repository lifecycle event fields are unsupported.")
	if (
		lifecycle["event_type"] != "repository_created"
		or lifecycle["source"] != "github_owner_roster"
		or lifecycle["occurred_at"] != mirror["created_at"]
		or type(lifecycle["occurred_in_report_window"]) is not bool
	):
		raise RuntimeError("Evidence repository lifecycle event is inconsistent.")
	start = datetime.datetime.combine(
		datetime.date.fromisoformat(report_date),
		datetime.time.min,
		tzinfo=zoneinfo.ZoneInfo(timezone_name),
	)
	occurred = datetime.datetime.fromisoformat(
		lifecycle["occurred_at"].replace("Z", "+00:00")
	).astimezone(start.tzinfo)
	if lifecycle["occurred_in_report_window"] != (
		start <= occurred < start + datetime.timedelta(days=1)
	):
		raise RuntimeError("Evidence repository lifecycle report-window state is inconsistent.")
