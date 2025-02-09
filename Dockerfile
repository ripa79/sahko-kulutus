FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/modules ./modules
COPY --from=builder /app/server.js .
COPY --from=builder /app/package*.json .

EXPOSE 3000

CMD ["npm", "start"]