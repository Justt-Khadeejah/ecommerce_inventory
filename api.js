const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, { method = 'GET', token, body, form = false } = {}) {
  const headers = {};
  let payload = body;

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    payload = new URLSearchParams(body);
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
  });

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (email, password) => request('/auth/login', { method: 'POST', form: true, body: { username: email, password } }),
  me: (token) => request('/users/me', { token }),
  categories: () => request('/categories'),
  createCategory: (token, payload) => request('/categories', { method: 'POST', token, body: payload }),
  updateCategory: (token, id, payload) => request(`/categories/${id}`, { method: 'PUT', token, body: payload }),
  deleteCategory: (token, id) => request(`/categories/${id}`, { method: 'DELETE', token }),
  products: () => request('/products'),
  createProduct: (token, payload) => request('/products', { method: 'POST', token, body: payload }),
  updateProduct: (token, id, payload) => request(`/products/${id}`, { method: 'PUT', token, body: payload }),
  deleteProduct: (token, id) => request(`/products/${id}`, { method: 'DELETE', token }),
  orders: (token) => request('/orders', { token }),
  createOrder: (token, payload) => request('/orders', { method: 'POST', token, body: payload }),
  health: () => request('/health'),
};
