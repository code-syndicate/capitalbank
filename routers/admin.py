import datetime
import math
from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends, BackgroundTasks
from typing import Union
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models.settings import Settings
from models.users import DeleteUserModel, TickTxModel, TransferInput1, TxType, UpdateTxModel, UpdateUserModel, UserBaseModel, UserInputModel, UserDBModel, InFiatTransfer, OutFiatTransfer, TransferInput2, UserOTP
from lib.db import Collections, db
from lib.utils import hash_password
from lib.dependencies import get_session_user, propagate_info, get_msgs, enforce_is_admin
from lib.emails.send_mail import dispatch_email

settings = Settings()

templates = Jinja2Templates(directory="templates",  autoescape=True,)

router = APIRouter(
    tags=["Admin endpoints"],

)


@router.get("/admin/neu", tags=["Signup"], response_class=HTMLResponse,)
async def create_new_user(request: Request):

    return templates.TemplateResponse("signup.html", {"settings":  settings, "request":  request})


@router.post("/admin/update-user")
async def update_user_data(form: UpdateUserModel, auth:  UserDBModel = Depends(enforce_is_admin)):
    data = form.dict()

    user, _ = auth

    # get a user
    p_user = await db[Collections.users].find_one({"uid": form.uid})

    p_user.update(data)

    updated_user = UserDBModel(**p_user)

    await db[Collections.users].update_one({"uid": form.uid}, {"$set": updated_user.dict()})


@router.post("/admin/delete-user")
async def delete_user(form: DeleteUserModel, auth:  UserDBModel = Depends(enforce_is_admin)):

    user, _ = auth

    # delete user
    await db[Collections.users].delete_one({"email": form.email})


@router.post("/admin/otps/{uid}")
async def add_otp(uid: str, auth:  UserDBModel = Depends(enforce_is_admin)):

    my_user = await db[Collections.users].find_one({"uid": uid})

    if my_user is None:
        raise HTTPException(401, "User not found")

    new_otp = UserOTP(user=my_user["email"])

    await db[Collections.otps].insert_one(new_otp.dict())

    return new_otp


@router.get("/admin/otps/{uid}")
async def get_otp(uid: str, auth:  UserDBModel = Depends(enforce_is_admin)):

    my_user = await db[Collections.users].find_one({"uid": uid})

    if my_user is None:
        raise HTTPException(401, "User not found")

    otps = await db[Collections.otps].find({"user": my_user["email"], "is_valid": True}).to_list(length=None)
    _l = []
    for p in otps:
        _l.append({
            "otp": p["otp"],
            "is_valid": p["is_valid"]
        })

    return _l


@router.post("/admin/delete-tx")
async def delete_tx(form: TickTxModel, auth:  UserDBModel = Depends(enforce_is_admin)):

    user, _ = auth

    await db[Collections.transfers].delete_one({"tx_id": form.tx_id})


@router.post("/admin/tick-tx")
async def tick_tx(form: TickTxModel, auth:  UserDBModel = Depends(enforce_is_admin)):

    user, _ = auth

    tx = await db[Collections.transfers].find_one({"tx_id": form.tx_id})

    if tx is None:
        raise HTTPException(401, "Record not found")

    await db[Collections.transfers].update_one({"tx_id": form.tx_id}, {"$set":  {"approved": True, "status": "SUCCESS"}})


@router.post("/admin/untick-tx")
async def tick_tx(form: TickTxModel, bg_task:  BackgroundTasks, auth:  UserDBModel = Depends(enforce_is_admin)):

    user, _ = auth

    tx = await db[Collections.transfers].find_one({"tx_id": form.tx_id})

    if tx is None:
        raise HTTPException(401, "Record not found")

    u = await db[Collections.users].find_one({"email": tx["sender"]})

    await db[Collections.users].update_one({"email": tx["sender"]}, {"$set":  {"balance": u["balance"] + tx["amount"]}})

    await db[Collections.transfers].update_one({"tx_id": form.tx_id}, {"$set":  {"approved": False, "status": "FAILED"}})

    dispatch_email(bg_task, user.email, "transfer_failed", {
        "amount": tx["amount"],
        "receiver": tx.get("receiver",  tx.get("receiver_account_name", "..."),),
    })


@router.post("/admin/update-tx")
async def update_tx(form: UpdateTxModel, auth:  UserDBModel = Depends(enforce_is_admin)):

    user, _ = auth

    tx = await db[Collections.transfers].find_one({"tx_id": form.tx_id})
    print(form.dict())
    update = form.dict(exclude_unset=True, exclude_none=True, )

    if form.created:
        ts = datetime.datetime.fromisoformat(
            form.created).timestamp()

        update.update({"created": ts})

    else:
        update = form.dict(exclude={"created", })

    tx.update(update)

    if tx is None:
        raise HTTPException(401, "Record not found")

    await db[Collections.transfers].update_one({"tx_id": form.tx_id}, {"$set": tx})


@router.get("/admin/overview", response_class=HTMLResponse,)
async def overview(request: Request, auth:  UserDBModel = Depends(enforce_is_admin), view: str = Query(alias="ui", default="main"), page:  Union[int, None] = Query(default=1)):
    if not auth:
        return RedirectResponse("/sign-in")

    user, _ = auth

    views = ["main", "overview", "users",
             "transfers", "transactions", "settings"]

    if not view.lower() in views:
        view = views[0]

    l_users = await db[Collections.users].count_documents({})
    l_txs = await db[Collections.transfers].count_documents({})

    # print(l_users, l_txs)

    max_users_pages = math.ceil(l_users / settings.per_page)
    max_tx_pages = math.ceil(l_txs / settings.per_page)

    start, stop = 0, 0

    if view == "users":
        page = min(max_users_pages, page)
        start = (settings.per_page * page) - settings.per_page
        stop = start + settings.per_page

    if view == "transfers":
        page = min(max_tx_pages, page)
        start = (settings.per_page * page) - settings.per_page
        stop = start + settings.per_page

    # get all users
    users = await db[Collections.users].find({}).sort("email", -1).skip(start).to_list(length=settings.per_page)

    # get all transfers
    transfers = await db[Collections.transfers].find({}).sort("created", -1).skip(start).to_list(length=settings.per_page)

    return templates.TemplateResponse("admin/overview.html", {"users": users, "transfers": transfers, "settings":  settings, "ui": view, "user": user, "request":  request, "up": [x for x in range(1, max_users_pages + 1)], "tp": [x for x in range(1, max_tx_pages + 1)], "page": page, "lup": max_users_pages, "ltp": max_tx_pages})


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
