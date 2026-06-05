FROM node:18-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Expose the Vite default port
EXPOSE 5173

# Run the dev server on 0.0.0.0 so it can be accessed outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
