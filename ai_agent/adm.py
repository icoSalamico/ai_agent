from markupsafe import Markup
from sqlalchemy import select
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware

from database.models import Company, Conversation, ZApiInstance  # ✅ ADICIONAR AQUI
from itsdangerous import URLSafeSerializer  # type: ignore
from dotenv import load_dotenv  # type: ignore
import os

# Load environment variables
load_dotenv()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = "secret"  # 🔐 Replace with a secure key from env

# --- Authentication Setup ---
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

# --- Company Admin View ---
class CompanyAdmin(ModelView, model=Company):
    column_list = [
        Company.id,
        Company.name,
        Company.provider,
        Company.display_number,
        Company.phone_number_id,
        Company.language,
        Company.tone,
        Company.business_hours,
        Company.ai_prompt,
        Company.verify_token,
        Company.whatsapp_token,
        Company.webhook_secret,
        Company.zapi_instance_id,
        Company.zapi_token,
        Company.active,
    ]
    column_searchable_list = [Company.name, Company.display_number, Company.phone_number_id]
    column_filters = [Company.provider]
    can_create = True
    can_edit = True
    can_delete = True

# --- Conversation Admin View ---
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

# ✅ --- ZApiInstance Admin View ---
class ZApiInstanceAdmin(ModelView, model=ZApiInstance):
    column_list = [
        ZApiInstance.id,
        ZApiInstance.instance_id,
        ZApiInstance.token,
        ZApiInstance.assigned,
        ZApiInstance.company_id,
    ]
    column_searchable_list = [ZApiInstance.instance_id]
    column_filters = [ZApiInstance.assigned]
    can_create = True
    can_edit = True
    can_delete = True

# --- Admin setup ---
admin_auth_backend = AdminAuth(secret_key=SECRET_KEY)

def setup_admin(app, engine):
    admin = Admin(app=app, engine=engine, authentication_backend=admin_auth_backend)
    admin.add_view(CompanyAdmin)
    admin.add_view(ConversationAdmin)
    admin.add_view(ZApiInstanceAdmin)  # ✅ ADICIONAR AQUI
