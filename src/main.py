
from config.db import db
from config.controllers import users_controller
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models.user import UserIn, StudentCreator, ProfessorCreator, UserTypeEnum, LoggedInState
from mongoengine import connect, get_db
from routes.user import user
from routes.project import project
from routes.notification import notification
from schemas.user import userEntity
from models.user import PlaceHolderUser, LoggedOutState
from utils.auth import AuthHandler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

load_dotenv('.env')

app = FastAPI()
auth_handler = AuthHandler()

# TODO (Alam) Verificar si hacer la conexión aquí es seguro
# connection = connect(host=os.environ['MONGODB_URI'])

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# @app.on_event("startup")
# async def create_db_client():
#     # Prueba de conexión a Mongo
#     print(get_db())
#     return


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.json()
    print(body)
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Default factory
    factory = StudentCreator()

    token = request.cookies.get('token')
    is_logged_in = await auth_handler.auth_is_logged_in(db, token)
    if not is_logged_in:
        request.state.user = PlaceHolderUser()
        return await call_next(request)

    if is_logged_in["user_type"] == UserTypeEnum.professor:
        factory = ProfessorCreator()

    user = factory.createUser(userEntity(is_logged_in))
    user.transition_to(LoggedInState)
    request.state.user = user

    return await call_next(request)

app.include_router(user)
app.include_router(project)
app.include_router(notification)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = request.state.user
    return user.goToHome(request)


@app.get("/register", response_class=HTMLResponse)
async def index(request: Request):
    user = request.state.user
    return user.goToRegister(request)


@app.get("/dashboard", response_class=HTMLResponse)
async def index(request: Request):
    user = request.state.user
    context = {}
    if user._state != LoggedOutState:
        context['project_invitations'] = users_controller.get_project_invitations(
            user.id)
        context['project_membeships'] = users_controller.get_project_memberships(
            user.id)
        context['user_notifications'] = users_controller.get_user_notifications(
            user.id)
    return user.goToDashboard(request, context)

'''
@app.get("/example/{id}", response_class=HTMLResponse)
def example(request: Request, id: str):
    return templates.TemplateResponse("example.html", {"request": request, "id": id})
'''
