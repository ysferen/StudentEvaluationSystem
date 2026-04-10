# syntax=docker/dockerfile:1.4
FROM node:22-alpine

WORKDIR /app

# Copy frontend files
COPY package*.json ./
COPY orval.config.cjs ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--host"]
