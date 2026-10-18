"""Shared service-combination rules for pool assignment and final validation."""


def is_compatible_service(candidate, active_services, config):
    """Return whether candidate can be added to the current active service values."""
    if candidate in active_services:
        return False

    for group in config.get("exclusive_service_groups", []):
        group_services = set(group["services"])
        selected_from_group = sum(service in group_services for service in active_services)
        if candidate in group_services and selected_from_group >= group["max_selected"]:
            return False

    incompatible_pairs = {
        frozenset(pair) for pair in config.get("incompatible_service_pairs", [])
    }
    return all(
        frozenset((candidate, selected)) not in incompatible_pairs
        for selected in active_services
    )


def validate_active_services(active_services, config):
    """Raise ValueError when a final active-service set breaks a pool rule."""
    services = list(active_services.values())
    if len(services) != len(set(services)):
        raise ValueError("duplicate active service")

    for group in config.get("exclusive_service_groups", []):
        group_services = set(group["services"])
        selected = [service for service in services if service in group_services]
        if len(selected) > group["max_selected"]:
            raise ValueError(
                f"exclusive service group {group['name']} exceeded: {', '.join(selected)}"
            )

    selected_services = set(services)
    for pair in config.get("incompatible_service_pairs", []):
        if set(pair).issubset(selected_services):
            raise ValueError(f"incompatible service pair: {' + '.join(pair)}")
