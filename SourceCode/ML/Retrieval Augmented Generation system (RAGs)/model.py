import os
import json
from collections import defaultdict
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, FieldCondition, MatchValue, Filter
from database import load_data_from_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set cache directory for Hugging Face models
os.environ["HF_HOME"] = "/app/cache"
os.environ["HF_HUB_CACHE"] = "/app/cache"

# Initialize environment variables
chat_groq_api = os.getenv("GROQ_API_KEY")
qdrant_api = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QDRANT_API_URL")

# Initialize models
llm = ChatGroq(temperature=0.5, model_name="llama-3.3-70b-versatile", api_key=chat_groq_api)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={},
    encode_kwargs={"normalize_embeddings": True}
)
qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api)

def verify_qdrant_collection(collection_name='course_roadmaps'):
    try:
        collection_info = qdrant_client.get_collection(collection_name)
        points_count = collection_info.points_count
        logger.info(f"Collection '{collection_name}' exists with vector size {collection_info.config.params.vectors.size}, points: {points_count}")
        return points_count > 0
    except Exception as e:
        logger.error(f"Error verifying collection '{collection_name}': {e}")
        return False

def store_data_to_qdrant(data, collection_name='course_roadmaps', batch_size=384):
    try:
        if not qdrant_client.collection_exists(collection_name):
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Created collection '{collection_name}'")
        else:
            logger.info(f"Collection '{collection_name}' already exists, will upsert data")

        # Add keyword indexes
        qdrant_client.create_payload_index(collection_name=collection_name, field_name="category", field_schema="keyword")
        qdrant_client.create_payload_index(collection_name=collection_name, field_name="level", field_schema="keyword")
        logger.info(f"Created keyword indexes for 'category' and 'level'")

        points = []
        point_id = 0
        for category, course_list in data.items():
            logger.debug(f"Processing category: {category}, {len(course_list)} courses")
            for entry in course_list:
                embedding = embeddings.embed_query(entry["course_title"] + " " + entry["description"])
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={**entry, "category": category}
                ))
                point_id += 1
                logger.debug(f"Created point {point_id} for course: {entry['course_title']}")

        if points:
            qdrant_client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Stored {len(points)} course embeddings")
        else:
            logger.warning("No points to store in Qdrant")
        return True
    except Exception as e:
        logger.error(f"Error storing data to Qdrant: {e}")
        return False

def search_courses(category=None, level=None, top_k=50):
    try:
        must_conditions = []
        if category:
            must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category.lower())))
        if level:
            must_conditions.append(FieldCondition(key="level", match=MatchValue(value=level.lower())))
        logger.info(f"Searching courses with category: {category}, level: {level}, top_k: {top_k}")

        query_filter = Filter(must=must_conditions) if must_conditions else None

        results = qdrant_client.scroll(
            collection_name="course_roadmaps",
            scroll_filter=query_filter,
            with_payload=True,
            with_vectors=False,
            limit=top_k
        )[0]

        logger.info(f"Found {len(results)} courses")
        for result in results[:5]:  # Log up to 5 results for brevity
            logger.debug(f"Search result: {result.payload}")
        return [r.payload for r in results]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def build_roadmap_prompt(user_interests, user_level, context=None, roadmap_type="courses", output_style="detailed", num_stages=7):
    if isinstance(user_interests, list):
        user_interests = ", ".join(user_interests)

    template = f"""You are an AI-driven Roadmap Generation System specializing in {roadmap_type} recommendations.
A user wants to learn {user_interests} and is currently at a {user_level} level.
Your task is to generate a structured roadmap in {num_stages} stages based ONLY on the following courses:

{context}

Requirements:
- Do NOT generate external titles or URLs.
- Each stage must list 1 course with: Title, Description, Level, URL.
- Explain why each stage matters and how it leads to the next.
- Output format should be {output_style}.
"""
    logger.debug(f"Generated prompt: {template[:500]}...")  # Log first 500 chars
    return template.strip()

def generate_roadmap(user_interests, user_level, category, num_stages=7):
    try:
        logger.info(f"Generating roadmap for interests: {user_interests}, level: {user_level}, category: {category}, num_stages: {num_stages}")
        course_results = search_courses(category=category, level=user_level, top_k=num_stages)
        if not course_results:
            logger.warning(f"No courses found for category: {category}, level: {user_level}")
            return {
                "success": False,
                "error": "No matching courses found.",
                "data": None
            }

        # Create stages directly from course results
        stages = []
        for i, course in enumerate(course_results, 1):
            stage = {
                "stage_number": i,
                "Id": course['Id'],
                "title": course['course_title'],
                "description": course['description'],
                "level": course['level'],
                "url": course.get('url', 'URL not available')
            }
            
            # Generate explanation using LLM
            explanation_prompt = f"""
            Given this course in a learning roadmap:
            Title: {course['course_title']}
            Description: {course['description']}
            Level: {course['level']}
            
            Generate a brief explanation of why this stage is important and how it connects to the next stage.
            Keep it concise and focused on the learning progression.
            """
            
            try:
                explanation = llm.predict(explanation_prompt).strip()
                stage["explanation"] = explanation
            except Exception as e:
                logger.warning(f"Failed to generate explanation for stage {i}: {e}")
                stage["explanation"] = "This stage builds upon previous knowledge and prepares you for the next level."
            
            stages.append(stage)
            logger.debug(f"Added stage {i}: {stage['title']}")

        return {
            "success": True,
            "error": None,
            "data": {
                "roadmap": {
                    "user_interests": user_interests,
                    "user_level": user_level,
                    "category": category,
                    "num_stages": num_stages,
                    "stages": stages[:num_stages]  # Ensure we only return the requested number of stages
                }
            }
        }
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        return {
            "success": False,
            "error": f"Error generating roadmap: {str(e)}",
            "data": None
        }

def initialize_data():
    logger.info("Starting Qdrant initialization")
    course_data = load_data_from_db()  # Always load to log categories/levels
    logger.info(f"Loaded {len(course_data)} categories with courses: {[len(courses) for courses in course_data.values()]}")
    
    # Reset the collection to ensure it has the new structure
    reset_qdrant_collection("course_roadmaps")
    
    # Now create and populate the collection
    logger.info("Loading data into Qdrant")
    store_data_to_qdrant(course_data, "course_roadmaps")


def reset_qdrant_collection(collection_name='course_roadmaps'):
    try:
        if qdrant_client.collection_exists(collection_name):
            qdrant_client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection '{collection_name}'")
        return True
    except Exception as e:
        logger.error(f"Error resetting collection: {e}")
        return False
