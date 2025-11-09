import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollegeRecommender:
    def __init__(self):
        self.course_vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.location_vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        self.fee_scaler = MinMaxScaler()
        self.rating_scaler = MinMaxScaler()
        self.is_fitted = False

    def preprocess_data(self, colleges_data):
        """Preprocess college data for ML model"""
        processed_data = []

        for college in colleges_data:
            # Handle courses
            if isinstance(college.get('courses'), list):
                courses_str = ', '.join(college['courses'])
            else:
                courses_str = str(college.get('courses', ''))

            # Handle location
            location_str = f"{college.get('city', '')} {college.get('state', '')}"

            # Handle fees and ratings
            avg_fee = float(college.get('avg_fee', 0))
            placement_rating = float(college.get('placement_rating', 0))

            processed_data.append({
                'college_data': college,
                'courses_str': courses_str,
                'location_str': location_str,
                'avg_fee': avg_fee,
                'placement_rating': placement_rating
            })

        return processed_data

    def fit(self, colleges_data):
        """Fit the model with college data"""
        try:
            self.processed_colleges = self.preprocess_data(colleges_data)

            # Extract features for vectorizers
            courses_corpus = [college['courses_str'] for college in self.processed_colleges]
            locations_corpus = [college['location_str'] for college in self.processed_colleges]
            fees = [[college['avg_fee']] for college in self.processed_colleges]
            ratings = [[college['placement_rating']] for college in self.processed_colleges]

            # Fit vectorizers and scalers
            self.course_features = self.course_vectorizer.fit_transform(courses_corpus)
            self.location_features = self.location_vectorizer.fit_transform(locations_corpus)
            self.fee_scaler.fit(fees)
            self.rating_scaler.fit(ratings)

            self.is_fitted = True
            logger.info(f"College recommender fitted with {len(colleges_data)} colleges")

        except Exception as e:
            logger.error(f"Error fitting recommender: {e}")
            self.is_fitted = False

    def calculate_similarity_scores(self, student_profile):
        """Calculate similarity scores between student and colleges"""
        if not self.is_fitted:
            return np.zeros(len(self.processed_colleges))

        scores = np.zeros(len(self.processed_colleges))

        try:
            # 1. Course similarity (40% weight)
            if student_profile.get('desired_course'):
                course_query = [student_profile['desired_course']]
                course_query_vec = self.course_vectorizer.transform(course_query)
                course_similarity = cosine_similarity(course_query_vec, self.course_features).flatten()
                scores += 0.4 * course_similarity

            # 2. Location similarity (25% weight)
            if student_profile.get('location_pref'):
                location_query = [student_profile['location_pref']]
                location_query_vec = self.location_vectorizer.transform(location_query)
                location_similarity = cosine_similarity(location_query_vec, self.location_features).flatten()
                scores += 0.25 * location_similarity

            # 3. Budget compatibility (15% weight)
            if student_profile.get('budget') and student_profile['budget'] > 0:
                budget = float(student_profile['budget'])
                fees = [[college['avg_fee']] for college in self.processed_colleges]
                scaled_fees = self.fee_scaler.transform(fees).flatten()
                scaled_budget = self.fee_scaler.transform([[budget]]).flatten()[0]

                fee_compatibility = 1 - np.abs(scaled_fees - scaled_budget)
                fee_compatibility = np.maximum(fee_compatibility, 0)
                scores += 0.15 * fee_compatibility

            # 4. Academic compatibility (20% weight)
            academic_score = self.calculate_academic_compatibility(student_profile)
            scores += 0.2 * academic_score

        except Exception as e:
            logger.error(f"Error calculating similarity scores: {e}")

        return scores

    def calculate_academic_compatibility(self, student_profile):
        """Calculate academic compatibility score"""
        academic_score = np.ones(len(self.processed_colleges)) * 0.5

        try:
            student_academic = student_profile.get('academic_profile', {})
            entrance_score = student_academic.get('entrance_score')

            if entrance_score:
                normalized_score = min(float(entrance_score) / 1000, 1.0)
                ratings = [[college['placement_rating']] for college in self.processed_colleges]
                placement_scores = self.rating_scaler.transform(ratings).flatten()
                academic_score = 0.7 * normalized_score + 0.3 * placement_scores

        except Exception as e:
            logger.error(f"Error calculating academic compatibility: {e}")

        return academic_score

    def recommend(self, student_profile, top_n=12):
        """Get top college recommendations for student"""
        if not self.is_fitted:
            logger.warning("Recommender not fitted, returning empty list")
            return []

        try:
            similarity_scores = self.calculate_similarity_scores(student_profile)
            top_indices = np.argsort(similarity_scores)[::-1][:top_n]

            recommendations = []
            for idx in top_indices:
                if similarity_scores[idx] > 0.1:  # Minimum threshold
                    college = self.processed_colleges[idx]['college_data'].copy()
                    match_score = round(similarity_scores[idx] * 100, 1)
                    college['match_score'] = match_score
                    college['match_percentage'] = f"{match_score}%"
                    recommendations.append(college)

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []


# Global instance
recommender = CollegeRecommender()