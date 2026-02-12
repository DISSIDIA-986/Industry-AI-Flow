from __future__ import annotations

from backend.services.demo_mode_service import (
    DEMO_MODE_LIVE_HYBRID,
    DEMO_MODE_LOCAL_SAFE,
    DEMO_MODE_SCRIPTED_REPLAY,
    get_demo_mode_service,
)


def test_demo_mode_resolve_route_mode_profiles():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)

    assert service.resolve_route_mode(None) == "hybrid_auto"
    assert service.resolve_route_mode("cloud_only") == "cloud_only"

    service.set_mode(DEMO_MODE_LOCAL_SAFE)
    assert service.resolve_route_mode(None) == "local_only"
    assert service.resolve_route_mode("cloud_only") == "local_only"


def test_scripted_replay_returns_scenario_and_fallback():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_SCRIPTED_REPLAY, allow_cloud_override=False)

    matched = service.replay_response("please run cost estimate for this project")
    assert matched is not None
    assert matched["id"] == "cost_estimation_showcase"

    fallback = service.replay_response("totally unmatched query")
    assert fallback is not None
    assert fallback["id"] == "generic_fallback"


def test_cloud_override_can_enable_cloud_in_local_safe():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LOCAL_SAFE, allow_cloud_override=False)

    assert service.cloud_calls_allowed() is False

    service.set_cloud_override(True)
    assert service.cloud_calls_allowed() is True

    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)
