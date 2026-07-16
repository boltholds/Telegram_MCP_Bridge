FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 bridge && mkdir -p /data/telegram && chown -R bridge:bridge /data
USER bridge
EXPOSE 8765
CMD ["python", "-m", "telegram_mcp_bridge.web"]
