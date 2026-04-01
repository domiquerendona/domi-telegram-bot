try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from web.api.admin import router as admin_router
from web.api.auth import router as auth_router
from web.api.dashboard import router as dashboard_router
from web.api.users import router as users_router
from web.api.form import router as form_router


load_dotenv()

from db import init_db, ensure_web_admin
init_db()
ensure_web_admin()

app = FastAPI()

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(form_router)

origins = [
    "http://localhost:4200",
    "https://angular-production-44c8.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Domi App</title>
        </head>
        <body>
            <h1>Panel Web Domi 🚀</h1>
            <p>Backend funcionando correctamente.</p>
        </body>
    </html>
    """
