FROM scratch

USER 1000

COPY --chown=1000:1000 scratch.bin scratch.bin

ARG BUILD_TIME
ENV BUILD_TIME=${BUILD_TIME}

LABEL org.grand-challenge.api-method=invoke
