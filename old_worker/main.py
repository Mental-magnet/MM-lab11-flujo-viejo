import json
import os

import anyio
import pika
import pika.channel
import pika.frame

import old_worker.audio as audio
import old_worker.email as email
import old_worker.whisp as whisp


class TasksWorkerRPC():
    def __init__(self) -> None:
        print("[WORKER]   Starting...")
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(os.environ.get("RABBITMQ_HOST"),
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
        print("[WORKER]   Queue 'tasks' declared\n")
        
        # Seteo la cantidad de tareas que se pueden enviar a un worker,
        self.channel.basic_qos(prefetch_size=0,prefetch_count=1)
        
        self.channel.basic_consume(queue="tasks",
                                   on_message_callback=self.onRequest,
                                   auto_ack=False)
        print("[WORKER]   basic_consume declared\n")
        
        self.emailService = email.Gmail()
        print("[WORKER]   Email service declared\n")
        
        self.audioService = audio.Audio()
        print("[WORKER]   Audio service declared\n")
        
        self.whispService = whisp.Whisp()
        print("[WORKER]   Whisp service declared\n")
        
        
        self.generations : list[str] = []
        self.whispResults : list[dict] = []
        
    def onRequest(self, ch : pika.channel.Channel , method : pika.frame.Method , properties, body : bytes):
        """
        Funcion que se ejecuta cuando se recibe una tarea
        
        Args:
            ch (pika.channel.Channel): Canal de comunicacion
            method (pika.frame.Method): Metodo
            properties ([type]): Propiedades
            body (bytes): Cuerpo del mensaje
        """
        
        data = json.loads(body)
        
        print(f"[WORKER]   Received {data}\n")
        
        processedData = anyio.run(self.asyncOnRequest,  data)
        
        print(f"[WORKER]   Processed {processedData}\n")
        
        self.channel.basic_publish(
            exchange="",
            routing_key="callback",
            body=json.dumps(processedData)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        self.generations = []
        
        print(f"[WORKER]   Sent {processedData}\n")
    
    async def whispSomething(self , generations : list[str]) -> None:
        """
        Whisper something
        """
        print("[WORKER]   Whispering...\n")
        
        for obj in generations:
            result = await self.whispService.whisperThis(
                                                   obj["path"],
                                                   obj["text"]
                                                   )

            if result["ratio"] < 90:
                result["path"] = obj["path"]
                
                raise Exception(f"El ratio de coincidencia es menor a 90: {result}")
            
            self.connection.process_data_events(time_limit=0)
            
            self.whispResults.append(result)
            
        print(self.whispResults)
        print("[WORKER]   All audios saved\n")
    
    async def asyncOnRequest(self, body : dict[str , str | int]):
        
        texts = self.emailService.getTextsFromTask(body["ID"] , body["EMAIL"])
        
        toGenerate = [{"id" : i + 1,
                       "fileID" : f"{(i+1) // 10}{(i + 1) % 10}",
                       "text" : text} 
                       for i , text in enumerate(texts)]
        
        async with anyio.create_task_group() as tg:
            
            for obj in toGenerate:
                tg.start_soon(self.audioService.saveAudio , body["ID"] , obj , self.generations)
        
        async with anyio.create_task_group() as tg:
            generationsOrdered = sorted(self.generations , key=lambda x: x["id"])
        
            tg.start_soon(self.whispSomething , generationsOrdered)

        return body
        
    def start(self):
        print("[WORKER]   Worker started\n")
        self.channel.start_consuming()
        
        
def start():
    worker = TasksWorkerRPC()
    print("Worker started")
    worker.start()
    
