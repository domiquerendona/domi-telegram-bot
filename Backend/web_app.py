from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Convierte cualquier excepción no capturada en JSON 500 con CORS headers.
    Sin esto, los errores llegan al navegador como text/plain sin CORS headers
    y Angular los ve como status 0 ('Error 0: sin conexión').
    """
    import logging
    logging.getLogger("web_app").error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


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
