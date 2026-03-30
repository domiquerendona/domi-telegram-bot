import {
  createNodeRequestHandler,
  isMainModule,
} from '@angular/ssr/node';
import express from 'express';
import { join } from 'node:path';

const browserDistFolder = join(import.meta.dirname, '../browser');

const app = express();

/**
 * Servir archivos estáticos
 */
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

/**
 * 👉 IMPORTANTE: fallback para Angular (SPA)
 */
app.use((req, res) => {
  res.sendFile(join(browserDistFolder, 'index.html'));
});

/**
 * Iniciar servidor
 */
if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = Number(process.env["PORT"]) || 3000;

  app.listen(port, '0.0.0.0', (error) => {
    if (error) throw error;

    console.log(`Server running on port ${port}`);
  });
}

export const reqHandler = createNodeRequestHandler(app);