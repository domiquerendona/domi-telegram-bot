import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { join } from 'node:path';

const browserDistFolder = join(import.meta.dirname, '../browser');

const app = express();
const allowedHosts = process.env['ALLOWED_HOSTS']
  ? process.env['ALLOWED_HOSTS'].split(',')
  : ['angular-production-44c8.up.railway.app', 'localhost'];
const angularApp = new AngularNodeAppEngine({ allowedHosts });

/**
 * Servir archivos estáticos del browser build
 */
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

/**
 * Todas las rutas las maneja Angular SSR
 */
app.use(async (req, res, next) => {
  try {
    const response = await angularApp.handle(req);
    if (response) {
      await writeResponseToNodeResponse(response, res);
    } else {
      next();
    }
  } catch (e) {
    next(e);
  }
});

/**
 * Iniciar servidor
 */
if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = Number(process.env['PORT']) || 3000;

  app.listen(port, '0.0.0.0', (error?: Error) => {
    if (error) throw error;
    console.log(`Server running on port ${port}`);
  });
}

export const reqHandler = createNodeRequestHandler(app);
