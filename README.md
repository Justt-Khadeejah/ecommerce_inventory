# E-Commerce Inventory API + React Frontend

## Backend
- FastAPI
- SQLite database
- SQLAlchemy ORM
- JWT authentication
- Password hashing
- CRUD for categories, products, and orders

### Demo credentials
- Admin: `admin@shop.com`
- Password: `Admin123!`
- Customer: `customer@shop.com`
- Password: `Customer123!`

## Run backend
```bash
cd backend
python -m venv .venv
# activate the virtual environment
pip install -r requirements.txt
uvicorn main:app --reload
```

The SQLite database is stored in `backend/db/inventory.db`.

## Frontend
- React + Vite
- API integration with login, register, catalog, management, and orders

### Run frontend
```bash
cd frontend
npm install
npm run dev
```

## API docs
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Notes
- Admin users can create/update/delete categories and products.
- Authenticated users can place orders.
- The database is pre-seeded with sample categories and products.
