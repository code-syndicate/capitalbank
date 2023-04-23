from fastapi import Cookie, Response, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from models.settings import Settings
from typing import Optional
from lib.db import Collections, db
from models.users import AuthSession, UserDBModel


settings = Settings()


async def propagate_info(response:  Response, request:  Request, ):

    _info = request.cookies.get("info", "")

    response.set_cookie("info", _info)


async def get_msgs(request:  Request, ):

    _info = request.cookies.get("info", None)

    if _info:
        return _info.split(":")

    return []


async def get_session_user(response:  Response, request:  Request,  session_key: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name)):
    msg = ""

    if session_key is None:
        msg = "Sign in required."
        return None

    session_db = await db[Collections.sessions].find_one({"uid": session_key})

    if not session_db:
        msg = "Unauthorized, please sign in."

        return None

    session = AuthSession(**session_db)

    if not session.is_valid:
        msg = "Authorization expired, please sign in."

        return None

    user_db = await db[Collections.users].find_one({"uid": session.user_id})

    if not user_db:
        msg = "Authorization not found, please sign in."

    if msg:
        _info = request.cookies.get("info", "")

        _info += f":{msg}"

        response.set_cookie("info", _info)

        response.set_cookie("info", response)

    async def sign_out():
        await db[Collections.sessions].update_one({"uid": session_key}, {"$set": {"is_valid": False}})

    return UserDBModel(**user_db), sign_out


def enforce_is_admin(auth=Depends(get_session_user)):

    if auth is None:
        return None

    user, _ = auth

    if not user.is_superuser:
        raise HTTPException(401, "Unauthorized.")
    
    return auth
