FROM node:20.12.1
RUN mkdir /frontend
WORKDIR /frontend
RUN npm install -g npm@10.5.0 && npm install create-next-app
RUN apt-get update && apt-get install -y xdg-utils
