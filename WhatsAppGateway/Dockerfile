FROM node:22-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev --no-audit --no-fund
COPY src ./src
RUN mkdir -p /var/lib/errno-whatsapp/session && chown -R node:node /var/lib/errno-whatsapp
USER node
EXPOSE 8787
CMD ["npm", "start"]
