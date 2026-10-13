# GIxPD – Práctica 2: entrenar y servir un modelo con Docker y Kubernetes

Servicio que entrena un modelo con datos de 100 clientes de una tienda
(minutos antes de comprar vs. dinero gastado) y lo expone por API.
Se empaqueta en Docker y se despliega en Kubernetes (Minikube).

## Estructura del repo

```
practica2/
├── train/    # script de entrenamiento + Dockerfile (model-train:default)
├── server/   # API Flask + Dockerfile (model-server:default)
└── k8s/      # manifiestos de Kubernetes (ConfigMap, Job, Deployment, Service)
```

## Requisitos

- Docker
- Minikube (para la fase de Kubernetes)
- kubectl (para la fase de Kubernetes)

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

## Variable `MODEL_PATH`

Indica dónde se guarda (train) y desde dónde se lee (server) el modelo.
Su valor es `/models/model.npy`. Debe terminar en `.npy`: `np.save` añade esa
extensión por su cuenta, y el servidor tiene que leer el nombre exacto.
En Kubernetes este valor vendrá de un ConfigMap.

## Estado del proyecto

- [x] Imagen `model-train:default`
- [ ] Imagen `model-server:default`
- [ ] ConfigMap
- [ ] Job (entrenamiento)
- [ ] Deployment (3 réplicas)
- [ ] Service

## Dificultades y aprendizajes

- GitHub ya no acepta contraseña por HTTPS: hace falta un token personal clásico con permiso `repo`.
- `np.save` añade `.npy` al nombre del archivo; train y server deben usar la misma ruta exacta.
- Los contenedores son efímeros: el modelo se guarda en un volumen para que sobreviva.
