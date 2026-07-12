# Image de l'agent CEO autonome. Build depuis le dossier company/ :
#   docker build -t company-agent .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x scripts/agent_loop.sh

# Boucle 24/7 : dialogue Slack + cycles (voir scripts/agent_loop.sh)
CMD ["bash", "scripts/agent_loop.sh"]
