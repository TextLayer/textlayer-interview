docker build -t textlayer-interview .
docker run -d --name textlayer-test -p 5000:5000 --env-file .env textlayer-interview
