"""
Script to set up the database for the genealogy batch scraper.
"""
from database_schema import setup_database

if __name__ == "__main__":
    print("Setting up database tables...")
    session = setup_database()
    print("Database setup complete!")