import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from database.database import engine, initialize_database
from database.base import Base
from routers import auth, users, members, audit, dashboard, gadgets
from database.models.gadget import Gadget, GadgetVariant, Warehouse, GadgetVariantStock, StockMovement, GadgetLock

app = FastAPI(title="APS Backend v2")
# Inizializzazione automatica database (tabelle, permessi e trigger)
initialize_database()

# Ensure directories for uploaded images exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
images_dir = os.path.join(static_dir, "images", "gadgets")
os.makedirs(images_dir, exist_ok=True)

# Mount static files folder
app.mount("/static", StaticFiles(directory=static_dir), name="static")

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(users.router, prefix="/users")
app.include_router(members.router, prefix="/members")
app.include_router(audit.router, prefix="/audit-logs")
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
app.include_router(gadgets.router, prefix="/gadgets", tags=["gadgets"])


#if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run(app, host="0.0.0.0", port=8000)