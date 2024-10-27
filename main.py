from fastapi import FastAPI, Request, HTTPException, status, WebSocket,  WebSocketDisconnect, Depends
from tortoise.contrib.fastapi import register_tortoise
from models import *  
from crud import *
import replicate
import requests
from typing import List

# Authentication
from authentication import * 
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)


# Signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import send_mail
from pydantic import BaseModel

# Response classes
from fastapi.responses import HTMLResponse

# Cors middleware
from fastapi.middleware.cors import CORSMiddleware

# OAuth for social import
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# template
from fastapi.templating import Jinja2Templates

# Image upload
from fastapi import File, UploadFile
import secrets # This is a inbuilt library that will be use to generate hex token to store image
from fastapi.staticfiles import StaticFiles
from PIL import Image
import os




app = FastAPI()

replicate.Client(api_token=config_credentials['REPLICATE_API_TOKEN'])
#  Staticfiles setup config
app.mount("/static", StaticFiles(directory='static'), name='static')

# Add session middleware to handle session
# app.add_middleware(SessionMiddleware, secret_key=config_credentials['SECRET_KEY'])

# Paystack payment type hind model
class VerifyPayment(BaseModel):
    reference: str


connected_clients: List[WebSocket] = []
# config = Config('.env')

# oauth = OAuth(config)
# oauth.register(
#     name='google',
#     client_id= config_credentials['GOOGLE_CLIENT_ID'],
#     client_secret = config_credentials['GOOGLE_CLIENT_SECRET'],
#     authorize_url = 'https://accounts.google.com/o/oauth2/auth',
#     authorize_params = None,
#     access_token_url = 'https://accounts.google.com/o/oauth2/token',
#     access_token_params = None,
#     refresh_token_url = None,
#     client_kwargs={
#         'scope': 'openid email profile'
#     }

# )

# List of allowed origins
origins = [
    "http://localhost:5173",
    "http://localhost:8000"
] #List allowed origin during production

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials = True,
    allow_methods=['*'],
    allow_headers=['*'],
)

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
        
        payload = jwt.decode(token, config_credentials['SECRET'], algorithms="HS256", options={'verify_exp': True})

        user = await User.get(id=payload.get('user_id'))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={'WWW-Authenticate': "Bearer"}
            )
    except jwt.ExpiredSignatureError:
        print(f"token passed: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={'WWW-Authenticate': "Bearer"}
        )
    except jwt.InvalidTokenError:
        # Handle invalid token
        print(f"Invalid token: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={'WWW-Authenticate': "Bearer"}
        )
    except Exception as e:
        # Catch-all for any other exceptions and log for debugging
       
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
            headers={'WWW-Authenticate': "Bearer"}
        )
    return await user
    
    
@app.get('/user_me')
async def user_login(user_id: int): # type: ignore
    user = await User.get(id=user_id)
    
    return user

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

# # Redirect to Google Oauth 2.0 server to initiate the authentication
# @app.get('/auth/google')
# async def auth_google(request: Request):
#     redirect_url = config_credentials['GOOGLE_REDIRECT_URL']
    
#     print("State sent:", request.session.get('state'))  # Debugging
#     return await oauth.google.authorize_redirect(request, redirect_url)
#     # return await oauth.google.authorize_redirect(request, redirect_url)

# # This route handle callback from google
# @app.get("/auth/google/callback")
# async def google_callback(request: Request):
#     token = await oauth.google.authorize_access_token(request)
#     print("State received:", request.query_params.get('state')) 
#     user = await oauth.google.parse_id_token(request, token)

#     if not user:
#         raise HTTPException(status_code=400, detail="Invalid token")
    
#     return {
#         'email':user['email'],
#         'name': user['name']
#     }

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

    if extension not in ['png', 'jpg', 'jpeg', 'JPEG', 'PNG', 'JPG']:
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

    user_data = await user_pydantic.from_tortoise_orm(user)
    print(user_data)
    business = await Business.get(owner=user)
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

# CRUD
@app.get('/products')
async def get_all_product():
    return await get_products()

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

@app.get('/product/{product_id}')
async def retrieve_product(product_id: int):
    return await get_product(product_id)

@app.get('/product_by_owner')
async def retrieve_product_by_owner(user_id: int, user: user_pydantic = Depends(get_current_user)): # type: ignore
    return await retrieve_product_by_Business(user_id)

# AI Landing page generator

@app.post('/generate_landing_page')
async def generate_landing_page(request: Request):
    data = await request.json()
    main_message = data.get('main_message', 'welcome to our product')

    page_type = data.get('page_type', 'general')

    prompt=f"Generate a catchy headline for a {data['page_type']} landing page with the message: {main_message}"
    
    input_data = {
        'prompt': prompt,
        "max_token": 1024
    }

    # Stream the response from replicate model
    response_text = ""
    for event in replicate.stream(
        "meta/meta-liama-3.1-405b-instruct",
        input=input_data
    ):
        response_text += event

    return {
        "content": response_text,
        "main_message": main_message,
        "page_type": page_type
    }

# Retrieve Order
@app.post('/order')
async def create_order(order:order_pydanticIn,  product: int, user:user_pydantic = Depends(get_current_user)): # type: ignore
    return await add_order(order, product, user)

# Retrieve User order history
@app.get('/order-by-user')
async def retrieve_user_order(user: user_pydantic = Depends(get_current_user)):
    return await order_by_user(user)

# Retrive detail of your product order
@app.get('/order-by-owner')
async def retrieve_owner_product(user: user_pydantic = Depends(get_current_user)):
    return await order_to_owner(user)


# Payment
@app.post('/verify-transaction')
async def verify_transaction(payment: VerifyPayment):
    url= f"https://api.paystack.co/transaction/verify/{payment.reference}"
    headers = {
        "Authorization": f"Bearer {config_credentials['PUBLIC_TEST_SECRET_KEY']}",
        "Content-Type": "application/json"
    }

    # Send request to paystack to verify the transaction
    response = requests.get(url, headers=headers)
    response_data = response.json()

    if response_data['status'] == False:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    if response_data['data']['status'] == 'success':
        # Handle successful payment (e.g., update order status, grant access to product, etc.)
        return {"status": "success", "data": response_data['data']}
    else:
        # Handle failed payment
        raise HTTPException(status_code=400, detail="Payment not successful")
    

# Upload user shipping detail
@app.post('/upload-shipping')
async def upload_shipping(user_detail: user_detailIn_pydantic, user: user_pydantic = Depends(get_current_user)):

    return await upload_user_detail(user_detail, user)

@app.get('/shipping-detail')
async def retrieve_shipping(id: int):
    return await get_shipping(id)

@app.get('/retrieve_user_shipping')
async def retrieve_user_detail(user_id: int):
    return await get_shipping_by_user(user_id)

# Notification for owner
@app.websocket('/ws/notify')
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Keep connection open to listen for events
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# Function to broadcast notification to all connected client
async def notify_clients(order):
    for client in connected_clients:
        await client.send_json(order)


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules = {'models': ['models']},
    generate_schemas= True,
    add_exception_handlers=True,
)
