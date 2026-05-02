# Este Dockerfile es diferente al de Python porque usa un patrón llamado multi-stage build. Tiene dos etapas.
# La primera etapa (builder) se encarga de compilar el código Go. Usa la imagen oficial de Go, copia el código fuente, descarga las dependencias y compila el programa.

FROM golang:1.23-alpine AS builder

WORKDIR /app
# Establece el directorio de trabajo dentro del contenedor del scanner.

COPY go.mod .
# "estas son las dependencias que necesito"

RUN go mod download  
# Descarga las dependencias del proyecto.

COPY . .

RUN go build -o bin/scanner ./cmd
# Compila todo el código Go y genera un binario ejecutable llamado scanner dentro de bin/. Esto es algo que Python no hace, Go compila a un archivo ejecutable standalone.

# go build          → compilar
# -o bin/scanner    → el ejecutable output se llama "scanner" y va dentro de "bin/"
# ./cmd             → compilá el código que está en la carpeta cmd/


# Etapa 2 — imagen final

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/bin/scanner .
# Copia solo el binario compilado de la etapa anterior. Todo el código fuente, las herramientas de Go, las dependencias, quedan afuera. Esto hace que la imagen final sea mucho más liviana, porque solo incluye lo necesario para ejecutar el programa. Go no necesita estar instalado para correr el binario, solo para compilarlo.
# app/bin/scanner --- (Existe dentro del contenedor)

EXPOSE 8080

CMD ["./scanner"]