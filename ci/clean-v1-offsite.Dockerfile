FROM node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203
WORKDIR /app/upstream
RUN mkdir -p /home/ci /home/offsite && chown 10001:10001 /home/ci /home/offsite
COPY --chown=10001:10001 . /app/upstream
USER 10001:10001
ENTRYPOINT ["node","/app/upstream/ci-container-pilot.mjs"]
