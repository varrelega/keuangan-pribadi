import axios from 'axios';

const IS_PRODUCTION = window.location.hostname !== 'localhost';
const API_BASE = IS_PRODUCTION
  ? 'https://keuangan-pribadi-production-f4c0.up.railway.app/api'
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const register = (username, password) =>
  api.post('/auth/register', { username, password });

export const login = (username, password) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  return api.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

// Wallets
export const getWallets = () => api.get('/wallets/');
export const getWallet = (id) => api.get(`/wallets/${id}`);
export const createWallet = (data) => api.post('/wallets/', data);
export const updateWallet = (id, data) => api.put(`/wallets/${id}`, data);
export const deleteWallet = (id) => api.delete(`/wallets/${id}`);

// Categories
export const getCategories = () => api.get('/categories/');
export const createCategory = (data) => api.post('/categories/', data);
export const updateCategory = (id, data) => api.put(`/categories/${id}`, data);
export const deleteCategory = (id) => api.delete(`/categories/${id}`);

// Budgets
export const getBudgets = (periode) =>
  api.get('/budgets/', { params: periode ? { periode } : {} });
export const createBudget = (data) => api.post('/budgets/', data);
export const updateBudget = (id, data) => api.put(`/budgets/${id}`, data);
export const deleteBudget = (id) => api.delete(`/budgets/${id}`);

// Transactions
export const getTransactions = (filters = {}) =>
  api.get('/transactions/', { params: filters });
export const createTransaction = (data) => api.post('/transactions/', data);
export const deleteTransaction = (id) => api.delete(`/transactions/${id}`);

// Dashboard
export const getDashboard = () => api.get('/dashboard/');

export default api;
