#/bin/sh
git pull origin main
# docker compose down
docker compose pull
docker compose up -d --build --remove-orphans
docker compose logs -f api
