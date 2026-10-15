# GIxPD – Práctica 2: entrenar y servir un modelo con Docker y Kubernetes

Servicio que entrena un modelo con datos de 100 clientes de una tienda
(minutos antes de comprar vs. dinero gastado) y lo expone por API.
Se empaqueta en Docker y se despliega en Kubernetes (Minikube).

## Arquitectura

```
ConfigMap (MODEL_PATH) ──┬──▶ Job: entrena ──escribe──▶ PVC ◀──lee── Deployment (3 pods)
                         └─────────────────────────────────────────────────▲
                                                                  Service "modelserver"
```

- **ConfigMap**: guarda la ruta del modelo (`MODEL_PATH`) fuera de las imágenes.
- **PVC**: volumen compartido donde el Job deja el modelo y de donde lo leen los pods.
- **Job**: entrena el modelo una vez y termina.
- **Deployment**: 3 réplicas del servidor Flask, siempre activas.
- **Service**: punto de entrada único que reparte el tráfico entre los 3 pods.

## Estructura del repo

```
practica2/
├── train/    # script de entrenamiento + Dockerfile (model-train:default)
├── server/   # API Flask + Dockerfile (model-server:default)
└── k8s/      # manifiestos: configmap, pvc, job, deployment, service
```

## Requisitos

- Docker
- Minikube
- kubectl

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

# 2. Cargar las imágenes en Minikube (vía .tar por su tamaño)
docker save -o model-train.tar model-train:default
docker save -o model-server.tar model-server:default
minikube image load model-train.tar
minikube image load model-server.tar
minikube image ls

# 3. Configuración y almacenamiento
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl get pvc                      # debe estar en Bound

# 4. Entrenar el modelo (Job)
kubectl apply -f k8s/job.yaml
kubectl get jobs                     # COMPLETIONS 1/1
kubectl logs job/model-train

# 5. Servidor (Deployment + Service)
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods                     # 3 pods model-server en 1/1 Running
kubectl get endpoints modelserver    # 3 IPs, una por pod

# 6. Acceder al servicio
kubectl port-forward service/modelserver 5000:5000
```

Desde otra terminal:

```bash
curl localhost:5000/
curl "localhost:5000/model?minutes=5"
```

### Recursos de `k8s/`

| Archivo | Recurso | Qué hace |
|---|---|---|
| `configmap.yaml` | ConfigMap `model-config` | Guarda `MODEL_PATH=/models/model.npy` |
| `pvc.yaml` | PersistentVolumeClaim `model-pvc` | Volumen donde se guarda el modelo |
| `job.yaml` | Job `model-train` | Entrena y guarda el modelo en el PVC; con requests y límites de recursos |
| `deployment.yaml` | Deployment `model-server` | 3 réplicas del servidor, con recursos, probes de liveness y readiness y el PVC montado |
| `service.yaml` | Service `modelserver` | Reparte el tráfico entre los 3 pods (puerto 5000 → 8000) |

### Puertos

El servidor Flask escucha en el **8000**. El Service expone el **5000** y reenvía
al 8000 (`port: 5000`, `targetPort: 8000`), así el
`kubectl port-forward service/modelserver 5000:5000` del enunciado funciona sin
tocar las imágenes.

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
- [x] Deployment (3 réplicas)
- [x] Service
- [ ] Prueba de excelencia: cambiar el modelo y ver que la API devuelve otro valor

## Dificultades y aprendizajes

- GitHub ya no acepta contraseña por HTTPS: hace falta un token personal clásico con permiso `repo` (uno de grano fino dio error 403).
- `np.save` añade `.npy` al nombre del archivo; train y server deben usar la misma ruta exacta.
- Con una ruta relativa en `MODEL_PATH` (`models/model.npy`) el servidor no encontraba el modelo; hay que usar la absoluta (`/models/model.npy`).
- El script del servidor no arranca Flask (no tiene `app.run`), así que se lanza desde el `CMD` con `flask --app main-server run --host=0.0.0.0 --port=8000`. Es el servidor de desarrollo de Flask; en producción se usaría gunicorn.
- Los contenedores son efímeros: el modelo se guarda en un volumen (en Kubernetes, un PVC) para que sobreviva y lo compartan el Job y el servidor.
- El alias de `kubectl` solo existía en la terminal donde se escribió: hay que añadirlo a `~/.bashrc`.
- Tras reiniciar la VM, Minikube estaba parado y `kubectl` daba `no route to host`: hay que hacer `minikube start`.
- La VM se quedó sin espacio (`no space left on device`) al arrancar Minikube: se amplió el disco a 30 GB.
- El `selector` del Service tiene que coincidir con las etiquetas de los pods (`app: model-server`); se comprueba con `kubectl get endpoints modelserver`, que debe listar las 3 IPs.
- Un Job no se puede editar ni relanzar: hay que borrarlo y volver a aplicarlo.
