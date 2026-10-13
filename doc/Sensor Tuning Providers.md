# Sensor Tuning providers

The proposed RHAPI 1.11 receiver registration API lets plugins expose receivers
in Settings > Sensor Tuning without creating additional race seats. See
`ui.register_sensor_tuning()` in [RHAPI](RHAPI.md) for the callback contract.

The Settings page polls cached receiver snapshots through authenticated routes.
Each receiver keeps a separate graph and confirmed threshold state. A failed
write restores the last confirmed levels; removing a node/provider stops its
graph and removes its controls. RSSI histories remain bounded while paused.

Capture is optional. Providers implementing it collect their own receiver
samples for three seconds, apply RH's EnterAt peak margin, and return confirmed
hardware levels. Averaging belongs in the receiver callback rather than in the
browser: a browser only observes occasional snapshots and can miss RF samples.

## Regression checks

From `src/tests`, using RH's server Python requirements:

```text
python -m unittest test_server test_sensor_tuning
```

The UI checks use Node.js 18 or later, Playwright and Chromium as development
dependencies. From the repository root, after installing those dependencies:

```text
node --test src/tests/test_sensor_tuning_ui.cjs
```

`PLAYWRIGHT_MODULE` can point to an existing Playwright installation;
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` can point to an existing Chromium executable.
The checks load the repository's actual graph library and UI script with mocked
telemetry and write responses. They do not connect to timing hardware or start
a race server.
