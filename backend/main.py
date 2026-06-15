from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'inventory.db'}"

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
PBKDF2_ITERATIONS = 120_000

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="customer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    orders: Mapped[List["Order"]] = relationship(back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_category_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    products: Mapped[List["Product"]] = relationship(back_populates="category", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), default="")
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    category: Mapped[Optional[Category]] = relationship(back_populates="products")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="product")

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="items")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = ""
    password: str = Field(min_length=6, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = ""
    role: str
    created_at: datetime

class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = ""

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = ""

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = ""
    created_at: datetime

class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = ""
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    image_url: Optional[str] = ""
    category_id: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = ""
    price: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = ""
    category_id: Optional[int] = None

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = ""
    price: float
    stock: int
    image_url: Optional[str] = ""
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    created_at: datetime

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: float
    product_name: Optional[str] = None

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: datetime
    items: List[OrderItemOut] = []

app = FastAPI(
    title="E-Commerce Inventory API",
    description="FastAPI inventory management API with authentication, CRUD, and order handling.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(hashed).decode()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_b64, hash_b64 = hashed_password.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(hash_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

def product_to_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        image_url=product.image_url,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        created_at=product.created_at,
    )

def order_to_out(order: Order) -> OrderOut:
    items = [
        OrderItemOut(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            product_name=item.product.name if item.product else None,
        )
        for item in order.items
    ]
    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at,
        items=items,
    )

def seed_data(db: Session):
    if db.query(User).count() == 0:
        admin = User(
            email="admin@shop.com",
            full_name="Demo Admin",
            hashed_password=hash_password("Admin123!"),
            role="admin",
        )
        customer = User(
            email="customer@shop.com",
            full_name="Demo Customer",
            hashed_password=hash_password("Customer123!"),
            role="customer",
        )
        db.add_all([admin, customer])
        db.commit()

    if db.query(Category).count() == 0:
        categories = [
            Category(name="Phones", description="Mobile devices and accessories"),
            Category(name="Computers", description="Laptops and PC gear"),
            Category(name="Groceries", description="Basic grocery inventory"),
        ]
        db.add_all(categories)
        db.commit()

    if db.query(Product).count() == 0:
        cats = {c.name: c for c in db.query(Category).all()}
        products = [
            Product(name="Smartphone X", description="Latest Android smartphone", price=699.99, stock=25, category_id=cats["Phones"].id),
            Product(name="Laptop Pro 14", description="Lightweight productivity laptop", price=1199.0, stock=12, category_id=cats["Computers"].id),
            Product(name="Rice 25kg", description="Premium rice bag", price=32.5, stock=80, category_id=cats["Groceries"].id),
        ]
        db.add_all(products)
        db.commit()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

@app.get("/", tags=["General"])
def root():
    return {"message": "E-Commerce Inventory API is running"}

@app.get("/health", tags=["General"])
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserOut, tags=["Auth"], status_code=201)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=Token, tags=["Auth"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)

@app.get("/users/me", response_model=UserOut, tags=["Auth"])
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/categories", response_model=list[CategoryOut], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name.asc()).all()

@app.post("/categories", response_model=CategoryOut, status_code=201, tags=["Categories"])
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    existing = db.query(Category).filter(Category.name == category_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    category = Category(name=category_in.name, description=category_in.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@app.get("/categories/{category_id}", response_model=CategoryOut, tags=["Categories"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@app.put("/categories/{category_id}", response_model=CategoryOut, tags=["Categories"])
def update_category(category_id: int, category_in: CategoryUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category_in.name is not None:
        category.name = category_in.name
    if category_in.description is not None:
        category.description = category_in.description
    db.commit()
    db.refresh(category)
    return category

@app.delete("/categories/{category_id}", status_code=204, tags=["Categories"])
def delete_category(category_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return None

@app.get("/products", response_model=list[ProductOut], tags=["Products"])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return [product_to_out(p) for p in products]

@app.get("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_to_out(product)

@app.post("/products", response_model=ProductOut, status_code=201, tags=["Products"])
def create_product(product_in: ProductCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if product_in.category_id is not None and db.get(Category, product_in.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    product = Product(
        name=product_in.name,
        description=product_in.description,
        price=float(Decimal(str(product_in.price))),
        stock=product_in.stock,
        image_url=product_in.image_url,
        category_id=product_in.category_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product_to_out(product)

@app.put("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product_in.category_id is not None and db.get(Category, product_in.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in product_in.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product_to_out(product)

@app.delete("/products/{product_id}", status_code=204, tags=["Products"])
def delete_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return None

@app.post("/orders", response_model=OrderOut, status_code=201, tags=["Orders"])
def create_order(order_in: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not order_in.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    order = Order(user_id=current_user.id, total_amount=0.0, status="pending")
    db.add(order)
    db.flush()

    total = 0.0

    for item_in in order_in.items:
        product = db.get(Product, item_in.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item_in.product_id} not found")
        if product.stock < item_in.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
        product.stock -= item_in.quantity
        line_total = float(Decimal(str(product.price)) * Decimal(item_in.quantity))
        total += line_total
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item_in.quantity,
                unit_price=product.price,
            )
        )

    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order_to_out(order)

@app.get("/orders", response_model=list[OrderOut], tags=["Orders"])
def list_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Order).order_by(Order.created_at.desc())
    if current_user.role != "admin":
        query = query.filter(Order.user_id == current_user.id)
    orders = query.all()
    return [order_to_out(order) for order in orders]

@app.get("/orders/{order_id}", response_model=OrderOut, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this order")
    return order_to_out(order)
