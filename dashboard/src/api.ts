/**
 * API base URL helper.
 * - In development (Vite dev server): empty string → Vite proxy handles /report, /events, etc.
 * - In production (Vercel): "/api" → Vercel routes to api/index.py serverless function.
 */
export const API = import.meta.env.PROD ? '/api' : '';
