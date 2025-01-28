# FastAPI to create and manage the web service
# HTTPException to handle errors
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Pydantic BaseModel to define the data models and validate the data
from pydantic import BaseModel, Field

# List to define a list of items for fields in Pydantic models.
from typing import List

# uuid to generate unique IDs for receipts
from uuid import uuid4

from datetime import datetime
import math

app = FastAPI()

# In-memory database to store the receipts and their points
receipts_db = {}


# Pydantic models
# Field(..., description="Description of the item") means that the field is required and has a description
class Item(BaseModel):
    shortDescription: str = Field(
        ..., 
        description="Description of the item",
        pattern=r"^[\w\s\-&]+$"
    )
    price: str = Field(
        ..., 
        description="Price of the item in USD",
        pattern=r"^\d+\.\d{2}$"
    )

class Receipt(BaseModel):
    retailer: str = Field(
        ..., 
        description="Retailer name",
        pattern=r"^[\w\s\-&]+$"
    )
    purchaseDate: str = Field(
        ..., 
        description="Date of purchase in YYYY-MM-DD format"
    )
    purchaseTime: str = Field(
        ..., 
        description="Time of purchase in HH:MM format"
    )
    items: List[Item] = Field(
        ..., 
        description="List of purchased items",
        min_length=1
    )
    total: str = Field(
        ..., 
        description="Total amount of the purchase in USD",
        pattern=r"^\d+\.\d{2}$"
    )

# calculate_points takes a Receipt object as input and returns an integer representing the points
# async def: function is asynchronous and can be used with await
async def calculate_points(receipt: Receipt) -> int:
    points = 0

    # Rule 1: One point for every alphanumeric character in the retailer name
    points += sum(char.isalnum() for char in receipt.retailer)

    # Rule 2: 50 points if the total is a round dollar amount with no cents
    if float(receipt.total).is_integer():
        points += 50

    # Rule 3: 25 points if the total is a multiple of 0.25
    if float(receipt.total) % 0.25 == 0:
        points += 25

    # Rule 4: 5 points for every two items
    points += (len(receipt.items) // 2) * 5

    # Rule 5: Points based on trimmed length of item description
    for item in receipt.items:
        trimmed_length = len(item.shortDescription.strip())
        if trimmed_length % 3 == 0:
            points += math.ceil(float(item.price) * 0.2)

    # Rule 6: 6 points if the day in the purchase date is odd
    purchase_date = datetime.strptime(receipt.purchaseDate, "%Y-%m-%d")
    if purchase_date.day % 2 != 0:
        points += 6

    # Rule 7: 10 points if the time is after 2:00pm and before 4:00pm
    purchase_time = datetime.strptime(receipt.purchaseTime, "%H:%M").time()
    if purchase_time >= datetime.strptime("14:00", "%H:%M").time() and purchase_time <= datetime.strptime("16:00", "%H:%M").time():
        points += 10

    return points


# process_receipt: processes a receipt and returns the receipt ID
# It takes a Receipt object as input and returns a dictionary with the receipt ID
@app.post("/receipts/process")
async def process_receipt(receipt: Receipt):
    try:
        # Validate date format
        datetime.strptime(receipt.purchaseDate, "%Y-%m-%d")
        
        # Validate time format
        datetime.strptime(receipt.purchaseTime, "%H:%M")
        
        # Convert prices from string to float for calculations
        total = float(receipt.total)
        items_total = sum(float(item.price) for item in receipt.items)
        
        # Validate total matches sum of items 
        if abs(total - items_total) != 0.00:
            raise HTTPException(
                status_code=400, 
                detail="The receipt is invalid."
            )

        # Generate a unique ID for the receipt
        receipt_id = str(uuid4())

        # Calculate the points for the receipt
        points = await calculate_points(receipt)

        # Store the points in the receipts_db dictionary
        receipts_db[receipt_id] = points

        return {"id": receipt_id}
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="The receipt is invalid."
        )


# get_points: returns the points for a receipt
# It takes a receipt ID as input and returns a dictionary with the points
@app.get("/receipts/{id}/points")
async def get_points(id: str):
    # Check if the receipt ID is in the receipts_db dictionary
    if id not in receipts_db:
        raise HTTPException(status_code=404, detail="No receipt found for that ID.")
    
    return {"points": receipts_db[id]}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "The receipt is invalid."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"detail": "No receipt found for that ID."}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
