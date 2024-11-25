import httpx
import os
import pika
import json

import pika.channel
import pika.frame

import time

class TasksProducerRPC:
    def __init__(self):
        
        self.TASKS_QUANTITY = 0
        
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.environ.get("RABBITMQ_HOST"),
                                      port=5672,
                                      credentials=pika.PlainCredentials(
                                            os.environ.get("RABBITMQ_USER"),
                                            os.environ.get("RABBITMQ_PASSWORD")
                                      ),
                                      heartbeat=30,)
        )
        self.channel = self.connection.channel()
        
        # Declaro la cola de tareas, si no existe la crea y si existe no hace nada
        self.channel.queue_declare(queue="tasks", durable=True)
        
        # Seteo la cantidad de tareas que se pueden enviar a un worker,
        # en este caso, un worker solo puede tener una tarea a la vez
        self.channel.basic_qos(prefetch_count=1)
        
        # Declaro la cola de callback, si no existe la crea y si existe no hace nada
        # Sirve para recibir la confirmacion de que la tarea fue completada
        self.channel.queue_declare(queue="callback", exclusive=True)
        
        self.channel.basic_consume(queue="callback",
                                   on_message_callback=self.onResponse,
                                   auto_ack=True)
        
    def onResponse(self, ch : pika.channel , method : pika.frame.Method , properties, body : bytes):
        
        print(type(body))
        
        # skipcq: PTC-W6004
        httpx.post(
            url=f"http://{os.environ.get('OLD_SERVER_URL')}/tasks/submit",
            content= body,
            headers={
                "Content-Type": "application/zip",
                "IdClient" : properties.headers["ID"],
                "product" : os.environ.get("OLD_PRODUCER_PRODUCT")
            }
        )

        print(f"[PRODUCER]   Task {properties.correlation_id} completed")
        
        self.TASKS_QUANTITY -= 1
        
    def send_task(self, task: dict):
        self.channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(task), # Convierto el diccionario a un string JSON
            properties=pika.BasicProperties(
                delivery_mode= pika.DeliveryMode.Persistent,
                content_type="application/json",
                reply_to= "callback", # Nombre de la cola a la que se envia la confirmacion
                correlation_id= task["ID"] # ID de la tarea para identificarla
            )
        )
        print(f"Sent {task['ID']}")
        self.TASKS_QUANTITY += 1
    
    def processDataEvents(self):
        self.connection.process_data_events(time_limit=0)
    
    def wait(self):
        """
        Espera a que todas las tareas sean completadas
        """
        while self.TASKS_QUANTITY > 0:
            self.connection.process_data_events(time_limit=None)

    def close(self):
        self.connection.close()

def waitTwoMinutes(rpc : TasksProducerRPC):
    timeEnd = time.time() + 120
    
    while time.time() < timeEnd:
        
        rpc.processDataEvents()
        

def start():
    
    rpc = TasksProducerRPC()
    
    while True:
        
        print("[PRODUCER]   Querying tasks...")
        
        # Busco las tareas en el servidor viejo
        response = httpx.get(
            f"http://{os.environ.get("OLD_SERVER_URL")}/tasks/search/{os.environ.get("OLD_PRODUCER_PRODUCT")}?editor={os.environ.get('OLD_WORKER_EDITOR').upper()}&offset=10"
            )
            
        tasks = response.json()
        
        if type(tasks) != list:  # noqa: E721
            print("[PRODUCER]   No tasks found, retrying in 2 minutes")
            
            waitTwoMinutes(rpc)
            
            continue
        
        print(f"[PRODUCER]   Found {len(tasks)} tasks")
        
        for task in tasks:
            rpc.send_task(task)
                
        rpc.wait()
        print("[PRODUCER]   All tasks completed, querying again...")
    
    rpc.close()