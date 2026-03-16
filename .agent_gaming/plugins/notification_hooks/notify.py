"""
Minimal notification hook for the gaming tracker.
"""


def send_notification(event: dict) -> None:
    """Placeholder notification sink used by workflow prototypes."""
    print(f"[notify] {event.get('event_type', 'update')}: {event.get('title', event.get('summary', ''))}")


if __name__ == "__main__":
    send_notification({"event_type": "test", "summary": "gaming notification hook ready"})
