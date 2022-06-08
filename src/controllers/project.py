from abc import ABC, abstractmethod
from typing import List
from beanie import PydanticObjectId
from beanie.operators import In, NotIn, AddToSet

from bson import ObjectId

from models.project import ProjectIn, ProjectModel
from config.db import db

from controllers.user import PyMongoUsersController
from models.user import UserModel

users_controller = PyMongoUsersController()


class ProjectsController(ABC):

    @abstractmethod
    async def get_project(self, id: str) -> ProjectModel:
        return NotImplementedError()

    @abstractmethod
    async def get_projects_by_ids(self, ids: List[str]) -> List[ProjectModel]:
        return NotImplementedError()

    @abstractmethod
    async def create_project(self, data: ProjectModel) -> None:
        return NotImplementedError()

    @abstractmethod
    async def delete_by_ids(self, ids: List[str]) -> None:
        return NotImplementedError()

    @abstractmethod
    async def update_project(self, id: str, data: ProjectModel) -> None:
        return NotImplementedError()

    @abstractmethod
    async def get_possible_invitees(self, id: str) -> List[str]:
        return NotImplementedError()

    @abstractmethod
    async def invite_to_project(self, id: str, invitees: List[str]) -> None:
        return NotImplementedError()

    @abstractmethod
    async def notify_all(self, id):
        return NotImplementedError()


class PyMongoProjectsController(ProjectsController):

    async def get_project(self, id: str) -> ProjectModel:
        project = await ProjectModel.get(ObjectId(id), fetch_links=True)
        return project

    async def get_projects_by_ids(self, ids: List[str]) -> List[ProjectModel]:
        return NotImplementedError()

    async def create_project(self, data: ProjectIn) -> None:
        print(data)
        admin = await UserModel.get(data.admin)
        assert admin is not None, f'Admin with id ({data.admin}) not found'

        members = await UserModel.find_many(In(UserModel.id, data.members)).to_list()

        project_values = data.dict()
        del project_values['admin']
        del project_values['members']
        print(project_values)

        project = ProjectModel(
            **project_values, invitees=[], admin=admin, members=members)
        await project.create()

    async def delete_by_ids(self, ids: List[str]) -> None:
        return NotImplementedError()

    # TODO Test
    async def update_project(self, id: PydanticObjectId, data: ProjectModel) -> None:
        return await ProjectModel.find_one({ProjectModel.id: ObjectId(id)}).update({"$set": dict(data)})

    async def get_possible_invitees(self, id: PydanticObjectId) -> List[UserModel]:
        project = await ProjectModel.find_one(ProjectModel.id == id, fetch_links=True)
        assert isinstance(project, ProjectModel)

        member_ids = [member.id for member in project.members]
        possible_invitees = await UserModel.find(
            NotIn(UserModel.id, member_ids)
        ).to_list()

        return possible_invitees

    async def invite_to_project(self, id: PydanticObjectId, invitees: List[UserModel]) -> None:
        await ProjectModel \
            .find(ProjectModel.id == id) \
            .update(AddToSet({
                ProjectModel.invitees: {
                    '$each': [invitee.to_ref() for invitee in invitees]}
            }))

    async def invite_by_email(self, id: PydanticObjectId, invitee_emails: List[str]) -> None:

        invitees = await UserModel.find({
            'email': {'$in': invitee_emails}
        }).to_list()

        await self.invite_to_project(id, invitees)

    # Observer method

    async def notify_all(self, u_id: str, project_id: str, *args):
        project = await self.get_project(project_id)
        member_ids = [str(member.id) for member in project.members]
        for i in member_ids:
            if str(i) != str(u_id):
                user_sending = await users_controller.get_user(u_id)
                desc = "{} {} se ha unido al proyecto {}".format(
                    str(user_sending.first_name), str(user_sending.last_name), str(project.title))
                print(desc)

                await users_controller.update_notifications(i, u_id, desc)
                
        print("Finished sending notifications")
