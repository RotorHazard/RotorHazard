from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, RootModel

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


class CurrentLapsEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    current: dict[str, Any] = Field(..., description="Lap data for the current race.")
    last_race: dict[str, Any] | None = Field(None, description="Lap data for the previous race, when available.")


class LeaderboardEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    current: dict[str, Any] = Field(..., description="Leaderboard block for the current race.")
    last_race: dict[str, Any] | None = Field(None, description="Leaderboard block for the previous race, when available.")


class RaceStatusEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    race_status: int = Field(..., description="Current race state enum value.")
    race_format_id: int | None = Field(None, description="Active race format ID.")
    race_heat_id: int | None = Field(None, description="Active heat ID, or null in practice mode.")
    race_class_id: int | None = Field(None, description="Active class ID, or null in practice mode.")
    unlimited_time: bool | int = Field(..., description="Whether this race runs with unlimited time, often emitted as 0/1.")
    race_time_sec: int | float | None = Field(None, description="Configured race duration in seconds.")
    staging_tones: int = Field(..., description="Staging tone count/state.")
    hide_stage_timer: bool = Field(..., description="Whether the stage timer should be hidden.")
    pi_starts_at_s: int | float | None = Field(None, description="Monotonic timestamp when the race starts.")
    pi_staging_at_s: int | float | None = Field(None, description="Monotonic timestamp when staging starts.")
    show_init_time_flag: bool = Field(..., description="Whether initial time should be displayed.")
    next_round: int | None = Field(None, description="Next round number for the current heat.")


class CurrentHeatEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    current_heat: int | None = Field(..., description="Active heat ID, or null/none-like value for practice.")
    heatNodes: dict[int | str, Any] = Field(..., description="Node assignment and display data keyed by node index.")
    heat_format: int | None = Field(None, description="Race format ID inherited from the heat class.")
    heat_class: int | None = Field(None, description="Race class ID for the active heat.")
    coop_best_time: str | None = Field(None, description="Formatted coop best time, when applicable.")
    coop_num_laps: int | None = Field(None, description="Configured coop lap count, when applicable.")
    next_round: int | None = Field(None, description="Next round number for this heat.")


class PilotDataEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    pilots: list[dict[str, Any]] = Field(..., description="Known pilots and plugin-provided pilot fields.")
    pilotSort: str | None = Field(None, description="Configured UI pilot sort mode.")
    attributes: list[dict[str, Any]] | None = Field(None, description="Pilot attribute metadata, when requested.")


class HeatDataEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    heats: list[dict[str, Any]] = Field(..., description="Configured heats and their node slots.")
    attributes: list[dict[str, Any]] | None = Field(None, description="Heat attribute metadata.")


class RaceListEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    heats: dict[int | str, Any] = Field(..., description="Saved race history grouped by heat ID.")


class RaceScheduledEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    scheduled: bool = Field(..., description="Whether a scheduled race start is pending.")
    scheduled_at: int | float | None = Field(None, description="Monotonic timestamp for the scheduled start.")


class PhoneticDataEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    lap: int = Field(..., description="Lap number being announced.")
    raw_time: int | float | None = Field(None, description="Raw lap time.")
    phonetic: str | None = Field(None, description="Human-readable lap time callout text.")
    team_phonetic: str | None = Field(None, description="Team callout text, when team racing.")
    team_short_phonetic: str | None = Field(None, description="Short team callout text, when available.")
    leader_flag: bool = Field(..., description="Whether this lap made the pilot the leader.")
    node_finished: bool = Field(..., description="Whether the node/pilot has finished.")
    pilot: str | None = Field(None, description="Phonetic pilot name or fallback frequency label.")
    callsign: str | None = Field(None, description="Pilot callsign or fallback frequency label.")
    pilot_id: int | None = Field(None, description="Pilot ID, or null for unassigned nodes.")


class PhoneticLeaderEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    pilot: str | None = Field(None, description="Phonetic name of the current leader.")
    callsign: str | None = Field(None, description="Callsign of the current leader.")
    pilot_id: int | None = Field(None, description="Pilot ID of the current leader.")


class PhoneticTextEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str = Field(..., description="Text to announce.")
    domain: str | bool = Field(False, description="Announcement domain/category, or false for generic text.")
    winner_flag: bool = Field(False, description="Whether this text announces a winner.")


class PhoneticSplitCallEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    pilot_name: str = Field(..., description="Pilot phonetic name for the split callout.")
    split_id: str = Field(..., description="One-based split identifier as displayed to users.")
    split_time: str | None = Field(None, description="Formatted split time callout.")
    split_speed: str | None = Field(None, description="Formatted split speed callout.")


class CalloutsEvent(RootModel[list[str]]):
    root: list[str] = Field(..., description="Saved voice callout text snippets.")


class FirstPassRegisteredEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_index: int = Field(..., description="Node index that registered the first pass.")


__all__ = [
    "AlterRaceRequest",
    "CalcPilotsRequest",
    "CalcResetRequest",
    "CalloutsEvent",
    "CurrentHeatEvent",
    "CurrentLapsEvent",
    "DictLoadType",
    "FirstPassRegisteredEvent",
    "GetPilotRaceRequest",
    "HeatRequest",
    "HeatDataEvent",
    "KnownLoadType",
    "LeaderboardEvent",
    "LoadDataItem",
    "LoadDataRequest",
    "PhoneticDataEvent",
    "PhoneticLeaderEvent",
    "PhoneticSplitCallEvent",
    "PhoneticTextEvent",
    "PilotDataEvent",
    "RaceListEvent",
    "RaceScheduledEvent",
    "RaceStatusEvent",
    "ReplaceCurrentLapsRequest",
    "ResaveLapRequest",
    "ResaveLapsRequest",
    "ScheduleRaceRequest",
    "ServerTimeResponse",
    "SetCurrentHeatRequest",
]
