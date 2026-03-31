FROM node:22.12.0-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN printf 'export const environment = { production: true, apiBaseUrl: "https://backend-production-dc5f.up.railway.app" };\n' > src/environments/environment.ts \
 && printf 'export const environment = { production: true, apiBaseUrl: "https://backend-production-dc5f.up.railway.app" };\n' > src/environments/environment.prod.ts
RUN npm run build -- --configuration production

ENV PORT=3000
EXPOSE 3000

CMD ["node", "dist/Frontend/server/server.mjs"]
