from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import pandas as pd
import numpy as np
import urllib.parse
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# SQLAlchemy Models
class User(Base):
    __tablename__ = 'User'
    Id = Column(Integer, primary_key=True)
    Name = Column(String)
    PreferredCategory = Column(String, nullable=True)
    SkillLevel = Column(String, nullable=True)
    RegistrationDate = Column(DateTime, default=datetime.utcnow)
    Rating = relationship("Rating", back_populates="student")

class Course(Base):
    __tablename__ = 'courses'
    Id = Column(Integer, primary_key=True)
    Name = Column(String)
    CourseCategory = Column(String)
    CreationDate = Column(DateTime, default=datetime.utcnow)
    LevelOfCourse = Column(String)
    AverageRating = Column(Float, nullable=True)
    ImgUrl = Column(String, nullable=True)
    Price = Column(Float, default=0)
    Discount = Column(Float, default=0)
    CourseTags = relationship("CourseTag", back_populates="Course")
    Rating = relationship("Rating", back_populates="Course")

class Rating(Base):
    __tablename__ = 'Rating'
    Id = Column(Integer, primary_key=True)
    StudentId = Column(Integer, ForeignKey('User.Id'))
    CourseId = Column(Integer, ForeignKey('courses.Id'))
    ClickCount = Column(Integer, default=0)
    TimeSpentHours = Column(Float, default=0)
    CompletionStatus = Column(String)
    Stars = Column(Integer)
    RatingDate = Column(DateTime, default=datetime.utcnow)
    student = relationship("User", back_populates="Rating")
    Course = relationship("Course", back_populates="Rating")

class Tag(Base):
    __tablename__ = 'Tags'
    Id = Column(Integer, primary_key=True)
    Name = Column(String)
    CourseTags = relationship("CourseTag", back_populates="Tag")

class CourseTag(Base):
    __tablename__ = 'CourseTags'
    CourseId = Column(Integer, ForeignKey('courses.Id'), primary_key=True)
    TagId = Column(Integer, ForeignKey('Tags.Id'), primary_key=True)
    Course = relationship("Course", back_populates="CourseTags")
    Tag = relationship("Tag", back_populates="CourseTags")

class Database:
    def __init__(self):
        self.use_sample_data = False
        try:
            server = os.getenv("DB_SERVER", "SQL1003.site4now.net")
            database = os.getenv("DB_NAME", "db_ab91bf_grad")
            username = os.getenv("DB_USER", "db_ab91bf_grad_admin")
            password = os.getenv("DB_PASSWORD", "asdzxc123")

            connection_strings = [
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes",
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},1433;DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes"
            ]

            connected = False
            last_error = None

            for conn_str in connection_strings:
                try:
                    logger.info(f"Trying connection string: {conn_str}")
                    encoded_conn = urllib.parse.quote_plus(conn_str)
                    engine_url = f"mssql+pyodbc:///?odbc_connect={encoded_conn}"
                    self.engine = create_engine(
                        engine_url,
                        echo=False,
                        pool_timeout=30,
                        pool_pre_ping=True,
                        pool_recycle=3600
                    )
                    with self.engine.connect() as connection:
                        result = connection.execute(text("SELECT @@VERSION"))
                        version = result.scalar()
                        logger.info(f"Connected to SQL Server version: {version}")
                        connected = True
                        break
                except Exception as e:
                    logger.error(f"Connection attempt failed: {str(e)}")
                    last_error = e
                    continue

            if not connected:
                raise last_error if last_error else Exception("All connection attempts failed")

            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            self.use_sample_data = True
            logger.warning("Using sample data due to database connection failure")

    def test_connection(self):
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_data(self):
        if self.use_sample_data:
            return self._get_sample_data()

        session = self.SessionLocal()
        try:
            query = session.query(
                User.Id.label('User ID'),
                User.PreferredCategory,
                User.SkillLevel,
                Course.Id.label('Course ID'),
                Course.Name.label('Course Title'),
                Course.CourseCategory,
                Course.LevelOfCourse.label('Difficulty Level'),
                Course.ImgUrl,
                Course.Price,
                Course.Discount,
                Course.AverageRating,
                Rating.ClickCount.label('Click Count'),
                Rating.TimeSpentHours.label('Time Spent (hours)'),
                Rating.CompletionStatus.label('Completion Status'),
                Rating.Stars.label('Rating')
            ).join(Rating, User.Id == Rating.StudentId).join(Course, Rating.CourseId == Course.Id)

            df = pd.read_sql(query.statement, session.bind)

            # Calculate average rating from Rating table
            rating_query = session.query(
                Rating.CourseId.label('Course ID'),
                Rating.Stars
            )
            rating_df = pd.read_sql(rating_query.statement, session.bind)

            avg_rating_df = rating_df.groupby('Course ID').apply(
                lambda x: np.mean([stars for stars in x['Stars'] if stars is not None]) if any(stars is not None for stars in x['Stars']) else 0
            ).reset_index(name='CalculatedAverageRating')

            # Merge with the main dataframe
            df = df.merge(avg_rating_df, on='Course ID', how='left')
            # Use the calculated average rating if available, otherwise use the course's average rating
            df['AverageRating'] = df['CalculatedAverageRating'].fillna(df['AverageRating']).fillna(0)

            # Get course tags/keywords
            tag_query = session.query(
                CourseTag.CourseId,
                Tag.Name.label('TagName')
            ).join(Tag, CourseTag.TagId == Tag.Id)

            tags_df = pd.read_sql(tag_query.statement, session.bind)
            tags_grouped = tags_df.groupby('CourseId')['TagName'].apply(lambda x: ', '.join(x)).reset_index()
            tags_grouped.columns = ['Course ID', 'Keywords']

            df = df.merge(tags_grouped, on='Course ID', how='left')
            df['Keywords'] = df['Keywords'].fillna('')

            return df
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return self._get_sample_data()
        finally:
            session.close()

    def _get_sample_data(self):
        logger.info("Generating sample data")
        np.random.seed(42)
        n_samples = 500
        categories = ['Programming', 'Data Science', 'Web Development', 'Mobile Development', 'DevOps']
        skill_levels = ['beginner', 'intermediate', 'advanced']
        keywords = [
            'python, machine learning, data science',
            'web development, html, css, javascript',
            'data analysis, statistics, R',
            'mobile development, flutter, dart',
            'devops, docker, kubernetes',
            'artificial intelligence, deep learning, neural networks',
            'cloud computing, aws, azure',
            'database, sql, nosql, mongodb',
            'cybersecurity, ethical hacking, penetration testing',
            'game development, unity, unreal engine',
            'blockchain, smart contracts, ethereum',
            'big data, hadoop, spark'
        ]

        return pd.DataFrame({
            'User ID': range(1, n_samples + 1),
            'PreferredCategory': np.random.choice(categories, n_samples),
            'SkillLevel': np.random.choice(skill_levels, n_samples),
            'Course ID': range(1, n_samples + 1),
            'Course Title': [f'Course {i}' for i in range(1, n_samples + 1)],
            'CourseCategory': np.random.choice(categories, n_samples),
            'Difficulty Level': np.random.choice(skill_levels, n_samples),
            'ImgUrl': [f'https://example.com/course_{i}.jpg' for i in range(1, n_samples + 1)],
            'Price': np.random.randint(10, 200, n_samples),
            'Discount': np.random.randint(0, 50, n_samples),
            'Click Count': np.random.randint(0, 1000, n_samples),
            'Time Spent (hours)': np.random.uniform(0, 20, n_samples).round(2),
            'Completion Status': np.random.choice(['Yes', 'No'], n_samples),
            'Rating': np.random.randint(1, 6, n_samples),
            'AverageRating': np.random.uniform(3.5, 5.0, n_samples).round(2),
            'Keywords': np.random.choice(keywords, n_samples)
        })