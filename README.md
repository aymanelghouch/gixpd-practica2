# GIxPD – Práctica 2: entrenar y servir un modelo con Docker y Kubernetes


Servicio que entrena un modelo con datos de 100 clientes de una tienda
(minutos antes de comprar vs. dinero gastado) y lo expone por API.
Se empaqueta en Docker y se despliega en Kubernetes (Minikube).

## Estructura del repo

```
practica2/
├── train/    # script de entrenamiento + Dockerfile (model-train:default)
├── server/   # API Flask + Dockerfile (model-server:default)
└── k8s/      # manifiestos de Kubernetes (ConfigMap, PVC, Job, Deployment, Service)
```

## Requisitos

- Docker
- Minikube (para la fase de Kubernetes)
- kubectl (para la fase de Kubernetes)

## Variable `MODEL_PATH`

Indica dónde se guarda (train) y desde dónde se lee (server) el modelo.
Su valor es `/models/model.npy`. Debe terminar en `.npy`: `np.save` añade esa
extensión por su cuenta y el servidor tiene que leer el nombre exacto.
Además debe ser una ruta absoluta (con `/` inicial). En Kubernetes este valor
viene de un ConfigMap.

## Imagen `model-train`

Entrena el modelo y lo guarda en la ruta indicada por `MODEL_PATH`.

```bash
# Construir la imagen
docker build -t model-train:default ./train

# Crear el volumen donde se guardará el modelo
docker volume create modelvol

# Entrenar y guardar el modelo en el volumen
docker run --rm \
  -e MODEL_PATH=/models/model.npy \
  -v modelvol:/models \
  model-train:default

# Comprobar que el modelo está en el volumen
docker run --rm -v modelvol:/models alpine ls -l /models
```

## Imagen `model-server`

API Flask con dos rutas: `/` (página de documentación) y
`/model?minutes=5` (devuelve la predicción en JSON). Lee el modelo del volumen.

```bash
# Construir la imagen
docker build -t model-server:default ./server

# Arrancar el servidor
docker run --rm -p 8000:8000 \
  -e MODEL_PATH=/models/model.npy \
  -v modelvol:/models \
  model-server:default

# Probar (desde otra terminal)
curl localhost:8000/
curl "localhost:8000/model?minutes=5"
```

## Despliegue en Kubernetes (Minikube)

```bash
# 1. Arrancar el clúster
minikube start

# 2. Cargar las imágenes en Minikube (a través de .tar por su tamaño)
docker save -o model-train.tar model-train:default
docker save -o model-server.tar model-server:default
minikube image load model-train.tar
minikube image load model-server.tar
minikube image ls

# 3. Configuración y almacenamiento
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml

# 4. Entrenar el modelo (Job)
kubectl apply -f k8s/job.yaml
kubectl get jobs
kubectl logs job/model-train
```

Recursos de `k8s/`:

- `configmap.yaml`: ConfigMap `model-config` con `MODEL_PATH=/models/model.npy`.
- `pvc.yaml`: PersistentVolumeClaim `model-pvc`, el volumen donde se guarda el modelo.
- `job.yaml`: Job `model-train` que entrena y guarda el modelo en el PVC, con requests y límites de recursos.

## Buenas prácticas de Docker aplicadas

- Imagen base con versión fija y variante ligera (`python:3.11-slim`).
- `requirements.txt` se copia antes que el código para aprovechar la caché de capas.
- `pip install --no-cache-dir` para no guardar caché en la imagen.
- `COPY` solo de lo necesario y `.dockerignore` en cada carpeta.
- Configuración por variable de entorno (`MODEL_PATH`), no escrita en el código.
- Un solo proceso por contenedor.

## Estado del proyecto

- [x] Imagen `model-train:default`
- [x] Imagen `model-server:default`
- [x] ConfigMap
- [x] PVC
- [x] Job (entrenamiento)
- [ ] Deployment (3 réplicas)
- [ ] Service
- [ ] Prueba de excelencia: cambiar el modelo y ver que la API devuelve otro valor

## Dificultades y aprendizajes

- GitHub ya no acepta contraseña por HTTPS: hace falta un token personal clásico con permiso `repo` (uno de grano fino dio error 403).
- `np.save` añade `.npy` al nombre del archivo; train y server deben usar la misma ruta exacta.
- Con una ruta relativa en `MODEL_PATH` (`models/model.npy`) el servidor no encontraba el modelo; hay que usar la absoluta (`/models/model.npy`).
- El script del servidor no arrancaba Flask (no tiene `app.run`), así que se lanza desde el `CMD` con `flask --app main-server run --host=0.0.0.0 --port=8000`.
- Los contenedores son efímeros: el modelo se guarda en un volumen (en Kubernetes, un PVC) para que sobreviva y lo compartan Job y servidor.
- El alias de `kubectl` solo existía en la terminal donde se escribió: hay que añadirlo a `~/.bashrc`.
- Tras reiniciar la VM, Minikube estaba parado y `kubectl` daba `no route to host`: hay que hacer `minikube start`.
- La VM se quedó sin espacio (`no space left on device`) al arrancar Minikube: se amplió el disco a 30 GB desde Sunstone.
