import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import logging
from joblib import dump, load
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, data):
        self.data = data.copy()
        self.model_file = '/code/rf_model.joblib'
        self.tfidf_matrix_file = '/code/tfidf_matrix.joblib'
        self.tfidf_reduced_file = '/code/tfidf_reduced_file.joblib'
        self._preprocess_data()
        self._train_model()
        self._setup_content_based()

    def update_data(self, new_data):
        """Update the data without retraining the model"""
        self.data = new_data.copy()
        self._preprocess_data()
        logger.info("Data updated successfully")

    def _preprocess_data(self):
        try:
            # Ensure all required columns exist
            required_columns = [
                'Course ID', 'Course Title', 'CourseCategory', 'Difficulty Level',
                'Click Count', 'Time Spent (hours)', 'Completion Status', 'Rating',
                'PreferredCategory', 'SkillLevel', 'Price', 'Discount', 'ImgUrl',
                'AverageRating'
            ]
            
            # Log available columns for debugging
            logger.info(f"Available columns: {self.data.columns.tolist()}")
            
            for col in required_columns:
                if col not in self.data.columns:
                    logger.warning(f"Column {col} not found in data, adding with default values")
                    if col == 'Click Count':
                        self.data[col] = 0
                    elif col == 'Time Spent (hours)':
                        self.data[col] = 0.0
                    elif col == 'Completion Status':
                        self.data[col] = 'No'
                    elif col == 'Rating':
                        self.data[col] = 0
                    elif col == 'AverageRating':
                        self.data[col] = 0.0
                    else:
                        self.data[col] = ''

            # Feature Engineering
            self.data['Course Popularity'] = self.data.groupby('Course ID')['Click Count'].transform('sum')
            self.data['Completion Status Numeric'] = self.data['Completion Status'].apply(lambda x: 1 if x == 'Yes' else 0.5)
            self.data['User Engagement'] = self.data['Time Spent (hours)'] * self.data['Completion Status Numeric']
            
            # Map difficulty levels
            difficulty_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            self.data['Course Difficulty Score'] = self.data['Difficulty Level'].map(difficulty_map)
            
            # Calculate user-course match
            self.data['User-Course Match'] = self.data.apply(
                lambda row: 1 if row['PreferredCategory'] == row['CourseCategory'] else 0, axis=1
            )

            # Features and target
            self.X = self.data[[
                'PreferredCategory', 'SkillLevel', 'Course Difficulty Score',
                'User Engagement', 'Course Popularity', 'User-Course Match'
            ]]
            self.y = self.data['Rating']
            self.X = pd.get_dummies(self.X, columns=['PreferredCategory', 'SkillLevel'], drop_first=True)
            
            logger.info("Data preprocessing completed successfully")
            
        except Exception as e:
            logger.error(f"Error in data preprocessing: {str(e)}")
            raise

    def _train_model(self):
        try:
            if os.path.exists(self.model_file):
                self.model = load(self.model_file)
                logger.info("Loaded cached RandomForest model")
            else:
                self.model = RandomForestRegressor(n_estimators=50, random_state=42)
                X_train, X_test, y_train, y_test = train_test_split(
                    self.X, self.y, test_size=0.2, random_state=42
                )
                self.model.fit(X_train, y_train)
                y_pred = self.model.predict(X_test)
                logger.info(f"MSE: {mean_squared_error(y_test, y_pred):.4f}")
                logger.info(f"MAE: {mean_absolute_error(y_test, y_pred):.4f}")
                logger.info(f"R2: {r2_score(y_test, y_pred):.4f}")
                dump(self.model, self.model_file)
                logger.info("Saved RandomForest model to cache")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise

    def _setup_content_based(self):
        try:
            if os.path.exists(self.tfidf_matrix_file) and os.path.exists(self.tfidf_reduced_file):
                self.tfidf_matrix = load(self.tfidf_matrix_file)
                self.tfidf_reduced = load(self.tfidf_reduced_file)
                logger.info("Loaded cached TF-IDF and SVD matrices")
            else:
                self.tfidf = TfidfVectorizer(stop_words='english', max_features=2000)
                self.tfidf_matrix = self.tfidf.fit_transform(self.data['Keywords'].fillna(""))
                n_features = self.tfidf_matrix.shape[1]
                logger.info(f"TF-IDF matrix has {n_features} features")
                # Adjust n_components to be at most n_features
                n_components = min(50, n_features) if n_features > 0 else 1
                self.svd = TruncatedSVD(n_components=n_components, random_state=42)
                self.tfidf_reduced = self.svd.fit_transform(self.tfidf_matrix)
                dump(self.tfidf_matrix, self.tfidf_matrix_file)
                dump(self.tfidf_reduced, self.tfidf_reduced_file)
                logger.info("Saved TF-IDF and SVD matrices to cache")
            
            self.nn_model = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
            self.nn_model.fit(self.tfidf_reduced)
        except Exception as e:
            logger.error(f"Error setting up content-based filtering: {str(e)}")
            raise

    def get_random_recommendations(self, top_n=10):
        try:
            popular_courses = self.data.sort_values(by=['AverageRating', 'Course Popularity'], ascending=[False, False])
            unique_courses = popular_courses[[
                'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                'CourseCategory', 'Price', 'Discount'
            ]].drop_duplicates(subset=['Course ID'])
            random_courses = unique_courses.sample(n=min(top_n, len(unique_courses)))
            random_courses['DiscountedPrice'] = random_courses.apply(
                lambda row: row['Price'] - (row['Price'] * row['Discount'] / 100), axis=1
            )
            return random_courses
        except Exception as e:
            logger.error(f"Error in random recommendations: {str(e)}")
            return pd.DataFrame()

    def get_recommendations(self, user_id, preferred_category, skill_level, top_n=20):
        try:
            # Ensure Click Count is numeric and handle any null values
            self.data['Click Count'] = pd.to_numeric(self.data['Click Count'], errors='coerce').fillna(0)
            
            # Get user's click history across all categories
            user_data = self.data[self.data['User ID'] == user_id]
            
            if user_data.empty:
                # If no user data, get recommendations based on preferred category and skill level
                recommendations = self.data[
                    (self.data['CourseCategory'] == preferred_category) &
                    (self.data['Difficulty Level'] == skill_level)
                ][[
                    'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                    'CourseCategory', 'Price', 'Discount'
                ]].drop_duplicates()
                
                # Sort by average rating
                recommendations = recommendations.sort_values('AverageRating', ascending=False)
            else:
                # Get courses from categories the user has clicked on
                clicked_categories = user_data['CourseCategory'].unique()
                
                # Get recommendations based on user's click behavior
                behavior_rec = self.data[
                    (self.data['CourseCategory'].isin(clicked_categories))
                ][[
                    'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                    'CourseCategory', 'Price', 'Discount', 'Click Count'
                ]].drop_duplicates()
                
                # Sort by click count and average rating
                behavior_rec = behavior_rec.sort_values(['Click Count', 'AverageRating'], ascending=[False, False])
                
                # If we don't have enough recommendations, add some from preferred category
                if len(behavior_rec) < top_n:
                    preferred_rec = self.data[
                        (self.data['CourseCategory'] == preferred_category) &
                        (self.data['Difficulty Level'] == skill_level)
                    ][[
                        'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                        'CourseCategory', 'Price', 'Discount'
                    ]].drop_duplicates()
                    
                    # Sort preferred recommendations by average rating
                    preferred_rec = preferred_rec.sort_values('AverageRating', ascending=False)
                    
                    # Combine and remove duplicates
                    behavior_rec = pd.concat([behavior_rec, preferred_rec]).drop_duplicates(subset=['Course ID'])
                
                recommendations = behavior_rec
            
            # Get top N recommendations
            recommendations = recommendations.head(top_n)
            
            # Add discounted price
            recommendations['DiscountedPrice'] = recommendations.apply(
                lambda row: row['Price'] - (row['Price'] * row['Discount'] / 100), axis=1
            )
            
            # Ensure we have all required columns
            required_columns = [
                'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                'CourseCategory', 'Price', 'Discount', 'DiscountedPrice'
            ]
            
            for col in required_columns:
                if col not in recommendations.columns:
                    logger.warning(f"Column {col} missing in recommendations, adding with default value")
                    if col == 'AverageRating':
                        recommendations[col] = 0.0
                    elif col in ['Price', 'Discount', 'DiscountedPrice']:
                        recommendations[col] = 0
                    else:
                        recommendations[col] = ''
            
            return recommendations[required_columns]
            
        except Exception as e:
            logger.error(f"Error in get_recommendations: {str(e)}")
            # Return recommendations from preferred category as fallback
            try:
                fallback_rec = self.data[
                    (self.data['CourseCategory'] == preferred_category) &
                    (self.data['Difficulty Level'] == skill_level)
                ][[
                    'Course ID', 'Course Title', 'AverageRating', 'ImgUrl', 'Difficulty Level',
                    'CourseCategory', 'Price', 'Discount'
                ]].drop_duplicates().head(top_n)
                
                fallback_rec['DiscountedPrice'] = fallback_rec.apply(
                    lambda row: row['Price'] - (row['Price'] * row['Discount'] / 100), axis=1
                )
                
                return fallback_rec
            except Exception as fallback_error:
                logger.error(f"Fallback recommendation failed: {str(fallback_error)}")
                return pd.DataFrame()