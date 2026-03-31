FROM node:22.12.0-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV PORT=3000
EXPOSE 3000

CMD ["node", "dist/Frontend/server/server.mjs"]
