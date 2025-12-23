import json
import os

import faiss
from fastapi import FastAPI
from openai import OpenAI
from src.controller import router

app = FastAPI(root_path="/ai")
app.include_router(router)
