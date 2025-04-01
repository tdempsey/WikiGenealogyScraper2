"""
Script to verify the database setup for the genealogy batch scraper.
"""
import os
from sqlalchemy import create_engine, inspect

def verify_database():
    """Verify that database tables were created correctly."""
    database_url = os.environ.get("DATABASE_URL")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    print("Database tables:")
    for table_name in inspector.get_table_names():
        print(f"- {table_name}")
        print("  Columns:")
        for column in inspector.get_columns(table_name):
            print(f"  - {column['name']} ({column['type']})")
        print("")

if __name__ == "__main__":
    verify_database()