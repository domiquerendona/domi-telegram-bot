import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  try {
    const token = localStorage.getItem('admin_token');
    if (token) {
      req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
    }
  } catch {
    // SSR context — no localStorage
  }
  return next(req);
};
