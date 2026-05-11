# RotorHazard Race Simulation Scripts

These scripts drive RotorHazard through the same Socket.IO events that the UI uses. They create a small simulated race setup, start a race, send manual lap events, and optionally save the result.

## What It Simulates

- A RotorHazard event setup with a race class, heat, and pilots.
- A current heat assigned to mock timing nodes.
- Race staging/start via `stage_race`.
- Lap passes via `simulate_lap`.
- Live streams such as `leaderboard`, `current_laps`, `race_status`, `phonetic_data`, `phonetic_leader`, and `first_pass_registered`.
- Stop/save via `stop_race` and `save_laps`.

RotorHazard does not have a separate top-level "event" socket object; the event is the active DB/config state: classes, pilots, heats, races, and results.

## Prerequisites

From the repo root:

```sh
python -m venv venv
source venv/bin/activate
pip install -r src/server/requirements.txt
cd DronlyWork
npm install
```

## Recommended Run

One terminal, start a temporary mock server, run the full race, then stop it:

```sh
cd DronlyWork
./simulate/98_full_race_with_server.sh
```

Or use two terminals if you want to keep the server running after the demo.

Terminal 1, start RotorHazard with mock nodes:

```sh
cd DronlyWork
./simulate/00_start_mock_server.sh
```

Terminal 2, run the full race simulation:

```sh
cd DronlyWork
./simulate/99_full_race_demo.sh
```

Open the frontend at `http://localhost:5173`, press Connect, and watch the Live race server events panel. During the simulated race you should see lap/leaderboard/callout events arrive.

## Step-By-Step Scripts

```sh
./simulate/01_prepare_event.sh
./simulate/02_start_race.sh
./simulate/03_drive_laps.sh
./simulate/04_stop_and_save.sh
```

## Environment Variables

- `RH_SOCKET_URL`: Socket URL. Default: `http://localhost:5000`.
- `SIM_DATA_DIR`: Isolated RotorHazard data directory. Default: `DronlyWork/simulate/data`.
- `SIM_NODES`: Mock node count and simulated race seats. Default: `4`.
- `SIM_PILOTS`: Pilot count. Default: same as `SIM_NODES`.
- `SIM_LAPS`: Counted laps to send after first pass. Default: `4`.
- `SIM_PREFIX`: Prefix for generated class/heat/pilots. Default: `DRONLY`.
- `SIM_MIN_LAP_SEC`: Min lap seconds used for faster simulation. Default: `1`.
- `SIM_SAVE`: Save after stopping. Default: `1`; set `SIM_SAVE=0` to stop without saving.
- `SIM_FORCE_DISCARD`: Set `1` to discard an active/finished race before preparing.

Example:

```sh
SIM_NODES=6 SIM_PILOTS=6 SIM_LAPS=5 ./simulate/99_full_race_demo.sh
```

## Safety Notes

`00_start_mock_server.sh` uses `DronlyWork/simulate/data` by default, so the recommended flow does not touch your normal RotorHazard data directory. The client scripts still mutate whichever RotorHazard server `RH_SOCKET_URL` points to: they add/reuse race classes, pilots, heats, and saved race results.

If `01_prepare_event.sh` says the server has `0` nodes, restart RotorHazard with:

```sh
./simulate/00_start_mock_server.sh
```
