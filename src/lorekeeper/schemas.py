from pydantic import BaseModel


class LoreRememberInput(BaseModel):
    thought: str
