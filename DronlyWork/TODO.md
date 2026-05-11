python -m venv venv
source venv/bin/activate
pip install -r src/server/requirements.txt
python src/server/server.py
python src/server/generate_asyncapi.py



load_data
set_current_heat
activate_heat
deactivate_heat
alter_race
current_race_marshal
get_server_time 
schedule_race
cancel_schedule_race
stage_race
stop_race
save_laps
resave_laps
replace_current_laps
discard_laps
calc_pilots
calc_reset
get_race_scheduled
get_pilotrace
connect
disconnect
