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

# Copy OpenAPI schema from docs/api build context
COPY --from=schema_ctx schema.yml ./src/shared/api/schema.yml

# Generate API client
RUN npm run generate:api

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
