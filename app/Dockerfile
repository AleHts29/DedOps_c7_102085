# Imagen base vieja A PROPOSITO, para que el escaneo de imagen
# encuentre vulnerabilidades del sistema operativo.
# En el ejercicio 3 la vas a cambiar por python:3.12-slim y comparar.
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_insegura.py .

EXPOSE 8000

# Correr como root tambien es un hallazgo: en la version corregida
# se crea un usuario sin privilegios con USER.
CMD ["python", "app_insegura.py"]
