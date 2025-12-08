import json
import os

import faiss
from fastapi import FastAPI
from openai import OpenAI
from src.controller import router

app = FastAPI()
app.include_router(router)
