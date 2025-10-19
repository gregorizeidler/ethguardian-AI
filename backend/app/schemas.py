from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Address(BaseModel):
    address: str
    label: Optional[str] = None
    risk_score: Optional[float] = Field(default=None, description="0-100")
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None


class Transaction(BaseModel):
    hash: str
    from_address: str = Field(alias="from")
    to_address: Optional[str] = Field(default=None, alias="to")
    value: float
    time: int
    block: int
    nonce: int


class Node(BaseModel):
    id: str
    label: Optional[str] = None
    group: Optional[str] = None
    risk_score: Optional[float] = None
    val: Optional[float] = None


class Link(BaseModel):
    source: str
    target: str
    label: str = "TRANSFER"
    count: Optional[int] = None
    value_sum: Optional[float] = None


class GraphResponse(BaseModel):
    nodes: List[Node]
    links: List[Link]


class Alert(BaseModel):
    id: str
    address: str
    type: str
    score: float
    created_at: int
    details: Dict[str, Any] = {}


class AddressProfile(BaseModel):
    address: str
    risk_score: float
    features: Dict[str, float]
    stats: Dict[str, float]
