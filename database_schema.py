"""
Database schema for genealogy data collected from Wikidata.
"""
import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Create base class for declarative models
Base = declarative_base()

# Many-to-many relationship table for person occupations
person_occupation = Table(
    'person_occupation', 
    Base.metadata,
    Column('person_id', String(20), ForeignKey('person.wikidata_id')),
    Column('occupation_id', Integer, ForeignKey('occupation.id'))
)

class Person(Base):
    """Person model to store biographical information."""
    __tablename__ = 'person'
    
    wikidata_id = Column(String(20), primary_key=True)
    name = Column(String(255), nullable=False)
    birth_date = Column(DateTime, nullable=True)
    death_date = Column(DateTime, nullable=True)
    bio = Column(Text, nullable=True)
    gender = Column(String(50), nullable=True)
    image_url = Column(String(255), nullable=True)
    birth_place = Column(String(255), nullable=True)
    
    # Relationships
    occupations = relationship("Occupation", secondary=person_occupation)
    
    # Track when this record was last updated
    last_updated = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Person(wikidata_id='{self.wikidata_id}', name='{self.name}')>"

class Occupation(Base):
    """Occupation model to store occupation data."""
    __tablename__ = 'occupation'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    
    def __repr__(self):
        return f"<Occupation(id={self.id}, name='{self.name}')>"

class Relationship(Base):
    """Relationship model to store relationships between people."""
    __tablename__ = 'relationship'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(20), ForeignKey('person.wikidata_id'), nullable=False)
    target_id = Column(String(20), ForeignKey('person.wikidata_id'), nullable=False)
    relation_type = Column(String(50), nullable=False)  # parent, child, spouse, sibling
    
    # Define relationships to Person
    source = relationship("Person", foreign_keys=[source_id])
    target = relationship("Person", foreign_keys=[target_id])
    
    def __repr__(self):
        return f"<Relationship(source_id='{self.source_id}', target_id='{self.target_id}', type='{self.relation_type}')>"

def setup_database():
    """Create database tables if they don't exist."""
    database_url = os.environ.get("DATABASE_URL")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    # Create tables when script is run directly
    session = setup_database()
    print("Database tables created successfully.")