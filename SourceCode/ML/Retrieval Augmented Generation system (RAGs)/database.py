import pyodbc
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=SQL1003.site4now.net;"
        "DATABASE=db_ab91bf_grad;"
        "UID=db_ab91bf_grad_admin;"
        "PWD=asdzxc123;"
    )
    try:
        conn = pyodbc.connect(conn_str)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def load_data_from_db():
    category_buckets = defaultdict(list)
    total_courses = 0

    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database, returning empty buckets")
            return category_buckets

        cursor = conn.cursor()
        query = """
        SELECT Id, Name, Describtion, LevelOfCourse, CourseCategory, CourseUrl
        FROM courses
        """
        cursor.execute(query)

        for row in cursor.fetchall():
            category = row.CourseCategory.lower().strip() if row.CourseCategory else "general"
            course = {
                "Id": row.Id,  # Using row.Id directly since that's the column name
                "course_title": row.Name.strip() if row.Name else "Untitled Course",
                "description": row.Describtion.strip() if row.Describtion else "No description available",
                "level": row.LevelOfCourse.lower().strip() if row.LevelOfCourse else "general",
                "url": row.CourseUrl.strip() if row.CourseUrl else "URL not available"
            }
            # Add debug logging to verify the ID is being retrieved correctly
            logger.debug(f"Loading course with ID: {row.Id}")
            
            category_buckets[category].append(course)
            total_courses += 1
            logger.debug(f"Loaded course: ID: {course['Id']}, Title: {course['course_title']}, Category: {category}")
            
        # Log all categories and levels
        categories = list(category_buckets.keys())
        levels = set(course["level"] for courses in category_buckets.values() for course in courses)
        logger.info(f"Loaded {total_courses} courses across {len(categories)} categories: {categories}")
        logger.info(f"Available levels: {list(levels)}")
        
        # Log specific courses for "machine learning" and "beginner"
        if "machine learning" in category_buckets:
            ml_courses = [c for c in category_buckets["machine learning"] if c["level"] == "beginner"]
            logger.info(f"Found {len(ml_courses)} beginner-level machine learning courses")
            for course in ml_courses[:5]:  # Log up to 5 for brevity
                logger.info(f"Machine learning course: {course}")
        else:
            logger.warning("No machine learning courses found in database")

        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error loading data from database: {e}")

    return category_buckets