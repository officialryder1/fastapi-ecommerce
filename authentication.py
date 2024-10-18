from passlib.context import CryptContext
import jwt
from dotenv import dotenv_values
from models import User
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
config_credentials = dotenv_values(".env")

def get_hashed_password(password):
    return pwd_context.hash(password)

async def verify_token(token: str):
    try:
        payload = jwt.decode(token, config_credentials['SECRET'], algorithms="HS256")
        user = await User.get(id=payload.get('id'))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={'www.Authentication': "Bearer"}
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={'www.Authentication': "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={'www.Authentication': "Bearer"}
        )
    
    return user

async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(username: str, password: str):
    user = await User.get(username = username)

    if user and await verify_password(password, user.password):
        return user
    return False

async def token_generator(username: str, password: str):
    user = await authenticate_user(username, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password", headers={'www.Authentication': "Bearer"})
    
    token_data = {
        'user_id': user.id,
        'username': user.username
    }

    token = jwt.encode(token_data, config_credentials['SECRET'], algorithm='HS256')

    return token