import os
import pika
import json

import pika.channel
import pika.frame


class TasksWorkerRPC():
    def __init__(self) -> None:
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(os.environ.get("RABBITMQ_HOST"),
                                      port=5672,
                                      credentials=pika.PlainCredentials(
                                            os.environ.get("RABBITMQ_USER"),
                                            os.environ.get("RABBITMQ_PASSWORD")
                                      ))
        )
        self.channel = self.connection.channel()
        
        # Declaro la cola de tareas, si no existe la crea y si existe no hace nada
        self.channel.queue_declare(queue="tasks", durable=True)
        
        self.channel.basic_consume(queue="tasks",
                                   on_message_callback=self.onRequest,
                                   auto_ack=False)
        
    def onRequest(self, ch : pika.channel.Channel , method : pika.frame.Method , properties, body):
        print(f"Received {json.loads(body)}")
        task = json.loads(body)
        print(f"Task {task['ID']} completed")
        self.channel.basic_publish(
            exchange="",
            routing_key="callback",
            body=json.dumps({"ID": task["ID"]})
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    def start(self):
        self.channel.start_consuming()
        
        
def start():
    worker = TasksWorkerRPC()
    print("Worker started")
    worker.start()