# lab11

Repositorio para el codigo de automatización de Lab11

La primera dependencia es RabbitMQ, para crear una cola de mensajes entre el productor (El que recibe tareas) y los workers (Nuestros "editores")

```sh
docker run -d --hostname my-rabbit --name rabbitmq -e RABBITMQ_DEFAULT_USER=lab11 -e RABBITMQ_DEFAULT_PASS=Laboratorio11! -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management

```

Si se usa docker compose, mejor. Recuerda setear la cantidad de memoria para rabbit

# Variables de entorno

estas son las disponibles: Para levantar un productor y un worker

```dotenv
MODE = "producer" # producer, worker
RABBITMQ_HOST = "localhost"
RABBITMQ_USER = "XXXXXX" # Cambiar por el usuario de rabbitmq
RABBITMQ_PASSWORD = "XXXXXX" # Cambiar por la contraseña de rabbitmq

OLD_PRODUCER_CREATOR = "test" # Este refiere al creador como en Lab11
OLD_PRODUCER_PRODUCT = "test" # El producto del creador como en Lab11

OLD_WORKER_EDITOR = "lab11" # Este refiere al editor como en el excel

OLD_SERVER_URL = "localhost:8000" # ip:port del servidor de lab11
```
