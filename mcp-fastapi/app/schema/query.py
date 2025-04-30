from pydantic import BaseModel
from typing import List


class DBQueryRequest(BaseModel):
    query: str

class DBQueryResponse(BaseModel):
    rows: List[dict]
    message: str