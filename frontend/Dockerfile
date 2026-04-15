# syntax=docker/dockerfile:1.4
FROM node:22-alpine

LABEL project="ses" service="frontend"

RUN mkdir -p /app && chown node:node /app
WORKDIR /app

USER node

COPY --chown=node:node package*.json ./
COPY --chown=node:node orval.config.cjs ./

RUN npm ci

COPY --chown=node:node . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
