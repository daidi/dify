FROM --platform=linux/amd64 node:19-bullseye-slim

WORKDIR /app

COPY . .

RUN npm config set registry https://registry.npmmirror.com && yarn install
# RUN yarn install
RUN yarn build

EXPOSE 3000

CMD ["yarn","start"]
