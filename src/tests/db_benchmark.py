import time
import random
from ..server.Database import initialize, DB_session, Pilot, Heat, SavedRaceMeta, SavedPilotRace, SavedRaceLap
import os

def run_benchmark():
    # Initialize database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'rh.sqlite')
    initialize(f'sqlite:///{db_path}')

    # Test parameters
    num_pilots = 50
    num_heats = 20
    num_races = 10
    num_laps = 20

    print("Starting database benchmark...")
    print("Testing write operations...")

    # 1. Test pilot creation
    start_time = time.time()
    for i in range(num_pilots):
        pilot = Pilot(
            callsign=f"Pilot{i}",
            team="Test Team",
            phonetic=f"Pilot{i}",
            name=f"Test Pilot {i}",
            color="#000000",
            active=True
        )
        DB_session.add(pilot)
    DB_session.commit()
    pilot_time = time.time() - start_time
    print(f"Created {num_pilots} pilots in {pilot_time:.2f} seconds")

    # 2. Test heat creation
    start_time = time.time()
    for i in range(num_heats):
        heat = Heat(
            name=f"Heat {i}",
            class_id=1,
            _cache_status="valid",
            order=i,
            status=0,
            auto_frequency=True,
            group_id=1,
            active=True
        )
        DB_session.add(heat)
    DB_session.commit()
    heat_time = time.time() - start_time
    print(f"Created {num_heats} heats in {heat_time:.2f} seconds")

    # 3. Test race and lap creation
    start_time = time.time()
    for race_num in range(num_races):
        # Create race meta
        race = SavedRaceMeta(
            round_id=1,
            heat_id=1,
            class_id=1,
            format_id=1,
            start_time=int(time.time()),
            start_time_formatted="2024-01-01 00:00:00",
            _cache_status="valid"
        )
        DB_session.add(race)
        DB_session.flush()  # Get the race ID

        # Create pilot race entries
        for pilot_id in range(1, num_pilots + 1):
            pilot_race = SavedPilotRace(
                race_id=race.id,
                node_index=pilot_id,
                pilot_id=pilot_id,
                history_values="",
                history_times="",
                penalty_time=0,
                enter_at=0,
                exit_at=0
            )
            DB_session.add(pilot_race)
            DB_session.flush()

            # Create laps for this pilot
            for lap_num in range(num_laps):
                lap = SavedRaceLap(
                    race_id=race.id,
                    pilotrace_id=pilot_race.id,
                    node_index=pilot_id,
                    pilot_id=pilot_id,
                    lap_time_stamp=time.time(),
                    lap_time=random.uniform(10, 20),
                    lap_time_formatted="00:00:15.000",
                    source=0,
                    deleted=False
                )
                DB_session.add(lap)

    DB_session.commit()
    race_time = time.time() - start_time
    print(f"Created {num_races} races with {num_pilots} pilots and {num_laps} laps each in {race_time:.2f} seconds")

    print("\nTesting read operations...")

    # 4. Test reading all pilots
    start_time = time.time()
    pilots = DB_session.query(Pilot).all()
    read_pilot_time = time.time() - start_time
    print(f"Read {len(pilots)} pilots in {read_pilot_time:.2f} seconds")

    # 5. Test reading all heats
    start_time = time.time()
    heats = DB_session.query(Heat).all()
    read_heat_time = time.time() - start_time
    print(f"Read {len(heats)} heats in {read_heat_time:.2f} seconds")

    # 6. Test reading all races with related data
    start_time = time.time()
    races = DB_session.query(SavedRaceMeta).all()
    for race in races:
        pilot_races = DB_session.query(SavedPilotRace).filter_by(race_id=race.id).all()
        for pilot_race in pilot_races:
            laps = DB_session.query(SavedRaceLap).filter_by(pilotrace_id=pilot_race.id).all()
    read_race_time = time.time() - start_time
    print(f"Read {len(races)} races with all related data in {read_race_time:.2f} seconds")

    # Cleanup
    DB_session.query(SavedRaceLap).delete()
    DB_session.query(SavedPilotRace).delete()
    DB_session.query(SavedRaceMeta).delete()
    DB_session.query(Heat).delete()
    DB_session.query(Pilot).delete()
    DB_session.commit()

    print("\nBenchmark complete!")

if __name__ == "__main__":
    run_benchmark()