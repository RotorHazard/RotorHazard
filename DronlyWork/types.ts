// Generated from DronlyWork/asyncapi.yaml
// Do not edit by hand. Run `npm run generate:types` after changing api_schema.py.

export type NoSpec = unknown;

export interface LeaderboardEvent {
  [key: string]: unknown;
  current: Record<string, unknown>;
  last_race?: Record<string, unknown> | null;
}

export interface CurrentLapsEvent {
  [key: string]: unknown;
  current: Record<string, unknown>;
  last_race?: Record<string, unknown> | null;
}

export interface RaceStatusEvent {
  [key: string]: unknown;
  race_status: number;
  race_format_id?: number | null;
  race_heat_id?: number | null;
  race_class_id?: number | null;
  unlimited_time: boolean | number;
  race_time_sec?: number | null;
  staging_tones: number;
  hide_stage_timer: boolean;
  pi_starts_at_s?: number | null;
  pi_staging_at_s?: number | null;
  show_init_time_flag: boolean;
  next_round?: number | null;
}

export interface CurrentHeatEvent {
  [key: string]: unknown;
  current_heat: number | null;
  heatNodes: Record<string, unknown>;
  heat_format?: number | null;
  heat_class?: number | null;
  coop_best_time?: string | null;
  coop_num_laps?: number | null;
  next_round?: number | null;
}

export interface PilotDataEvent {
  [key: string]: unknown;
  pilots: Record<string, unknown>[];
  pilotSort?: string | null;
  attributes?: Record<string, unknown>[] | null;
}

export interface HeatDataEvent {
  [key: string]: unknown;
  heats: Record<string, unknown>[];
  attributes?: Record<string, unknown>[] | null;
}

export interface RaceListEvent {
  [key: string]: unknown;
  heats: Record<string, unknown>;
}

export interface RaceScheduledEvent {
  [key: string]: unknown;
  scheduled: boolean;
  scheduled_at?: number | null;
}

export interface PhoneticDataEvent {
  [key: string]: unknown;
  lap: number;
  raw_time?: number | null;
  phonetic?: string | null;
  team_phonetic?: string | null;
  team_short_phonetic?: string | null;
  leader_flag: boolean;
  node_finished: boolean;
  pilot?: string | null;
  callsign?: string | null;
  pilot_id?: number | null;
}

export interface PhoneticLeaderEvent {
  [key: string]: unknown;
  pilot?: string | null;
  callsign?: string | null;
  pilot_id?: number | null;
}

export interface PhoneticTextEvent {
  [key: string]: unknown;
  text: string;
  domain?: string | boolean;
  winner_flag?: boolean;
}

export interface PhoneticSplitCallEvent {
  [key: string]: unknown;
  pilot_name: string;
  split_id: string;
  split_time?: string | null;
  split_speed?: string | null;
}

export type CalloutsEvent = string[];

export interface FirstPassRegisteredEvent {
  [key: string]: unknown;
  node_index: number;
}

export interface LoadDataRequestDictLoadType {
  [key: string]: unknown;
  type: "ui" | "config" | string;
  value?: unknown;
}

export interface LoadDataRequest {
  load_types: ("node_data" | "environmental_data" | "frequency_data" | "heat_list" | "heat_data" | "heat_attribute_types" | "seat_data" | "class_list" | "class_data" | "format_data" | "pilot_list" | "pilot_data" | "result_data" | "node_tuning" | "enter_and_exit_at_levels" | "start_thresh_lower_amount" | "start_thresh_lower_duration" | "min_lap" | "action_setup" | "event_actions" | "leaderboard" | "current_laps" | "race_status" | "current_heat" | "race_list" | "language" | "all_languages" | "led_effect_setup" | "led_effects" | "callouts" | "imdtabler_page" | "vrx_list" | "backups_list" | "upd_cfg_files_list" | "exporter_list" | "importer_list" | "heatgenerator_list" | "raceclass_rank_method_list" | "race_points_method_list" | "plugin_list" | "plugin_repo" | "cluster_status" | "hardware_log_init" | string | LoadDataRequestDictLoadType)[];
}

export interface HeatRequest {
  heat: number;
}

export interface AlterRaceRequest {
  race_id: number;
  heat_id: number;
}

export interface ServerTimeResponse {
  server_time_s: number;
}

export interface ScheduleRaceRequest {
  m: number;
  s: number;
}

export interface ResaveLapsRequestResaveLapRequest {
  [key: string]: unknown;
  lap_time_stamp: number;
  lap_time: number | string;
  source: number;
  deleted: boolean;
  peak_rssi?: number | null;
}

export interface ResaveLapsRequest {
  heat_id: number;
  round_id: number;
  callsign: string;
  race_id: number;
  pilotrace_id: number;
  seat: number;
  pilot_id: number;
  laps: ResaveLapsRequestResaveLapRequest[];
  enter_at: number;
  exit_at: number;
}

export interface ReplaceCurrentLapsRequestResaveLapRequest {
  [key: string]: unknown;
  lap_time_stamp: number;
  lap_time: number | string;
  source: number;
  deleted: boolean;
  peak_rssi?: number | null;
}

export interface ReplaceCurrentLapsRequest {
  heat_id: number;
  round_id: number;
  callsign: string;
  race_id: number;
  pilotrace_id: number;
  seat: number;
  pilot_id: number;
  laps: ReplaceCurrentLapsRequestResaveLapRequest[];
  enter_at: number;
  exit_at: number;
}

export interface CalcPilotsRequest {
  heat: number;
  preassignments?: Record<string, number>;
}

export interface CalcResetRequest {
  heat: number;
}

export interface SetCurrentHeatRequest {
  heat: number | null;
}

export interface GetPilotRaceRequest {
  pilotrace_id: number;
}

export type SocketEventName = "connect" | "disconnect" | "join_cluster" | "join_cluster_ex" | "check_secondary_query" | "cluster_event_trigger" | "cluster_message_ack" | "dispatch_event" | "load_data" | "broadcast_message" | "set_frequency" | "set_frequency_preset" | "set_enter_at_level" | "set_exit_at_level" | "set_start_thresh_lower_amount" | "set_start_thresh_lower_duration" | "set_language" | "cap_enter_at_btn" | "cap_exit_at_btn" | "set_scan" | "expand_heat" | "get_class_recents" | "add_heat" | "duplicate_heat" | "deactivate_heat" | "activate_heat" | "alter_heat" | "delete_heat" | "add_race_class" | "duplicate_race_class" | "alter_race_class" | "delete_class" | "add_pilot" | "alter_pilot" | "delete_pilot" | "set_seat_color" | "reset_seat_color" | "add_profile" | "alter_profile" | "delete_profile" | "set_profile" | "alter_race" | "backup_database" | "download_database" | "list_backups" | "restore_database" | "delete_database" | "reset_database" | "export_database" | "import_data" | "generate_heats_v2" | "shutdown_pi" | "reboot_pi" | "restart_server" | "kill_server" | "set_log_level" | "download_logs" | "backup_settings" | "download_settings" | "reset_settings_to_defaults" | "restore_cfg_file" | "rename_cfg_file" | "delete_cfg_file" | "load_cfg_file" | "set_min_lap" | "set_min_first_crossing" | "set_min_lap_behavior" | "set_race_format" | "add_race_format" | "alter_race_format" | "delete_race_format" | "set_led_event_effect" | "use_led_effect" | "get_pi_time" | "get_server_time" | "schedule_race" | "cancel_schedule_race" | "stage_race" | "stop_race" | "current_race_marshal" | "save_laps" | "resave_laps" | "replace_current_laps" | "discard_laps" | "calc_pilots" | "calc_reset" | "confirm_heat_plan" | "set_current_heat" | "delete_lap" | "restore_deleted_lap" | "simulate_lap" | "LED_solid" | "LED_brightness" | "set_option" | "set_config" | "set_config_section" | "set_ui_binding_value" | "set_consecutives_count" | "get_race_scheduled" | "save_callouts" | "reload_callouts" | "play_callout_text" | "imdtabler_update_freqs" | "clean_cache" | "retry_secondary" | "get_pilotrace" | "check_bpillfw_file" | "do_bpillfw_update" | "set_vrx_node" | "plugin_install" | "plugin_delete" | "datadir_handler";

export interface SocketEvents {
  connect: undefined;
  disconnect: undefined;
  join_cluster: undefined;
  join_cluster_ex: undefined;
  check_secondary_query: undefined;
  cluster_event_trigger: undefined;
  cluster_message_ack: undefined;
  dispatch_event: undefined;
  load_data: LoadDataRequest;
  broadcast_message: undefined;
  set_frequency: undefined;
  set_frequency_preset: undefined;
  set_enter_at_level: undefined;
  set_exit_at_level: undefined;
  set_start_thresh_lower_amount: undefined;
  set_start_thresh_lower_duration: undefined;
  set_language: undefined;
  cap_enter_at_btn: undefined;
  cap_exit_at_btn: undefined;
  set_scan: undefined;
  expand_heat: undefined;
  get_class_recents: undefined;
  add_heat: undefined;
  duplicate_heat: undefined;
  deactivate_heat: HeatRequest;
  activate_heat: HeatRequest;
  alter_heat: undefined;
  delete_heat: undefined;
  add_race_class: undefined;
  duplicate_race_class: undefined;
  alter_race_class: undefined;
  delete_class: undefined;
  add_pilot: undefined;
  alter_pilot: undefined;
  delete_pilot: undefined;
  set_seat_color: undefined;
  reset_seat_color: undefined;
  add_profile: undefined;
  alter_profile: undefined;
  delete_profile: undefined;
  set_profile: undefined;
  alter_race: AlterRaceRequest;
  backup_database: undefined;
  download_database: undefined;
  list_backups: undefined;
  restore_database: undefined;
  delete_database: undefined;
  reset_database: undefined;
  export_database: undefined;
  import_data: undefined;
  generate_heats_v2: undefined;
  shutdown_pi: undefined;
  reboot_pi: undefined;
  restart_server: undefined;
  kill_server: undefined;
  set_log_level: undefined;
  download_logs: undefined;
  backup_settings: undefined;
  download_settings: undefined;
  reset_settings_to_defaults: undefined;
  restore_cfg_file: undefined;
  rename_cfg_file: undefined;
  delete_cfg_file: undefined;
  load_cfg_file: undefined;
  set_min_lap: undefined;
  set_min_first_crossing: undefined;
  set_min_lap_behavior: undefined;
  set_race_format: undefined;
  add_race_format: undefined;
  alter_race_format: undefined;
  delete_race_format: undefined;
  set_led_event_effect: undefined;
  use_led_effect: undefined;
  get_pi_time: undefined;
  get_server_time: undefined;
  schedule_race: ScheduleRaceRequest;
  cancel_schedule_race: undefined;
  stage_race: undefined;
  stop_race: undefined;
  current_race_marshal: undefined;
  save_laps: undefined;
  resave_laps: ResaveLapsRequest;
  replace_current_laps: ReplaceCurrentLapsRequest;
  discard_laps: undefined;
  calc_pilots: CalcPilotsRequest;
  calc_reset: CalcResetRequest;
  confirm_heat_plan: undefined;
  set_current_heat: SetCurrentHeatRequest;
  delete_lap: undefined;
  restore_deleted_lap: undefined;
  simulate_lap: undefined;
  LED_solid: undefined;
  LED_brightness: undefined;
  set_option: undefined;
  set_config: undefined;
  set_config_section: undefined;
  set_ui_binding_value: undefined;
  set_consecutives_count: undefined;
  get_race_scheduled: undefined;
  save_callouts: undefined;
  reload_callouts: undefined;
  play_callout_text: undefined;
  imdtabler_update_freqs: undefined;
  clean_cache: undefined;
  retry_secondary: undefined;
  get_pilotrace: GetPilotRaceRequest;
  check_bpillfw_file: undefined;
  do_bpillfw_update: undefined;
  set_vrx_node: undefined;
  plugin_install: undefined;
  plugin_delete: undefined;
  datadir_handler: undefined;
}

export interface SocketEventAcks {
  connect: undefined;
  disconnect: undefined;
  join_cluster: undefined;
  join_cluster_ex: undefined;
  check_secondary_query: undefined;
  cluster_event_trigger: undefined;
  cluster_message_ack: undefined;
  dispatch_event: undefined;
  load_data: undefined;
  broadcast_message: undefined;
  set_frequency: undefined;
  set_frequency_preset: undefined;
  set_enter_at_level: undefined;
  set_exit_at_level: undefined;
  set_start_thresh_lower_amount: undefined;
  set_start_thresh_lower_duration: undefined;
  set_language: undefined;
  cap_enter_at_btn: undefined;
  cap_exit_at_btn: undefined;
  set_scan: undefined;
  expand_heat: undefined;
  get_class_recents: undefined;
  add_heat: undefined;
  duplicate_heat: undefined;
  deactivate_heat: undefined;
  activate_heat: undefined;
  alter_heat: undefined;
  delete_heat: undefined;
  add_race_class: undefined;
  duplicate_race_class: undefined;
  alter_race_class: undefined;
  delete_class: undefined;
  add_pilot: undefined;
  alter_pilot: undefined;
  delete_pilot: undefined;
  set_seat_color: undefined;
  reset_seat_color: undefined;
  add_profile: undefined;
  alter_profile: undefined;
  delete_profile: undefined;
  set_profile: undefined;
  alter_race: undefined;
  backup_database: undefined;
  download_database: undefined;
  list_backups: undefined;
  restore_database: undefined;
  delete_database: undefined;
  reset_database: undefined;
  export_database: undefined;
  import_data: undefined;
  generate_heats_v2: undefined;
  shutdown_pi: undefined;
  reboot_pi: undefined;
  restart_server: undefined;
  kill_server: undefined;
  set_log_level: undefined;
  download_logs: undefined;
  backup_settings: undefined;
  download_settings: undefined;
  reset_settings_to_defaults: undefined;
  restore_cfg_file: undefined;
  rename_cfg_file: undefined;
  delete_cfg_file: undefined;
  load_cfg_file: undefined;
  set_min_lap: undefined;
  set_min_first_crossing: undefined;
  set_min_lap_behavior: undefined;
  set_race_format: undefined;
  add_race_format: undefined;
  alter_race_format: undefined;
  delete_race_format: undefined;
  set_led_event_effect: undefined;
  use_led_effect: undefined;
  get_pi_time: undefined;
  get_server_time: ServerTimeResponse;
  schedule_race: undefined;
  cancel_schedule_race: undefined;
  stage_race: undefined;
  stop_race: undefined;
  current_race_marshal: undefined;
  save_laps: undefined;
  resave_laps: undefined;
  replace_current_laps: undefined;
  discard_laps: undefined;
  calc_pilots: undefined;
  calc_reset: undefined;
  confirm_heat_plan: undefined;
  set_current_heat: undefined;
  delete_lap: undefined;
  restore_deleted_lap: undefined;
  simulate_lap: undefined;
  LED_solid: undefined;
  LED_brightness: undefined;
  set_option: undefined;
  set_config: undefined;
  set_config_section: undefined;
  set_ui_binding_value: undefined;
  set_consecutives_count: undefined;
  get_race_scheduled: undefined;
  save_callouts: undefined;
  reload_callouts: undefined;
  play_callout_text: undefined;
  imdtabler_update_freqs: undefined;
  clean_cache: undefined;
  retry_secondary: undefined;
  get_pilotrace: undefined;
  check_bpillfw_file: undefined;
  do_bpillfw_update: undefined;
  set_vrx_node: undefined;
  plugin_install: undefined;
  plugin_delete: undefined;
  datadir_handler: undefined;
}

export type SocketServerEventName = "leaderboard" | "current_laps" | "race_status" | "current_heat" | "pilot_data" | "heat_data" | "race_list" | "race_scheduled" | "phonetic_data" | "phonetic_leader" | "phonetic_text" | "phonetic_split_call" | "callouts" | "first_pass_registered";

export interface SocketServerEvents {
  leaderboard: LeaderboardEvent;
  current_laps: CurrentLapsEvent;
  race_status: RaceStatusEvent;
  current_heat: CurrentHeatEvent;
  pilot_data: PilotDataEvent;
  heat_data: HeatDataEvent;
  race_list: RaceListEvent;
  race_scheduled: RaceScheduledEvent;
  phonetic_data: PhoneticDataEvent;
  phonetic_leader: PhoneticLeaderEvent;
  phonetic_text: PhoneticTextEvent;
  phonetic_split_call: PhoneticSplitCallEvent;
  callouts: CalloutsEvent;
  first_pass_registered: FirstPassRegisteredEvent;
}

export type SocketPayload<T extends SocketEventName> = SocketEvents[T];
export type SocketAck<T extends SocketEventName> = SocketEventAcks[T];
export type SocketServerPayload<T extends SocketServerEventName> = SocketServerEvents[T];
