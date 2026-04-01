import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('[interceptor] running:', req.url);
  try {
    const token = localStorage.getItem('admin_token');
    console.log('[interceptor] token:', token ? 'FOUND' : 'NULL');
    if (token) {
      req = req.clone({
        setHeaders: { Authorization: token }
      });
    }
  } catch {
    console.log('[interceptor] SSR context - no localStorage');
  }
  return next(req);
};
