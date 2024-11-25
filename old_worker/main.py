import json
import os

import pika
import pika.channel
import pika.frame

import dtos.worker_task_dto
import old_worker.audio as audio
import old_worker.email as email
import old_worker.whisp as whisp
import utils.path as path

import shutil

import functools

import anyio

import dtos.worker_task_dto as DTOS

class TasksWorkerRPC():
    def __init__(self) -> None:
        print("[WORKER]   Empezando...")
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
        print("[WORKER]   Queue 'tasks' declarado\n")
        
        # Seteo la cantidad de tareas que se pueden enviar a un worker,
        self.channel.basic_qos(prefetch_count=1)
        
        self.channel.basic_consume(queue="tasks",
                                   on_message_callback=TasksWorkerRPC.wrapperSync(self.onRequest),
                                   auto_ack=False)
        print("[WORKER]   basic_consume declarado\n")
        
        self.emailService = email.Gmail()
        print("[WORKER]   Email service declarado\n")
        
        self.audioService = audio.Audio()
        print("[WORKER]   Audio service declarado\n")
        
        self.whispService = whisp.Whisp()
        print("[WORKER]   Whisp service declarado\n")
        
        self.generations = []
    
    @staticmethod
    def wrapperSync(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return anyio.run(f, *args, **kwargs)
        
        return wrapper
            
    
    async def onRequest(self, ch : pika.channel.Channel , method : pika.frame.Method , properties, body : bytes | str):
        """
        Funcion que se ejecuta cuando se recibe una tarea
        
        Args:
            ch (pika.channel.Channel): Canal de comunicacion
            method (pika.frame.Method): Metodo
            properties ([type]): Propiedades
            body (bytes): Cuerpo del mensaje
        """
        
        data : DTOS.TaskDTO = json.loads(body)
        
        print(f"[WORKER]   Recibido {data}\n")
        
        processedData = await self.processALL(data) # Procesamos la tarea
        
        print(f"[WORKER]   ZIP generado {processedData}\n")
        
        
        self.connection.process_data_events(time_limit=0)
        with open(processedData , "rb") as file:
            self.channel.basic_publish(
                exchange="",
                routing_key="callback",
                properties=pika.BasicProperties(
                    delivery_mode= pika.DeliveryMode.Persistent,
                    content_type="application/zip", # Tipo de contenido
                    headers= {
                        "ID" : data["ID"],
                    }
                    ),
                body=file.read()
            )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        print(f"[WORKER]   Enviado {processedData}\n")
        
        shutil.rmtree(path.findFile("audios")) # Borramos la carpeta audios
        
        os.mkdir(path.findFile("audios")) # Creamos la carpeta audios
        
        os.unlink(processedData) # Borramos el archivo ZIP
        
        self.connection.process_data_events(time_limit=0)
    
    def whispSomething(self , generations : list[str]) -> list[dict[str , str | int]]:
        """
        Ejecutamos el servicio de whisper para cada generacion
        """
        print("[WORKER]   Whispering...\n")
        
        whispResults = []
        
        for obj in generations:
            result = self.whispService.whisperThis(
                                                   obj["path"],
                                                   obj["text"]
                                                   )

            if result["ratio"] < 90:
                raise Exception(f"El ratio de coincidencia es menor a 90: {result}")
            
            self.connection.process_data_events(time_limit=0) # Para evitar que se cierre la conexion
            
            whispResults.append(result)
        
        print("[WORKER]   Todos los audios guardados\n")
        
        return whispResults
    
    @staticmethod
    def zipIt(ID : str):
        """
        Comprime los archivos de audio
        """
        archive = shutil.make_archive(base_name=ID,
                            format="zip",
                            root_dir=path.findFile("audios"))
        
        return archive
    
    async def processALL(self, body : dict[str , str | int]):
        
        texts = self.emailService.getTextsFromTask(body["ID"],
                                                   body["EMAIL"])
        
        self.connection.process_data_events(time_limit=0)
        
        toGenerate = [{"id" : i + 1,
                       "fileID" : f"{(i+1) // 10}{(i + 1) % 10}",
                       "text" : text} 
                       for i , text in enumerate(texts[:-1])]
        
        self.generations = []
        
        async with anyio.create_task_group() as tg:
            
            for obj in toGenerate:
                tg.start_soon(self.audioService.saveAudio , body["ID"] , obj , self.generations)
        
        generationsOrdered = sorted(self.generations , key=lambda x: x["id"])
        
        self.whispSomething(generationsOrdered)
        
        archive = TasksWorkerRPC.zipIt(body["ID"])
        
        self.emailService.markAsFinished(texts[-1]["emailID"])

        print(f"[WORKER]   ZIP generado {archive}\n")
        
        return archive
    
        
        
    def start(self):
        print("[WORKER]   Worker funcionando\n")
        self.channel.start_consuming()
        
        
def start():
    worker = TasksWorkerRPC()
    print("Worker started")
    worker.start()
    
