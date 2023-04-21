from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends
from typing import Union
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models.settings import Settings
from models.users import AuthSession, RequestAccessTokenInput, UserInputModel, UserDBModel
from lib.db import Collections, db
from lib.utils import hash_password
from lib.dependencies import get_session_user, propagate_info, get_msgs

settings = Settings()

templates = Jinja2Templates(directory="templates",  autoescape=True,)

router = APIRouter(
    tags=["Generic endpoints"]
)


@router.get("/", tags=["Home"], response_class=HTMLResponse)
async def index(request: Request):

    return RedirectResponse("/sign-in")

    # return templates.TemplateResponse("index.html", {"settings": settings, "request": request})


@router.get("/apps/dashboard", tags=["Dashboard"], response_class=HTMLResponse)
async def dashboard(request: Request, auth:  UserDBModel = Depends(get_session_user), tab: Union[str, None] = Query(alias="tab", default="dash"), msgs:  list[str] = Depends(get_msgs)):
    print(msgs)

    if not auth:
        return RedirectResponse("/sign-in")

    user,  _ = auth

    views = ["dash", "transfer", "transfers",
             "transactions", "profile", "settings"]

    if not tab.lower() in views:
        tab = views[0]

    return templates.TemplateResponse("dashboard.html", {"settings": settings, "request": request, "user": user, "tab": tab})


@router.get("/sign-out", tags=["Sign out"], )
async def sign_out(auth:  UserDBModel = Depends(get_session_user)):
    if not auth:
        return RedirectResponse("/sign-in")

    _, log_out = auth

    await log_out()

    return RedirectResponse("/")


@router.get("/sign-in", tags=["Login"], response_class=HTMLResponse,)
async def signin(request:  Request, auth:  UserDBModel = Depends(get_session_user), msgs:  list[str] = Depends(get_msgs)):
    print(msgs)

    user, _ = auth if auth else (None, None)
    if user:
        return RedirectResponse("/apps/dashboard")

    return templates.TemplateResponse("signin.html", {"settings":  settings, "request":  request, "msgs":  msgs})


@router.post("/sign-in", tags=["Login"], )
async def signin_post(form:  RequestAccessTokenInput, response:  Response):

    existing_user_with_email = await db[Collections.users].find_one({"email": form.email})

    if not existing_user_with_email:
        raise HTTPException(404, "No matching account.")

    user = UserDBModel(**existing_user_with_email)
    guessed_password_hash = hash_password(form.password)

    if user.password_hash != guessed_password_hash:

        raise HTTPException(401, "Invalid account credentials.")

    new_session = AuthSession(
        user_id=user.uid, duration_in_hours=48
    )

    await db[Collections.sessions].insert_one(new_session.dict())

    response.set_cookie(settings.session_cookie_name, new_session.uid)

    return


@router.get("/sign-up", tags=["Signup"], response_class=HTMLResponse,)
async def signup(request: Request, auth:  UserDBModel = Depends(get_session_user)):

    if auth:
        _, log_out = auth

        await log_out()

    return templates.TemplateResponse("signup.html", {"settings":  settings, "request":  request})


@router.post("/sign-up", tags=["Signup"], )
async def signup_post(request: Request, form: UserInputModel):
    data = form.dict()

    if data["password"] != data["password2"]:
        raise HTTPException(status_code=400, detail="Passwords do not match!")

    data.update({
        "password_hash":  hash_password(form.password2),
    })

    user = UserDBModel(**data)

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
