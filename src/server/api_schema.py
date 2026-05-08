from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

KnownLoadType: TypeAlias = Literal[
    "node_data",
    "environmental_data",
    "frequency_data",
    "heat_list",
    "heat_data",
    "heat_attribute_types",
    "seat_data",
    "class_list",
    "class_data",
    "format_data",
    "pilot_list",
    "pilot_data",
    "result_data",
    "node_tuning",
    "enter_and_exit_at_levels",
    "start_thresh_lower_amount",
    "start_thresh_lower_duration",
    "min_lap",
    "action_setup",
    "event_actions",
    "leaderboard",
    "current_laps",
    "race_status",
    "current_heat",
    "race_list",
    "language",
    "all_languages",
    "led_effect_setup",
    "led_effects",
    "callouts",
    "imdtabler_page",
    "vrx_list",
    "backups_list",
    "upd_cfg_files_list",
    "exporter_list",
    "importer_list",
    "heatgenerator_list",
    "raceclass_rank_method_list",
    "race_points_method_list",
    "plugin_list",
    "plugin_repo",
    "cluster_status",
    "hardware_log_init",
]

class DictLoadType(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["ui", "config"] | str = Field(
        ...,
        description="Structured load request type. Known values: 'ui' and 'config'.",
        examples=["config"],
    )
    value: Any = Field(
        None,
        description="Payload passed to the corresponding RaceContext.rhui emitter.",
        examples=[{"GENERAL": ["SECONDARIES"]}],
    )


LoadDataItem: TypeAlias = KnownLoadType | str | DictLoadType

class LoadDataRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"load_types": ["frequency_data", "heat_data", "pilot_data"]},
                {
                    "load_types": [
                        {
                            "type": "config",
                            "value": {"GENERAL": ["SECONDARIES"]},
                        }
                    ]
                },
            ]
        },
    )

    load_types: list[LoadDataItem] = Field(
        ...,
        description=(
            "Data blocks requested by the UI. Items may be known string load types "
            "or structured requests for targeted UI/config updates."
        ),
        min_length=1,
    )

class HeatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"heat": 3}]},
    )

    heat: int = Field(..., description="Heat ID to activate or deactivate.")


class SetCurrentHeatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"heat": 3}, {"heat": None}]},
    )

    heat: int | None = Field(
        ...,
        description="Heat ID to set as current. Null selects practice mode.",
    )


class AlterRaceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"race_id": 12, "heat_id": 3}]},
    )

    race_id: int = Field(..., description="Saved race ID to reassign.")
    heat_id: int = Field(..., description="Destination heat ID.")


class ServerTimeResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"server_time_s": 12345.678}]},
    )

    server_time_s: float = Field(..., description="Server monotonic time in seconds.")


class ScheduleRaceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"m": 1, "s": 30}]},
    )

    m: int = Field(..., description="Minutes until race start.")
    s: int = Field(..., description="Seconds until race start.")


class ResaveLapRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    lap_time_stamp: float = Field(..., description="Lap timestamp in milliseconds from race start.")
    lap_time: float | str = Field(..., description="Incremental lap time in milliseconds, or legacy formatted value.")
    source: int = Field(..., description="Lap source identifier.")
    deleted: bool = Field(..., description="Whether this lap is marked deleted.")
    peak_rssi: int | None = Field(None, description="Peak RSSI recorded for this lap.")


class ResaveLapsRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "heat_id": 3,
                    "round_id": 1,
                    "callsign": "Pilot 1",
                    "race_id": 42,
                    "pilotrace_id": 7,
                    "seat": 0,
                    "pilot_id": 12,
                    "laps": [
                        {
                            "lap_time_stamp": 12500,
                            "lap_time": 12500,
                            "source": 2,
                            "deleted": False,
                            "peak_rssi": 218,
                        }
                    ],
                    "enter_at": 210,
                    "exit_at": 190,
                }
            ]
        },
    )

    heat_id: int = Field(..., description="Heat ID for the saved race.")
    round_id: int = Field(..., description="Round number for display/logging.")
    callsign: str = Field(..., description="Pilot callsign for display/logging.")
    race_id: int = Field(..., description="Saved race ID.")
    pilotrace_id: int = Field(..., description="Saved pilot-race row ID.")
    seat: int = Field(..., description="Node/seat index.")
    pilot_id: int = Field(..., description="Pilot ID assigned to this seat.")
    laps: list[ResaveLapRequest] = Field(..., description="Replacement lap list.")
    enter_at: int = Field(..., description="Enter-at threshold used for this pilot race.")
    exit_at: int = Field(..., description="Exit-at threshold used for this pilot race.")


class ReplaceCurrentLapsRequest(ResaveLapsRequest):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "heat_id": 3,
                    "round_id": 1,
                    "callsign": "Pilot 1",
                    "race_id": 42,
                    "pilotrace_id": 7,
                    "seat": 0,
                    "pilot_id": 12,
                    "laps": [
                        {
                            "lap_time_stamp": 12500,
                            "lap_time": 12500,
                            "source": 2,
                            "deleted": False,
                            "peak_rssi": 218,
                        }
                    ],
                    "enter_at": 210,
                    "exit_at": 190,
                }
            ]
        },
    )


class CalcPilotsRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"heat": 3}, {"heat": 3, "preassignments": {"1": 0}}]},
    )

    heat: int = Field(..., description="Heat ID to calculate pilot assignments for.")
    preassignments: dict[int, int] = Field(
        default_factory=dict,
        description="Optional heat-slot to seat preassignments.",
    )


class CalcResetRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"heat": 3}]},
    )

    heat: int = Field(..., description="Heat ID whose generated plan should be reset.")


class GetPilotRaceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"pilotrace_id": 7}]},
    )

    pilotrace_id: int = Field(..., description="Saved pilot-race row ID to load.")


__all__ = [
    "AlterRaceRequest",
    "CalcPilotsRequest",
    "CalcResetRequest",
    "DictLoadType",
    "GetPilotRaceRequest",
    "HeatRequest",
    "KnownLoadType",
    "LoadDataItem",
    "LoadDataRequest",
    "ReplaceCurrentLapsRequest",
    "ResaveLapRequest",
    "ResaveLapsRequest",
    "ScheduleRaceRequest",
    "ServerTimeResponse",
    "SetCurrentHeatRequest",
]
