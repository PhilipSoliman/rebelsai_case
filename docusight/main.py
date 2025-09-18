from typing import Union

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os
from pathlib import Path

# hardcoded folder path (not realistic, just for demo purposes)
CLIENT_FOLDER = Path(os.path.dirname(os.path.abspath(__file__))) / "client"

# main application instance
app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)