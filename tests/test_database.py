from core.database import DatabaseManager

def test_initialisation_and_tables(tmp_path):
    db=DatabaseManager(tmp_path/"test.db"); db.initialise()
    assert db.count("zones")==0

def test_invalid_table_rejected(tmp_path):
    db=DatabaseManager(tmp_path/"test.db"); db.initialise()
    try: db.read("users; DROP TABLE zones")
    except ValueError: pass
    else: raise AssertionError("Invalid table accepted")

