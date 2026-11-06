from fastapi import FastAPI

app = FastAPI(title="Inception Catalog API")

ITEMS = [
    {"id": 1, "name": "Laptop", "price": 75000},
    {"id": 2, "name": "Keyboard", "price": 2500},
    {"id": 3, "name": "Mouse", "price": 1200}
]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "catalog"}

@app.get("/items")
def get_items():
    return {"items": ITEMS}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    return next(
        (item for item in ITEMS if item["id"] == item_id),
        {"error": "Item not found"}
    )
