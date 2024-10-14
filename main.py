from fastapi import FastAPI, Request, HTTPException, status, Depends
from tortoise.contrib.fastapi import register_tortoise
from models import *  # noqa: F403

# Authentication
from authentication import *  # noqa: F403
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)


# Signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import send_mail

# Response classes
from fastapi.responses import HTMLResponse

# template
from fastapi.templating import Jinja2Templates

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl ='/token') # This will redirect to a route call token fot verification

@app.post('/token')
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {
        'access_token': token,
        "token_type": "Bearer"
    }

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        pay_load = jwt.decode(token, config_credentials['SECRET'], algorithms=['HS256'])
        user = await User.get(id = pay_load.get('id'))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={'WWW-Authenticate': "Bearer"}
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={'www.Authentication': "Bearer"}
        )
    
    return await user
    

@app.post('/user_me')
async def user_login(user: user_pydanticIn = Depends(get_current_user)): # type: ignore
    business = await Business.get(owner = user)
    return {
        'status': 'ok',
        'data': {
            'username': user.username,
            'email': user.email,
            'is_verify': user.is_verified,
            'joined_date': user.joined_date
        }
    }

@post_save(User)
async def create_business(
    sender: "Type[User]",
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str]
) -> None:

    if created:
        business_obj =  await Business.create(
            name = instance.username,
            owner = instance
        )
        await business_pydantic.from_tortoise_orm(business_obj)
        # Send The email
        await send_mail({instance.email}, instance)


@app.post('/registration')
async def user_registration(user: user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = get_hashed_password(user_info['password'])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        'status': "ok",
        'data': f"Hello {new_user.username}, thanks for choosing our services. Please check your email inbox and click on the link to confirm your registration"
    }

templates = Jinja2Templates(directory='templates')
@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await verify_token(token)

    if user and not user.is_verified:
        user.is_verified=True
        await user.save()
        print(user.username)
        return  templates.TemplateResponse("verification.html", {"request": request, "username": user.username})
    
    raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={'www.Authentication': "Bearer"}
        )

@app.get('/')
async def index():
    return {"message": "Hello World"}


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules = {'models': ['models']},
    generate_schemas= True,
    add_exception_handlers=True,
)