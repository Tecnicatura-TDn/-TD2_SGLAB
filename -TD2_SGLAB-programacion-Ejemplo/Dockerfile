FROM node:20-alpine

WORKDIR /usr/src/app

# Primero las dependencias (aprovecha la caché de capas)
COPY package*.json ./
RUN npm install

# Luego el código
COPY . .

EXPOSE 3000

CMD ["node", "app.js"]
