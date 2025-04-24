from markupsafe import Markup
from sqlalchemy import select
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware

from database.models import Company, Conversation
from itsdangerous import URLSafeSerializer
from dotenv import load_dotenv
import os



# Load environment variables
load_dotenv()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = "secret"  # 🔐 Replace with a secure key from env


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        self.serializer = URLSafeSerializer(secret_key)

    @property
    def middlewares(self):
        return [Middleware(SessionMiddleware, secret_key=self.serializer.secret_key)]

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({"token": self.serializer.dumps({"user": username})})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        try:
            self.serializer.loads(token)
            return True
        except Exception:
            return False


class CompanyAdmin(ModelView, model=Company):
    column_list = [
        Company.id,
        Company.name,
        Company.phone_number_id,
        Company.whatsapp_token,
        Company.verify_token,
        Company.ai_prompt,
        Company.language,
        Company.tone,
        Company.business_hours,
        Company.webhook_secret,
    ]

    can_create = True
    can_edit = True
    can_delete = True


class ConversationAdmin(ModelView, model=Conversation):
    column_list = [
        Conversation.id,
        Conversation.phone_number,
        Conversation.user_message,
        Conversation.ai_response,
        Conversation.timestamp,
        Conversation.company_id,
    ]
    can_create = True
    can_edit = True
    can_delete = True


admin_auth_backend = AdminAuth(secret_key=SECRET_KEY)

def setup_admin(app, engine):
    admin = Admin(app=app, engine=engine, authentication_backend=admin_auth_backend)
    admin.add_view(CompanyAdmin)
    admin.add_view(ConversationAdmin)