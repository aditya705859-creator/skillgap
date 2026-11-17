"""
Seed the demo user and sample analyses.
"""
import json
import datetime
import bcrypt
from app.db import SessionLocal
from app.models import User, Analysis


def seed_demo_user():
    """Create demo user with 3 past analyses if not exists."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "demo@skillgap.app").first()
        if existing:
            return
        
        # Create demo user
        pw_hash = bcrypt.hashpw("Demo@1234".encode(), bcrypt.gensalt()).decode()
        demo = User(
            name="Alex Demo",
            email="demo@skillgap.app",
            password_hash=pw_hash,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=30),
        )
        db.add(demo)
        db.flush()
        
        # Sample analyses
        analyses_data = [
            {
                "target_role": "Data Scientist",
                "resume_filename": "alex_demo_resume.pdf",
                "resume_text": "Experienced data analyst with 2 years of experience in Python, SQL, and data visualization. Proficient in pandas, numpy, matplotlib, and scikit-learn. Built predictive models using logistic regression and random forest. Created dashboards using Tableau. Bachelor's degree in Statistics.",
                "jd_text": "We are looking for a Data Scientist with strong skills in Python, SQL, Machine Learning, Deep Learning, Statistics, and data visualization. Experience with TensorFlow or PyTorch required. Must have experience with A/B testing and experimental design. Preferred: cloud platforms (AWS/GCP), Spark, and PhD in quantitative field.",
                "score": 62.5,
                "grade": "C",
                "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=21),
                "results_json": {
                    "matched_skills": [
                        {"name": "Python", "confidence": 0.95, "category": "Programming", "evidence": "Experienced data analyst with 2 years of experience in Python"},
                        {"name": "SQL", "confidence": 0.9, "category": "Database", "evidence": "experience in Python, SQL, and data visualization"},
                        {"name": "Pandas", "confidence": 0.95, "category": "Data Science", "evidence": "Proficient in pandas, numpy, matplotlib"},
                        {"name": "NumPy", "confidence": 0.95, "category": "Data Science", "evidence": "Proficient in pandas, numpy, matplotlib"},
                        {"name": "Matplotlib", "confidence": 0.9, "category": "Visualization", "evidence": "Proficient in pandas, numpy, matplotlib"},
                        {"name": "scikit-learn", "confidence": 0.95, "category": "Machine Learning", "evidence": "pandas, numpy, matplotlib, and scikit-learn"},
                        {"name": "Tableau", "confidence": 0.9, "category": "Visualization", "evidence": "Created dashboards using Tableau"},
                        {"name": "Statistics", "confidence": 0.85, "category": "Statistics", "evidence": "Bachelor's degree in Statistics"},
                        {"name": "Logistic Regression", "confidence": 0.9, "category": "Machine Learning", "evidence": "predictive models using logistic regression"},
                        {"name": "Random Forest", "confidence": 0.9, "category": "Machine Learning", "evidence": "logistic regression and random forest"},
                    ],
                    "partial_skills": [
                        {"name": "Machine Learning", "confidence": 0.6, "similarity": 0.72, "category": "Machine Learning", "evidence": "Built predictive models using logistic regression and random forest", "related_to": "scikit-learn"},
                        {"name": "Data Visualization", "confidence": 0.5, "similarity": 0.68, "category": "Visualization", "evidence": "experience in Python, SQL, and data visualization", "related_to": "Matplotlib"},
                    ],
                    "missing_skills": [
                        {"name": "Deep Learning", "category": "Deep Learning", "importance": "required"},
                        {"name": "TensorFlow", "category": "Deep Learning", "importance": "required"},
                        {"name": "PyTorch", "category": "Deep Learning", "importance": "required"},
                        {"name": "A/B Testing", "category": "Statistics", "importance": "required"},
                        {"name": "AWS", "category": "Cloud", "importance": "preferred"},
                        {"name": "GCP", "category": "Cloud", "importance": "preferred"},
                        {"name": "Spark", "category": "Big Data", "importance": "preferred"},
                    ],
                    "score_breakdown": {
                        "exact_match": 45.0,
                        "partial_match": 12.0,
                        "category_coverage": 3.5,
                        "resume_quality": 2.0,
                        "total": 62.5
                    },
                    "category_scores": {
                        "Programming": 0.9,
                        "Database": 0.8,
                        "Machine Learning": 0.5,
                        "Deep Learning": 0.0,
                        "Statistics": 0.4,
                        "Visualization": 0.7,
                        "Cloud": 0.0,
                        "Big Data": 0.0,
                        "Data Science": 0.8,
                    },
                    "top_roles": [
                        {"role": "Data Analyst", "score": 85.2},
                        {"role": "Business Intelligence Analyst", "score": 72.1},
                        {"role": "Data Scientist", "score": 62.5},
                        {"role": "Analytics Engineer", "score": 55.3},
                        {"role": "ML Engineer", "score": 42.8},
                    ],
                    "roadmap": [
                        {"skill": "Statistics", "hours": 30, "difficulty": "intermediate", "project": "A/B Test Analysis Dashboard"},
                        {"skill": "A/B Testing", "hours": 20, "difficulty": "intermediate", "project": "E-commerce Experiment Design"},
                        {"skill": "Deep Learning", "hours": 60, "difficulty": "advanced", "project": "Image Classification with CNNs"},
                        {"skill": "TensorFlow", "hours": 40, "difficulty": "advanced", "project": "Neural Network from Scratch"},
                        {"skill": "AWS", "hours": 30, "difficulty": "intermediate", "project": "Deploy ML Model on SageMaker"},
                    ],
                    "jd_skill_count": 12,
                    "resume_word_count": 52,
                },
            },
            {
                "target_role": "ML Engineer",
                "resume_filename": "alex_demo_resume_v2.pdf",
                "resume_text": "Data scientist with expertise in Python, SQL, Machine Learning, and Deep Learning. Experienced with TensorFlow, Keras, scikit-learn, and pandas. Built and deployed ML models using Docker and AWS SageMaker. Familiar with MLOps practices, CI/CD pipelines, and Git version control. Experience with A/B testing and statistical analysis. Master's in Computer Science.",
                "jd_text": "ML Engineer role requiring Python, Machine Learning, Deep Learning, TensorFlow, PyTorch, Docker, Kubernetes, AWS, CI/CD, Git, SQL. Must have experience deploying models to production. Preferred: MLOps, Airflow, Spark, Scala.",
                "score": 74.8,
                "grade": "B",
                "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=10),
                "results_json": {
                    "matched_skills": [
                        {"name": "Python", "confidence": 0.95, "category": "Programming", "evidence": "Data scientist with expertise in Python"},
                        {"name": "SQL", "confidence": 0.9, "category": "Database", "evidence": "expertise in Python, SQL, Machine Learning"},
                        {"name": "Machine Learning", "confidence": 0.95, "category": "Machine Learning", "evidence": "expertise in Python, SQL, Machine Learning, and Deep Learning"},
                        {"name": "Deep Learning", "confidence": 0.95, "category": "Deep Learning", "evidence": "Machine Learning, and Deep Learning"},
                        {"name": "TensorFlow", "confidence": 0.95, "category": "Deep Learning", "evidence": "Experienced with TensorFlow, Keras"},
                        {"name": "Docker", "confidence": 0.9, "category": "DevOps", "evidence": "deployed ML models using Docker"},
                        {"name": "AWS", "confidence": 0.9, "category": "Cloud", "evidence": "Docker and AWS SageMaker"},
                        {"name": "CI/CD", "confidence": 0.85, "category": "DevOps", "evidence": "CI/CD pipelines, and Git"},
                        {"name": "Git", "confidence": 0.9, "category": "DevOps", "evidence": "CI/CD pipelines, and Git version control"},
                        {"name": "scikit-learn", "confidence": 0.95, "category": "Machine Learning", "evidence": "scikit-learn, and pandas"},
                    ],
                    "partial_skills": [
                        {"name": "Kubernetes", "confidence": 0.4, "similarity": 0.55, "category": "DevOps", "evidence": "deployed ML models using Docker and AWS", "related_to": "Docker"},
                        {"name": "MLOps", "confidence": 0.5, "similarity": 0.62, "category": "DevOps", "evidence": "Familiar with MLOps practices", "related_to": "CI/CD"},
                    ],
                    "missing_skills": [
                        {"name": "PyTorch", "category": "Deep Learning", "importance": "required"},
                        {"name": "Kubernetes", "category": "DevOps", "importance": "required"},
                        {"name": "Airflow", "category": "DevOps", "importance": "preferred"},
                        {"name": "Spark", "category": "Big Data", "importance": "preferred"},
                        {"name": "Scala", "category": "Programming", "importance": "preferred"},
                    ],
                    "score_breakdown": {
                        "exact_match": 52.0,
                        "partial_match": 10.8,
                        "category_coverage": 7.0,
                        "resume_quality": 5.0,
                        "total": 74.8
                    },
                    "category_scores": {
                        "Programming": 0.9,
                        "Database": 0.8,
                        "Machine Learning": 0.9,
                        "Deep Learning": 0.7,
                        "DevOps": 0.6,
                        "Cloud": 0.5,
                        "Big Data": 0.0,
                        "Data Science": 0.7,
                    },
                    "top_roles": [
                        {"role": "ML Engineer", "score": 74.8},
                        {"role": "Data Scientist", "score": 72.3},
                        {"role": "MLOps Engineer", "score": 65.1},
                        {"role": "Data Engineer", "score": 55.9},
                        {"role": "Deep Learning Engineer", "score": 52.4},
                    ],
                    "roadmap": [
                        {"skill": "PyTorch", "hours": 40, "difficulty": "advanced", "project": "Build a GAN with PyTorch"},
                        {"skill": "Kubernetes", "hours": 30, "difficulty": "intermediate", "project": "Deploy ML API on K8s"},
                        {"skill": "Spark", "hours": 35, "difficulty": "intermediate", "project": "Distributed Data Pipeline"},
                        {"skill": "Airflow", "hours": 25, "difficulty": "intermediate", "project": "ML Pipeline Orchestration"},
                    ],
                    "jd_skill_count": 14,
                    "resume_word_count": 68,
                },
            },
            {
                "target_role": "Data Engineer",
                "resume_filename": "alex_demo_resume_v3.pdf",
                "resume_text": "Software engineer transitioning to data engineering. Strong in Python, SQL, PostgreSQL, and Linux. Experience with Docker, Git, CI/CD, and AWS. Built ETL pipelines using Python and SQL. Familiar with Airflow and dbt. Some experience with Spark and Kafka. Bachelor's in Computer Engineering.",
                "jd_text": "Data Engineer needed with expertise in Python, SQL, Spark, Kafka, Airflow, dbt, AWS, Docker, Kubernetes, PostgreSQL, Snowflake. Must have experience building data pipelines. Preferred: Scala, Databricks, Terraform.",
                "score": 71.2,
                "grade": "B",
                "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=3),
                "results_json": {
                    "matched_skills": [
                        {"name": "Python", "confidence": 0.95, "category": "Programming", "evidence": "Strong in Python, SQL, PostgreSQL"},
                        {"name": "SQL", "confidence": 0.95, "category": "Database", "evidence": "Strong in Python, SQL, PostgreSQL"},
                        {"name": "PostgreSQL", "confidence": 0.95, "category": "Database", "evidence": "Strong in Python, SQL, PostgreSQL, and Linux"},
                        {"name": "Docker", "confidence": 0.9, "category": "DevOps", "evidence": "Experience with Docker, Git, CI/CD"},
                        {"name": "Git", "confidence": 0.9, "category": "DevOps", "evidence": "Experience with Docker, Git, CI/CD"},
                        {"name": "AWS", "confidence": 0.9, "category": "Cloud", "evidence": "CI/CD, and AWS"},
                        {"name": "Airflow", "confidence": 0.8, "category": "DevOps", "evidence": "Familiar with Airflow and dbt"},
                        {"name": "dbt", "confidence": 0.8, "category": "Data Science", "evidence": "Familiar with Airflow and dbt"},
                        {"name": "Linux", "confidence": 0.9, "category": "DevOps", "evidence": "PostgreSQL, and Linux"},
                    ],
                    "partial_skills": [
                        {"name": "Spark", "confidence": 0.5, "similarity": 0.58, "category": "Big Data", "evidence": "Some experience with Spark and Kafka", "related_to": "Python"},
                        {"name": "Kafka", "confidence": 0.5, "similarity": 0.55, "category": "Big Data", "evidence": "Some experience with Spark and Kafka", "related_to": "Data Engineering"},
                    ],
                    "missing_skills": [
                        {"name": "Kubernetes", "category": "DevOps", "importance": "required"},
                        {"name": "Snowflake", "category": "Database", "importance": "required"},
                        {"name": "Scala", "category": "Programming", "importance": "preferred"},
                        {"name": "Databricks", "category": "Big Data", "importance": "preferred"},
                    ],
                    "score_breakdown": {
                        "exact_match": 48.0,
                        "partial_match": 10.2,
                        "category_coverage": 7.0,
                        "resume_quality": 6.0,
                        "total": 71.2
                    },
                    "category_scores": {
                        "Programming": 0.9,
                        "Database": 0.9,
                        "DevOps": 0.7,
                        "Cloud": 0.5,
                        "Big Data": 0.3,
                        "Data Science": 0.4,
                    },
                    "top_roles": [
                        {"role": "Data Engineer", "score": 71.2},
                        {"role": "Backend Developer", "score": 68.5},
                        {"role": "DevOps Engineer", "score": 62.3},
                        {"role": "Site Reliability Engineer", "score": 55.8},
                        {"role": "Software Engineer", "score": 54.1},
                    ],
                    "roadmap": [
                        {"skill": "Spark", "hours": 35, "difficulty": "intermediate", "project": "Distributed Data Pipeline with PySpark"},
                        {"skill": "Kafka", "hours": 25, "difficulty": "intermediate", "project": "Real-time Streaming Pipeline"},
                        {"skill": "Kubernetes", "hours": 30, "difficulty": "intermediate", "project": "Container Orchestration Lab"},
                        {"skill": "Snowflake", "hours": 20, "difficulty": "intermediate", "project": "Cloud Data Warehouse Setup"},
                    ],
                    "jd_skill_count": 13,
                    "resume_word_count": 61,
                },
            },
        ]
        
        for a_data in analyses_data:
            analysis = Analysis(
                user_id=demo.id,
                target_role=a_data["target_role"],
                resume_filename=a_data["resume_filename"],
                resume_text=a_data["resume_text"],
                jd_text=a_data["jd_text"],
                results_json=a_data["results_json"],
                score=a_data["score"],
                grade=a_data["grade"],
                created_at=a_data["created_at"],
            )
            db.add(analysis)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
    finally:
        db.close()
