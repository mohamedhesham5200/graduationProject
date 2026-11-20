from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import RecommendationRequest, RecommendationResponse
from app.database import Database
from app.recommender import RecommendationEngine
from datetime import datetime
import pandas as pd
import subprocess
import logging
from typing import Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Learnify Recommendation API",
    description="ML-powered course recommendation system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://learnify.runasp.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db = None
recommender = None
last_refresh_time = 0
recommendation_cache: Dict[str, tuple] = {}  # Cache for recommendations
CACHE_DURATION = 60  # Cache duration in seconds

def refresh_recommender():
    global db, recommender, last_refresh_time
    current_time = time.time()
    
    # Only refresh if more than 1 minute has passed since last refresh
    if current_time - last_refresh_time > 60:
        try:
            df = db.get_data()
            recommender = RecommendationEngine(df)
            last_refresh_time = current_time
            logger.info("Recommender refreshed with new data")
        except Exception as e:
            logger.error(f"Error refreshing recommender: {str(e)}")
            raise

@app.on_event("startup")
async def startup_event():
    global db, recommender
    try:
        db = Database()
        df = db.get_data()
        recommender = RecommendationEngine(df)
        logger.info("Application startup successful: database and recommender initialized")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": recommender is not None,
        "database_connected": db is not None and not getattr(db, 'use_sample_data', True),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/debug")
async def debug_connection():
    try:
        if db is None:
            return {"status": "error", "message": "Database not initialized"}
        
        test_query = "SELECT TOP 1 * FROM [User]"
        result = pd.read_sql(test_query, db.engine)
        
        return {
            "status": "success",
            "database_connected": True,
            "has_data": not result.empty,
            "row_count": len(result) if not result.empty else 0,
            "columns": list(result.columns) if not result.empty else [],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/test-db")
async def test_database():
    try:
        if db is None:
            return {
                "status": "error",
                "message": "Database not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        connection_test = db.test_connection()
        
        return {
            "status": "success" if connection_test else "error",
            "database_connected": connection_test,
            "using_sample_data": getattr(db, 'use_sample_data', True),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": str(type(e)),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/network-test")
async def network_test():
    try:
        result = subprocess.run(['/code/test_connection.sh'], 
                              capture_output=True, 
                              text=True)
        
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    global recommender
    
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        # Get fresh data and update recommender
        df = db.get_data()
        recommender.update_data(df)
        
        if not request.is_registered:
            recommendations = recommender.get_random_recommendations(request.top_n)
        else:
            if not all([request.user_id, request.preferred_category, request.skill_level]):
                raise HTTPException(
                    status_code=400,
                    detail="For registered users, user_id, preferred_category, and skill_level are required"
                )
            recommendations = recommender.get_recommendations(
                user_id=request.user_id,
                preferred_category=request.preferred_category,
                skill_level=request.skill_level,
                top_n=request.top_n
            )
        
        if recommendations.empty:
            raise HTTPException(status_code=404, detail="No recommendations found")

        return RecommendationResponse(recommendations=recommendations.to_dict(orient='records'))
    except Exception as e:
        logger.error(f"Error in recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))