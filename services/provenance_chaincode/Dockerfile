FROM golang:1.25.4-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -o /provenance .

FROM debian:bookworm-slim
COPY --from=build /provenance /provenance
ENTRYPOINT ["/provenance"]
