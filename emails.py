import requests
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from dotenv import dotenv_values
import requests.api
from models import User
import jwt
from datetime import datetime, timedelta

from typing import List


config_credentials = dotenv_values(".env")

conf = ConnectionConfig(
    MAIL_USERNAME = config_credentials['EMAIL'],
    MAIL_PASSWORD = config_credentials['PASSWORD'],
    MAIL_FROM = config_credentials['EMAIL'],
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.mailersend.net",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
)


async def send_mail(email: List[str], instance: User):
    
    token_data = {
        "id": instance.id,
        "username": instance.username,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    token = jwt.encode(token_data,config_credentials['SECRET'], algorithm="HS256")

    print(token)
    template = f"""
        <!DOCTYPE html>
        <html>
            <head>
            </head>
            <body>
                <div style= "display: flex; align-items: center; justify-content: center; flex-direction: column;">
                    <h3> Account Verification</h3>
                    <br>

                    <p> Thanks for choosing our store, please click on the button below to verify your account</p>
                    <a style="margin-top: 1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration:none;
                     background: #0275d8; color: white;" href="http://127.0.0.1:8000/verification/?token={token}">Verify your email</a>

                    <p> Please kindly ignore if already verified or didn't register for our store. </p>
                </div>
            </body>
        </html>
    """

    message = MessageSchema(
        subject="Sweet store verification email",
        recipients=email,
        body = template,
        subtype= MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message=message)

 
