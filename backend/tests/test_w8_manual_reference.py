"""W8: a manually added swipe reference has no Ad Library start date, so its
run length stays unknown (never an invented "1 day") and no CTA is made up."""
import inspect

from app.services import creative_service


def test_manual_reference_does_not_invent_run_length_or_cta():
    source = inspect.getsource(creative_service.create_custom_swipe_reference)
    assert "days_active=None" in source
    assert "days_active=1" not in source
    assert 'cta=(data.get("cta") or None)' in source
