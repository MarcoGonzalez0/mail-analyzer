FROM python:3.12-slim

WORKDIR /app 
# Directorio de trabajo dentro del contenedor

COPY requirements.txt . 
# Copia el archivo de requisitos al contenedor

RUN pip install --no-cache-dir -r requirements.txt 
# Instala las dependencias necesarias para la aplicación

COPY . . 
# Copia el resto de los archivos de la aplicación al contenedor

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]