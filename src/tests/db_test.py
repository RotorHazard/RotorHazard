import time
import random
import os
import sys
import signal
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# Global flag for graceful shutdown
should_exit = False

def signal_handler(signum, frame):
    global should_exit
    print("\nReceived shutdown signal, finishing current operations...")
    should_exit = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Create base class for models
Base = declarative_base()

# Define models
class Pilot(Base):
    __tablename__ = 'pilot'
    id = Column(Integer, primary_key=True)
    callsign = Column(String(80), nullable=False)
    team = Column(String(80), nullable=False)
    phonetic = Column(String(80), nullable=False)
    name = Column(String(120), nullable=False)
    color = Column(String(7), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

class Heat(Base):
    __tablename__ = 'heat'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=True)
    class_id = Column(Integer, nullable=False)
    _cache_status = Column(String(16), nullable=False)
    order = Column(Integer, nullable=True)
    status = Column(Integer, nullable=False)
    auto_frequency = Column(Boolean, nullable=False)
    group_id = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False, default=True)

class SavedRaceMeta(Base):
    __tablename__ = 'saved_race_meta'
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, nullable=False)
    heat_id = Column(Integer, nullable=False)
    class_id = Column(Integer, nullable=False)
    format_id = Column(Integer, nullable=False)
    start_time = Column(Integer, nullable=False)
    start_time_formatted = Column(String, nullable=False)
    _cache_status = Column(String(16), nullable=False)

class SavedPilotRace(Base):
    __tablename__ = 'saved_pilot_race'
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('saved_race_meta.id'), nullable=False)
    node_index = Column(Integer, nullable=False)
    pilot_id = Column(Integer, ForeignKey('pilot.id'), nullable=False)
    history_values = Column(String, nullable=True)
    history_times = Column(String, nullable=True)
    penalty_time = Column(Integer, nullable=False)
    enter_at = Column(Integer, nullable=False)
    exit_at = Column(Integer, nullable=False)

class SavedRaceLap(Base):
    __tablename__ = 'saved_race_lap'
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('saved_race_meta.id'), nullable=False)
    pilotrace_id = Column(Integer, ForeignKey('saved_pilot_race.id'), nullable=False)
    node_index = Column(Integer, nullable=False)
    pilot_id = Column(Integer, ForeignKey('pilot.id'), nullable=False)
    lap_time_stamp = Column(Float, nullable=False)
    lap_time = Column(Float, nullable=False)
    lap_time_formatted = Column(String, nullable=False)
    source = Column(Integer, nullable=False)
    deleted = Column(Boolean, nullable=False)

def create_test_data(session, num_pilots=50, num_heats=20):
    """Create initial test data"""
    # Create pilots
    pilots = []
    for i in range(num_pilots):
        pilot = Pilot(
            callsign=f"Pilot{i}",
            team="Test Team",
            phonetic=f"Pilot{i}",
            name=f"Test Pilot {i}",
            color="#000000",
            active=True
        )
        session.add(pilot)
        pilots.append(pilot)
    session.commit()
    
    # Create heats
    heats = []
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
        session.add(heat)
        heats.append(heat)
    session.commit()
    
    return pilots, heats

def simulate_race(session, pilots, heats):
    """Simulate a single race with random data"""
    try:
        # Create race meta
        race = SavedRaceMeta(
            round_id=1,
            heat_id=random.choice(heats).id,
            class_id=1,
            format_id=1,
            start_time=int(time.time()),
            start_time_formatted=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            _cache_status="valid"
        )
        session.add(race)
        session.flush()

        # Create pilot race entries
        selected_pilots = random.sample(pilots, min(8, len(pilots)))  # Simulate 8 pilots per race
        for pilot in selected_pilots:
            pilot_race = SavedPilotRace(
                race_id=race.id,
                node_index=pilot.id,
                pilot_id=pilot.id,
                history_values="",
                history_times="",
                penalty_time=0,
                enter_at=0,
                exit_at=0
            )
            session.add(pilot_race)
            session.flush()

            # Create random number of laps (5-20) for each pilot
            num_laps = random.randint(5, 20)
            for lap_num in range(num_laps):
                lap = SavedRaceLap(
                    race_id=race.id,
                    pilotrace_id=pilot_race.id,
                    node_index=pilot.id,
                    pilot_id=pilot.id,
                    lap_time_stamp=time.time(),
                    lap_time=random.uniform(10, 20),
                    lap_time_formatted="00:00:15.000",
                    source=0,
                    deleted=False
                )
                session.add(lap)

        session.commit()
        return True
    except Exception as e:
        print(f"Error in race simulation: {str(e)}")
        session.rollback()
        return False

def run_benchmark():
    engine = None
    session = None
    
    try:
        # Initialize database
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'rh_test.sqlite')
        print(f"Initializing test database at: {db_path}")
        
        # Remove existing database if it exists
        if os.path.exists(db_path):
            print("Removing existing database...")
            os.remove(db_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine with optimized settings
        db_uri = f'sqlite:///{db_path}'
        engine = create_engine(db_uri, 
            connect_args={
                'check_same_thread': False,
                'timeout': 30,
                'isolation_level': None,
                'cached_statements': 100
            }
        )
        
        # Set SQLite PRAGMAs after connection
        def set_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA cache_size=-10000")
            cursor.execute("PRAGMA synchronous=FULL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
        
        from sqlalchemy import event
        event.listen(engine, 'connect', set_pragmas)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create initial test data
        print("Creating initial test data...")
        pilots, heats = create_test_data(session)
        print(f"Created {len(pilots)} pilots and {len(heats)} heats")

        # Run continuous load simulation for 2 minutes
        print("\nStarting continuous load simulation for 2 minutes...")
        print("Press Ctrl+C to stop early")
        
        start_time = time.time()
        end_time = start_time + 120  # 2 minutes
        races_completed = 0
        total_laps = 0
        
        while time.time() < end_time and not should_exit:
            # Simulate a race
            if simulate_race(session, pilots, heats):
                races_completed += 1
                # Count laps for this race
                laps = session.query(SavedRaceLap).filter_by(race_id=session.query(SavedRaceMeta).order_by(SavedRaceMeta.id.desc()).first().id).count()
                total_laps += laps
                
                # Print progress every 10 races
                if races_completed % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"Completed {races_completed} races ({total_laps} laps) in {elapsed:.1f} seconds")
            
            # Add some random delay between races (0.1-0.5 seconds)
            time.sleep(random.uniform(0.1, 0.5))

        # Print final statistics
        elapsed = time.time() - start_time
        print(f"\nSimulation complete!")
        print(f"Total time: {elapsed:.1f} seconds")
        print(f"Races completed: {races_completed}")
        print(f"Total laps recorded: {total_laps}")
        print(f"Average race time: {elapsed/races_completed:.2f} seconds")
        print(f"Average laps per race: {total_laps/races_completed:.1f}")

        # Cleanup
        print("\nCleaning up test data...")
        session.query(SavedRaceLap).delete()
        session.query(SavedPilotRace).delete()
        session.query(SavedRaceMeta).delete()
        session.query(Heat).delete()
        session.query(Pilot).delete()
        session.commit()

    except Exception as e:
        print(f"Error during benchmark: {str(e)}")
        if session:
            session.rollback()
    finally:
        # Clean up resources
        if session:
            session.close()
        if engine:
            engine.dispose()
        print("\nBenchmark complete!")

if __name__ == "__main__":
    run_benchmark() 