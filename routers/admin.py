from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends
from typing import Union
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models.settings import Settings
from models.users import AuthSession, ChangePasswordInput, RequestAccessTokenInput, TransferInput1, TxType, UserBaseModel, UserInputModel, UserDBModel, InFiatTransfer, OutFiatTransfer, TransferInput2
from lib.db import Collections, db
from lib.utils import hash_password
from lib.dependencies import get_session_user, propagate_info, get_msgs, enforce_is_admin

settings = Settings()

templates = Jinja2Templates(directory="templates",  autoescape=True,)

router = APIRouter(
    tags=["Admin endpoints"],

)


@router.get("/admin/neu", tags=["Signup"], response_class=HTMLResponse,)
async def create_new_user(request: Request):

    return templates.TemplateResponse("signup.html", {"settings":  settings, "request":  request})


@router.get("/admin/overview", response_class=HTMLResponse,)
async def overview(request: Request, auth:  UserDBModel = Depends(get_session_user), view: str = Query(alias="ui", default="main")):
    if not auth:
        return RedirectResponse("/sign-in")

    user, _ = auth

    views = ["main", "overview", "users",
             "transfers", "transactions", "settings"]

    if not view.lower() in views:
        view = views[0]

    return templates.TemplateResponse("admin/overview.html", {"settings":  settings, "ui": view,
                                                              "user": user, "request":  request})


@router.post("/sign-up", tags=["Signup"], )
async def signup_post(request: Request, form: UserInputModel):
    data = form.dict()

    if data["password"] != data["password2"]:
        raise HTTPException(status_code=400, detail="Passwords do not match!")

    data.update({
        "password_hash":  hash_password(form.password2),
    })

    user = UserDBModel(**data)
    user.is_superuser = form.is_admin

    existing_user_with_email = await db[Collections.users].find_one({"email": user.email})
    existing_user_with_phone = await db[Collections.users].find_one({"phone": user.phone})

    if existing_user_with_email:
        raise HTTPException(
            status_code=400, detail="Email address is registered to another account.")

    if existing_user_with_phone:
        raise HTTPException(
            status_code=400, detail="Phone number is registered to another account.")

    await db[Collections.users].insert_one(user.dict())

    return
