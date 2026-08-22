"""Sensor platform for Renovasjonsportal integration."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ADDRESS,
    ATTR_DAYS_UNTIL,
    ATTR_FRACTION,
    ATTR_MUNICIPALITY,
    ATTR_NEXT_DATE,
    ATTR_UPCOMING_DATES,
    DOMAIN,
    WASTE_FRACTIONS,
)
from .coordinator import RenovasjonCoordinator, RenovasjonData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Renovasjon sensors based on a config entry."""
    coordinator: RenovasjonCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for first data fetch
    await coordinator.async_config_entry_first_refresh()

    # Create sensors for each fraction found in the data
    entities: list[SensorEntity] = []

    if coordinator.data:
        for fraction in coordinator.data.fractions:
            entities.append(
                RenovasjonSensor(
                    coordinator=coordinator,
                    fraction=fraction,
                )
            )
            entities.append(
                RenovasjonDaysUntilSensor(
                    coordinator=coordinator,
                    fraction=fraction,
                )
            )

    async_add_entities(entities)


class RenovasjonSensor(CoordinatorEntity[RenovasjonCoordinator], SensorEntity):
    """Sensor for a waste fraction."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: RenovasjonCoordinator,
        fraction: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._fraction = fraction

        # Get fraction config if available
        fraction_config = WASTE_FRACTIONS.get(fraction, {})

        # Entity attributes
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{fraction}"
        self._attr_translation_key = fraction_config.get(
            "translation_key", fraction.lower().replace(" ", "_")
        )
        self._attr_icon = fraction_config.get("icon", "mdi:trash-can-outline")

        # Use fraction name as fallback
        self._attr_name = fraction

        # Device info - group all sensors under one device per address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Renovasjon {coordinator.data.address_name}",
            manufacturer="Renovasjonsportal",
            model=coordinator.data.municipality,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        if self.coordinator.data is None:
            return None

        next_disposal = self.coordinator.data.get_next_disposal(self._fraction)
        if next_disposal is None:
            return None

        return next_disposal.date.date()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            ATTR_FRACTION: self._fraction,
        }

        if self.coordinator.data is None:
            return attrs

        data: RenovasjonData = self.coordinator.data

        # Add address info
        attrs[ATTR_ADDRESS] = data.address_name
        attrs[ATTR_MUNICIPALITY] = data.municipality

        # Days until next collection
        days_until = data.get_days_until(self._fraction)
        if days_until is not None:
            attrs[ATTR_DAYS_UNTIL] = days_until

        # Next date as ISO string
        next_disposal = data.get_next_disposal(self._fraction)
        if next_disposal:
            attrs[ATTR_NEXT_DATE] = next_disposal.date.isoformat()

        # Upcoming dates
        upcoming = data.get_upcoming_disposals(self._fraction, limit=5)
        if upcoming:
            attrs[ATTR_UPCOMING_DATES] = [d.date.date().isoformat() for d in upcoming]

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class RenovasjonDaysUntilSensor(CoordinatorEntity[RenovasjonCoordinator], SensorEntity):
    """Sensor showing the number of days until collection."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        coordinator: RenovasjonCoordinator,
        fraction: str,
    ) -> None:
        """Initialize the days-until sensor."""
        super().__init__(coordinator)

        self._fraction = fraction
        fraction_config = WASTE_FRACTIONS.get(fraction, {})
        translation_key = fraction_config.get(
            "translation_key", fraction.lower().replace(" ", "_")
        )

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{fraction}_days_until"
        self._attr_translation_key = f"{translation_key}_days_until"
        self._attr_icon = fraction_config.get("icon", "mdi:trash-can-outline")
        self._attr_name = f"{fraction} days until collection"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Renovasjon {coordinator.data.address_name}",
            manufacturer="Renovasjonsportal",
            model=coordinator.data.municipality,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of days until the next collection."""
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get_days_until(self._fraction)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes useful for configuring a tile card."""
        days_until = self.native_value
        if days_until is None:
            return {ATTR_FRACTION: self._fraction}

        tile_color = "red" if days_until <= 1 else "yellow" if days_until <= 3 else ""
        return {
            ATTR_FRACTION: self._fraction,
            "tile_color": tile_color,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
