This project is a backend REST API built with FastAPI for managing users and news content. It 

includes authentication, role-based authorization, and full CRUD operations for news articles.
The system is designed with simplicity, security, and scalability in mind.
Features
Authentication
User registration with email validation
Secure login using JWT tokens
Password hashing using bcrypt
Token expiration support (1 hour)
Authorization
Role-based access control
Regular users can read news
Admin users can create, update, and delete news
News Management
Create news articles (admin only)
Retrieve all news articles
Update existing news articles (admin only)
Delete news articles (admin only)
Tech Stack
FastAPI (backend framework)
SQLAlchemy (ORM)
Pydantic (data validation)
PyJWT (authentication)
bcrypt (password hashing)
Uvicorn / Gunicorn (server deployment)
Python-dotenv (environment management)
