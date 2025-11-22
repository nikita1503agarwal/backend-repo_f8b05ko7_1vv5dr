"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Example schemas (you can keep or remove if not needed)

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# EV Charging Station schema

ConnectorType = Literal[
    "CCS2",
    "CHAdeMO",
    "Type2",
    "Type3",
    "Tesla",
    "GB/T",
]

class Station(BaseModel):
    """
    EV Charging Station
    Collection name: "station"
    """
    name: str = Field(..., description="Station name")
    network: Optional[str] = Field(None, description="Network/operator name")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    country: Optional[str] = Field("IN")
    postal_code: Optional[str] = Field(None)
    connectors: List[ConnectorType] = Field(default_factory=list, description="Supported connector standards")
    power_kw: Optional[float] = Field(None, ge=0, description="Max charging power in kW")
    price: Optional[str] = Field(None, description="Pricing info or note")
    available: Optional[bool] = Field(True, description="Availability flag (if known)")
    amenities: List[str] = Field(default_factory=list, description="Nearby amenities")
    phone: Optional[str] = Field(None)
    hours: Optional[str] = Field(None)

# Add your own schemas here as needed.
