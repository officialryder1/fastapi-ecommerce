from fastapi import FastAPI, Request, HTTPException, status, Depends
from tortoise.contrib.fastapi import register_tortoise
from models import *  # noqa: F403
from crud import *

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

# Cors middleware
from fastapi.middleware.cors import CORSMiddleware

# template
from fastapi.templating import Jinja2Templates

# Image upload
from fastapi import File, UploadFile
import secrets # This is a inbuilt library that will be use to generate hex token to store image
from fastapi.staticfiles import StaticFiles
from PIL import Image


app = FastAPI()

#  Staticfile setup config
app.mount("/static", StaticFiles(directory='static'), name='static')

# Add session middleware to handle session


# List of allowed origins
origins = ["http://localhost:5173"] #List allowed origin during production

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials = True,
    allow_methods=['*'],
    allow_headers=['*'],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl ='/token') # This will redirect to a route call token fot verification

# 

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
    
    
@app.get('/user_me')
async def user_login(user_id: int): # type: ignore
    user = await User.get(id=user_id)
    
    return {
        'status': 'ok',
        'data': {
            'user_id': user.id,
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
async def user_registration(user: user_pydanticIn): # type: ignore
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = get_hashed_password(user_info['password'])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        'status': "ok",
        'data': f"Hello {new_user.username}, thanks for choosing our services. Please check your email inbox and click on the link to confirm your registration"
    }

@app.get('/resend_mail')
async def resend_mail(user_id: int):
    user = await User.get(id=user_id)
    print(user.email)
    await send_mail([user.email], user)

    return {
        'status': "ok",
        'data': f"Hello {user.username}, thanks for choosing our services. Please check your email inbox and click on the link to confirm your registration"
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


# Image Uploading
@app.post('/uploadfile/profile')
async def create_upload_file(file: UploadFile = File(...), user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/image/"
    filename = file.filename

    # We would use the secret in other to replace the initial image name to a secret hex so we don't get conflict when to image has the same name
    extension = filename.split(".")[1]

    if extension not in ['png', 'jpg', 'jpeg']:
        return {'status': "error", 'detail': "File extension not allowed"}
    
    token_name = secrets.token_hex(10) + '.' + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, 'wb') as file:
        file.write(file_content)

    # Pillow
    # Scaling image we dont want to store high resolution image in the backend
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    business = await Business.get(owner= user)
    owner = await business.owner

    if owner == user:
        business.logo = token_name
        await business.save()
        
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this account",
            headers={'www.Authentication': "Bearer"}
        )
    file_url = 'localhost:8000' + generated_name[1:]
    return {
            'status': "ok",
            'filename': file_url
        }

@app.post('/uploadfile/product/{id}')
async def create_upload_file(id: int, file: UploadFile = File(...), user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/image/"
    filename = file.filename

    # We would use the secret in other to replace the initial image name to a secret hex so we don't get conflict when to image has the same name
    extension = filename.split(".")[1]

    if extension not in ['png', 'jpg', 'jpeg']:
        return {'status': "error", 'detail': "File extension not allowed"}
    
    token_name = secrets.token_hex(10) + '.' + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, 'wb') as file:
        file.write(file_content)

    # Pillow
    # Scaling image we dont want to store high resolution image in the backend
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this account",
            headers={'www.Authentication': "Bearer"}
        )
    
    file_url = 'localhost:8000' + generated_name[1:]
    return {
            'status': "ok",
            'filename': file_url
        }

@app.get('/products')
async def get_all_product():
    return await get_product()

@app.post('/product')
async def Upload_product(product: product_pydanticIn, user: user_pydantic = Depends(get_current_user)): # type: ignore
    return await create_product(product, user)

@app.delete('/product/{product_id}')
async def remove_product(product_id: int, user: user_pydantic = Depends(get_current_user)): # type: ignore

    product = await Product.filter(id=product_id).first()
    if product:
        return await delete_product(product_id, user)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product with ID not found")

@app.put('/product/{product_id}')
async def update_prodduct_details(product_id: int, product: product_pydanticIn, user: user_pydantic = Depends(get_current_user)): # type: ignore
    return await update_product(product_id, product, user)




register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules = {'models': ['models']},
    generate_schemas= True,
    add_exception_handlers=True,
)