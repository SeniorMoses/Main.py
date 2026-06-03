from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel, EmailStr, Field 
from datetime import datetime, timezone, timedelta
import jwt
from fastapi.concurrency import run_in_threadpool
import bcrypt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from pathlib import Path
from dotenv import load_dotenv
import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, Integer, String 
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey, Text
from typing import Optional 

env_path = Path('.env')
load_dotenv(env_path)

Base = declarative_base() 
dburl = os.getenv("DBURL")
engine = create_engine(dburl)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Signup(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)

class NewsContent(BaseModel): 
    title: str
    content: str
  
class UpdateNews(BaseModel):
    id: int
    new_title: Optional[str] = None 
    new_content: Optional[str] = None 

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False, default='user') 
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)

class News(Base):
    __tablename__ = "news"
    date = Column(Text, default=lambda: datetime.now(timezone.utc).isoformat())  
    id = Column(Integer, primary_key=True, index=True) 
    user_id = Column(Integer, ForeignKey("users.id")) 
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False) 

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db 
    except Exception as e: 
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Database error : {str(e)}'
        ) 
    finally:
        db.close()

SECRET = os.getenv('SECRET_KEY')

def create_token(user):
    token = jwt.encode(
        {
            'sub': str(user.id), 
            'username': user.username,
            'role': user.role, 
            'exp': datetime.now(timezone.utc) + timedelta(hours=1)
        },
        SECRET,
        algorithm='HS256'
    ) 
    return token 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def get_user(token: str = Depends(oauth2_scheme)):
    try:
        data = jwt.decode(token, SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='token expired')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='invalid token')
    return data

app = FastAPI()

@app.get('/')
def message():
    return {'message': 'fastapi server is running'}

@app.post('/signup')
async def register(data: Signup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail='email already exist, please login'
        )

    hashed = await run_in_threadpool(
        bcrypt.hashpw,
        data.password.encode(),
        bcrypt.gensalt()
    )
    hashed_password = hashed.decode() 

    new_user = User(
        username=data.username,
        email=data.email,
        password=hashed_password
    ) 

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Database error: {str(e)}'
        )

    return {'message': 'signup successfully'}  

@app.post('/login')
async def signin(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)): 
    user = db.query(User).filter(User.email == data.username).first() 
    if not user:
        raise HTTPException(status_code=401, detail='invalid credentials')

    is_valid = await run_in_threadpool(
        bcrypt.checkpw,
        data.password.encode(), 
        user.password.encode()  
    )

    if not is_valid:
        raise HTTPException(status_code=401, detail='invalid credentials')

    token = create_token(user)

    return {
        'access_token': token,
        'token_type': 'bearer',
        'message': 'login successfully'
    } 

@app.post('/post_news')
async def post_news(data: NewsContent, user=Depends(get_user), db: Session = Depends(get_db)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail='you are not allowed to use this feature')

    new_content = News(
        title=data.title,
        content=data.content,
        user_id=int(user['sub'])   
    ) 

    try:
        db.add(new_content)
        db.commit()
        db.refresh(new_content) 
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"server error {str(e)}")

    return {'message': 'news posted successfully'}   

@app.get('/read')
async def read(db: Session = Depends(get_db), user=Depends(get_user)):
    news = db.query(News).all() 
    return news 

@app.put('/news')
async def update_news(data: UpdateNews, user=Depends(get_user), db: Session = Depends(get_db)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail='You are not allowed to use this feature')

    found = db.query(News).filter(News.id == data.id).first()
    if not found:
        raise HTTPException(status_code=404, detail='Post Not Found')

    if data.new_title is not None:
        found.title = data.new_title
    if data.new_content is not None:
        found.content = data.new_content

    db.commit()
    db.refresh(found) 
    return {'message': 'news updated'} 
    
@app.delete('/delete/{id}')
async def delete(id:int, user=Depends(get_user), db:Session=Depends(get_db)):
    if user['role'] !='admin':
        raise HTTPException (
        status_code=403,
        detail='You are not allowed to use this feature'
        )
    found=db.query(News).filter(News.id==id).first() 
    if not found:
            raise HTTPException (
            status_code=404,
            detail='News not found'
            )
    try: 
           db.delete(found)
           db.commit()
           return {'message':'news deleted successfully'}
    except Exception as e:   
            db.rollback()
            raise HTTPException (
            status_code=500,
            detail=f'database error: {str(e)}' 
            )
    
    