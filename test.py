import pytest
from fastapi.testclient import TestClient
from main import app
from uuid import uuid4

client = TestClient(app)

# Test if a receipt is processed and the receipt ID is returned
def test_process_receipt():
    receipt = {
        "retailer": "M&M Corner Market",
        "purchaseDate": "2022-03-20",
        "purchaseTime": "14:33",
        "items": [
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"}
        ],
        "total": "9.00"
    }
    
    response = client.post("/receipts/process", json=receipt)
    # Check if the response is a dictionary
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "id" in response.json()
    
    # Check if the receipt_id is a string and not empty
    receipt_id = response.json()["id"]
    assert isinstance(receipt_id, str)
    assert len(receipt_id) > 0
    
    # Check if the points are calculated and being returned
    points_response = client.get(f"/receipts/{receipt_id}/points")
    assert points_response.status_code == 200
    assert "points" in points_response.json()

# Test if the points are calculated correctly for the sample M&M Corner Market receipt
def test_get_points_market():
    receipt = {
        "retailer": "M&M Corner Market",
        "purchaseDate": "2022-03-20",
        "purchaseTime": "14:33",
        "items": [
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"},
            {"shortDescription": "Gatorade", "price": "2.25"}
        ],
        "total": "9.00"
    }
    # Process the receipt and get the receipt ID
    process_response = client.post("/receipts/process", json=receipt)
    receipt_id = process_response.json()["id"]

    # Get the points for the receipt ID generated above
    points_response = client.get(f"/receipts/{receipt_id}/points")
    assert points_response.status_code == 200
    assert points_response.json()["points"] == 109


# Test if the points are calculated correctly for the sample Target receipt
def test_get_points_target():
    receipt = {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:01",
        "items": [
            {
            "shortDescription": "Mountain Dew 12PK",
            "price": "6.49"
            },{
            "shortDescription": "Emils Cheese Pizza",
            "price": "12.25"
            },{
            "shortDescription": "Knorr Creamy Chicken",
            "price": "1.26"
            },{
            "shortDescription": "Doritos Nacho Cheese",
            "price": "3.35"
            },{
            "shortDescription": "   Klarbrunn 12-PK 12 FL OZ  ",
            "price": "12.00"
            }
        ],
        "total": "35.35"
    }   
    process_response = client.post("/receipts/process", json=receipt)
    receipt_id = process_response.json()["id"]

    points_response = client.get(f"/receipts/{receipt_id}/points")
    assert points_response.status_code == 200
    assert points_response.json()["points"] == 28


class TestReceiptErrors:
    def test_receipt_not_found_basic(self):
        # Test basic case of non-existent receipt ID using a valid UUID format
        non_existent_uuid = str(uuid4())
        response = client.get(f"/receipts/{non_existent_uuid}/points")
        assert response.status_code == 404
        assert response.json()["detail"] == "No receipt found for that ID."

    def test_invalid_receipt_format(self):
        # Test invalid receipt format
        invalid_receipt = {
            "retailer": "",  # Empty retailer
            "purchaseDate": "2022-03-20",
            "purchaseTime": "14:33",
            "items": [
                {"shortDescription": "Milk", "price": "4.50"}
            ],
            "total": "4.50"
        }
        response = client.post("/receipts/process", json=invalid_receipt)
        assert response.status_code == 400
        assert response.json()["detail"] == "The receipt is invalid."

    @pytest.mark.parametrize("invalid_receipt", [
        {  # Missing required fields
            "retailer": "Test Store"
        },
        {  # Invalid date format
            "retailer": "Test Store",
            "purchaseDate": "03-20-2022",  # Wrong format
            "purchaseTime": "14:33",
            "items": [{"shortDescription": "Item", "price": "5.00"}],
            "total": "5.00"
        },
        {  # Invalid price format
            "retailer": "Test Store",
            "purchaseDate": "2022-03-20",
            "purchaseTime": "14:33",
            "items": [{"shortDescription": "Item", "price": "-5.00"}],  # Negative price
            "total": "5.00"
        },
        {  # Invalid time format
            "retailer": "Test Store",
            "purchaseDate": "2022-03-20",
            "purchaseTime": "2:33 PM",  # Wrong format (should be 24-hour)
            "items": [{"shortDescription": "Item", "price": "5.00"}],
            "total": "5.00"
        },
        {  # Empty items list
            "retailer": "Test Store",
            "purchaseDate": "2022-03-20",
            "purchaseTime": "14:33",
            "items": [],
            "total": "0.00"
        }
    ])

    def test_invalid_receipt_variations(self, invalid_receipt):
        # Test various invalid receipt formats
        response = client.post("/receipts/process", json=invalid_receipt)
        assert response.status_code == 400
        assert response.json()["detail"] == "The receipt is invalid."

    @pytest.mark.parametrize("invalid_id", [
        str(uuid4()),  # Random valid UUID format
        "invalid-id",
        "null",
        "undefined"
    ])
    def test_receipt_not_found_variations(self, invalid_id):
        """Test various non-existent receipt IDs"""
        response = client.get(f"/receipts/{invalid_id}/points")
        assert response.status_code == 404
        assert response.json()["detail"] == "No receipt found for that ID."



