import React, { useEffect, useMemo, useState } from 'react'
import { api } from './api'

const initialAuth = { email: 'admin@shop.com', password: 'Admin123!' }

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [user, setUser] = useState(null)
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [orders, setOrders] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [authMode, setAuthMode] = useState('login')
  const [busy, setBusy] = useState(false)
  const [selectedTab, setSelectedTab] = useState('catalog')

  const [loginForm, setLoginForm] = useState({ email: initialAuth.email, password: initialAuth.password })
  const [registerForm, setRegisterForm] = useState({ email: '', full_name: '', password: '' })
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' })
  const [productForm, setProductForm] = useState({ name: '', description: '', price: '', stock: '', image_url: '', category_id: '' })
  const [orderForm, setOrderForm] = useState({ product_id: '', quantity: 1 })

  const isAdmin = useMemo(() => user?.role === 'admin', [user])

  const loadData = async (authToken = token) => {
    try {
      const [cats, prods] = await Promise.all([api.categories(), api.products()])
      setCategories(cats)
      setProducts(prods)
      if (authToken) {
        const myOrders = await api.orders(authToken)
        setOrders(myOrders)
        const me = await api.me(authToken)
        setUser(me)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadData().catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    localStorage.setItem('token', token)
    loadData(token).catch((err) => setError(err.message))
  }, [token])

  const flash = (text, kind = 'success') => {
    if (kind === 'success') {
      setMessage(text)
      setError('')
    } else {
      setError(text)
      setMessage('')
    }
    setTimeout(() => {
      setMessage('')
      setError('')
    }, 3500)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const data = await api.login(loginForm.email, loginForm.password)
      setToken(data.access_token)
      flash('Logged in successfully')
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await api.register(registerForm)
      setAuthMode('login')
      flash('Account created. Please log in.')
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken('')
    setUser(null)
    flash('Logged out')
  }

  const submitCategory = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await api.createCategory(token, categoryForm)
      setCategoryForm({ name: '', description: '' })
      await loadData(token)
      flash('Category added')
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const submitProduct = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const payload = {
        ...productForm,
        price: Number(productForm.price),
        stock: Number(productForm.stock),
        category_id: productForm.category_id ? Number(productForm.category_id) : null,
      }
      await api.createProduct(token, payload)
      setProductForm({ name: '', description: '', price: '', stock: '', image_url: '', category_id: '' })
      await loadData(token)
      flash('Product added')
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const submitOrder = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const payload = {
        items: [
          {
            product_id: Number(orderForm.product_id),
            quantity: Number(orderForm.quantity),
          },
        ],
      }
      await api.createOrder(token, payload)
      setOrderForm({ product_id: '', quantity: 1 })
      await loadData(token)
      flash('Order created')
    } catch (err) {
      flash(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const stats = useMemo(() => ({
    products: products.length,
    categories: categories.length,
    orders: orders.length,
  }), [products, categories, orders])

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">FastAPI + React</p>
          <h1>E-Commerce Inventory API</h1>
          <p className="subtitle">
            Manage products, categories, users, and orders from one clean dashboard.
          </p>
        </div>
        <div className="hero-card">
          <div><strong>Products</strong><span>{stats.products}</span></div>
          <div><strong>Categories</strong><span>{stats.categories}</span></div>
          <div><strong>Orders</strong><span>{stats.orders}</span></div>
        </div>
      </header>

      <main className="grid">
        <section className="panel auth-panel">
          <div className="tabs">
            <button className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>Login</button>
            <button className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>Register</button>
          </div>

          {token ? (
            <div className="user-card">
              <p>Signed in as</p>
              <h3>{user?.full_name || user?.email || 'User'}</h3>
              <p className="muted">{user?.role || 'guest'}</p>
              <button onClick={handleLogout} className="secondary">Logout</button>
              <p className="hint">Demo admin: admin@shop.com / Admin123!</p>
            </div>
          ) : authMode === 'login' ? (
            <form onSubmit={handleLogin} className="form">
              <label>Email
                <input value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} />
              </label>
              <label>Password
                <input type="password" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} />
              </label>
              <button disabled={busy}>Login</button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="form">
              <label>Full name
                <input value={registerForm.full_name} onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })} />
              </label>
              <label>Email
                <input value={registerForm.email} onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })} />
              </label>
              <label>Password
                <input type="password" value={registerForm.password} onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })} />
              </label>
              <button disabled={busy}>Create account</button>
            </form>
          )}

          {message && <div className="notice success">{message}</div>}
          {error && <div className="notice error">{error}</div>}
        </section>

        <section className="panel">
          <div className="section-head">
            <h2>Catalog</h2>
            <div className="tabs small">
              <button className={selectedTab === 'catalog' ? 'active' : ''} onClick={() => setSelectedTab('catalog')}>Browse</button>
              <button className={selectedTab === 'admin' ? 'active' : ''} onClick={() => setSelectedTab('admin')}>Manage</button>
              <button className={selectedTab === 'orders' ? 'active' : ''} onClick={() => setSelectedTab('orders')}>Orders</button>
            </div>
          </div>

          {selectedTab === 'catalog' && (
            <>
              <div className="card-grid">
                {products.map((product) => (
                  <article key={product.id} className="card">
                    <div className="card-top">
                      <h3>{product.name}</h3>
                      <span className="price">${product.price.toFixed(2)}</span>
                    </div>
                    <p>{product.description || 'No description provided.'}</p>
                    <div className="meta">
                      <span>Stock: {product.stock}</span>
                      <span>{product.category_name || 'Uncategorized'}</span>
                    </div>
                  </article>
                ))}
              </div>
              <div className="card-grid categories">
                {categories.map((category) => (
                  <article key={category.id} className="card muted-card">
                    <h3>{category.name}</h3>
                    <p>{category.description || 'No description'}</p>
                  </article>
                ))}
              </div>
            </>
          )}

          {selectedTab === 'admin' && (
            <div className="admin-grid">
              <form onSubmit={submitCategory} className="form">
                <h3>Add Category</h3>
                <label>Name
                  <input value={categoryForm.name} onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })} />
                </label>
                <label>Description
                  <input value={categoryForm.description} onChange={(e) => setCategoryForm({ ...categoryForm, description: e.target.value })} />
                </label>
                <button disabled={!token || busy}>Create category</button>
              </form>

              <form onSubmit={submitProduct} className="form">
                <h3>Add Product</h3>
                <label>Name
                  <input value={productForm.name} onChange={(e) => setProductForm({ ...productForm, name: e.target.value })} />
                </label>
                <label>Description
                  <input value={productForm.description} onChange={(e) => setProductForm({ ...productForm, description: e.target.value })} />
                </label>
                <div className="row">
                  <label>Price
                    <input type="number" step="0.01" value={productForm.price} onChange={(e) => setProductForm({ ...productForm, price: e.target.value })} />
                  </label>
                  <label>Stock
                    <input type="number" value={productForm.stock} onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })} />
                  </label>
                </div>
                <label>Category
                  <select value={productForm.category_id} onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}>
                    <option value="">Select a category</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>{category.name}</option>
                    ))}
                  </select>
                </label>
                <button disabled={!token || busy}>Create product</button>
              </form>
            </div>
          )}

          {selectedTab === 'orders' && (
            <div className="admin-grid">
              <form onSubmit={submitOrder} className="form">
                <h3>Create Order</h3>
                <label>Product
                  <select value={orderForm.product_id} onChange={(e) => setOrderForm({ ...orderForm, product_id: e.target.value })}>
                    <option value="">Select a product</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>{product.name}</option>
                    ))}
                  </select>
                </label>
                <label>Quantity
                  <input type="number" min="1" value={orderForm.quantity} onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })} />
                </label>
                <button disabled={!token || busy}>Submit order</button>
              </form>

              <div className="orders-list">
                {orders.length === 0 ? (
                  <div className="empty">No orders yet.</div>
                ) : (
                  orders.map((order) => (
                    <article key={order.id} className="card">
                      <div className="card-top">
                        <h3>Order #{order.id}</h3>
                        <span className="price">${order.total_amount.toFixed(2)}</span>
                      </div>
                      <p>Status: {order.status}</p>
                      <ul>
                        {order.items.map((item) => (
                          <li key={item.id}>
                            {item.product_name || `Product ${item.product_id}`} × {item.quantity}
                          </li>
                        ))}
                      </ul>
                    </article>
                  ))
                )}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
