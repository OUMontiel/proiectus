
from beanie import PydanticObjectId
from beanie.operators import NotIn
from bson import ObjectId
from config.db import db
from fastapi import APIRouter, Response, status, Request, Cookie, Body
from models.project import ProjectIn, ProjectModel, ProjectOut
from models.user import UserModel, UserOut, UserTypeEnum
from schemas.project import projectEntity, projectsEntity
from starlette.status import HTTP_204_NO_CONTENT
from typing import List
from config.controllers import projects_controller, users_controller
from utils.auth import AuthHandler
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Union
from fastapi.templating import Jinja2Templates
from schemas.user import userEntity, usersEntity
from fastapi.encoders import jsonable_encoder


templates = Jinja2Templates(directory="templates")
project = APIRouter()
auth_handler = AuthHandler()


@project.get("/projects/create", response_class=HTMLResponse)
async def index(request: Request, token: Union[str, None] = Cookie(default=None)):
    possible_users = await UserModel\
        .find(NotIn(UserModel.id, [ObjectId(request.state.user.id)]), fetch_links=True)\
        .project(UserOut)\
        .to_list()

    # TODO Implement User GoToNewProject to Handle UserState
    return templates.TemplateResponse("createProject.html",
                                      {
                                          "request": request,
                                          "user": request.state.user,
                                          "possible_users": possible_users
                                      })

@project.get('/projects/{id}', response_class=HTMLResponse)
async def find_project(request: Request, id: PydanticObjectId):
    project = await projects_controller.get_project(id)

    return templates.TemplateResponse("project.html",
                                      {
                                          "request": request,
                                          "user": request.state.user,
                                          "project": project
                                      })

@project.get('/projects/{id}/createTask', response_class=HTMLResponse)
async def find_project(request: Request, id: PydanticObjectId):
    project = await projects_controller.get_project(id)

    return templates.TemplateResponse("createTask.html",
                                      {
                                          "request": request,
                                          "user": request.state.user,
                                          "project": project
                                      })

@project.post('/projects/create')
async def create_project(project: ProjectIn = Body(...)):
    await projects_controller.create_project(project)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content="Project created")


@project.post('/projects/invite/{id}')
async def invite_to_project(id: PydanticObjectId, invitees: List[str] = Body(...)):
    await projects_controller.invite_by_email(id, invitees)
    return Response(status_code=HTTP_204_NO_CONTENT)


@project.get('/projects/accept/{id}')
async def accept_invite(request: Request, id: PydanticObjectId):
    await users_controller.accept_project_invitation(request.state.user.id, id)
    await projects_controller.notify_all(request.state.user.id, id)
    return Response(status_code=HTTP_204_NO_CONTENT)


# TODO Verify that it works
@project.delete('/projects/{id}', status_code=status.HTTP_204_NO_CONTENT, tags=["projects"])
def delete_user(id: str):
    projectEntity(db.projects.find_one_and_delete({"_id": ObjectId(id)}))
    return Response(status_code=HTTP_204_NO_CONTENT)
