# syntax=docker/dockerfile:1.4
FROM node:22-alpine

LABEL project="ses" service="frontend"

WORKDIR /app

# Copy frontend files
COPY package*.json ./
COPY orval.config.cjs ./

# Install dependencies
RUN npm ci

# Copy all frontend files
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
