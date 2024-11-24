from google.oauth2 import service_account
import googleapiclient.discovery as google_discovery
import utils.path as path
import os
import base64
import re
class Gmail():
    def __init__(self) -> None:
        self.credentials = Gmail.generateCredentials()
        
        # Delega las credenciales a otro usuario, ej: xxxx@xxxxx.xx
        credentials_delegated = self.credentials.with_subject(os.environ.get("GMAIL_IMPERSONATE_EMAIL"))
        
        self.service = google_discovery.build("gmail",
                                              "v1",
                                              credentials=credentials_delegated
                                              )
    
    @staticmethod
    def generateCredentials() -> service_account.Credentials:
        """
        Crea las credenciales para acceder a la API de Gmail
        """
        
        key_path = path.findFile("secrets/emailBot.json")
        API_scopes =['https://www.googleapis.com/auth/gmail.settings.basic',
                     "https://www.googleapis.com/auth/gmail.insert",
                     "https://www.googleapis.com/auth/gmail.modify"
                    ]
        credentials = service_account.Credentials.from_service_account_file(key_path,
                                                                            scopes=API_scopes,
                                                                            )
        return credentials
    
    @staticmethod
    def testCredentials():
        credentials = Gmail.generateCredentials()
        
        if not credentials:
            print("[WORKER][GMAIL]   Credentials not found\n")
            
        print("[WORKER][GMAIL]   Credentials found\n")
    
    @staticmethod
    def handleMultipart(message : dict[str , str]) -> str:
        """
        Maneja un mensaje multipart
        
        Args:
            message (dict[str , str]): Mensaje a manejar
        """
        
        for part in message["parts"]:
            if part["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    
    @staticmethod
    def parseDecodedMessage(decodedMessage : str) -> str:
        texts = []
        
        # Encuentra los textos entre llaves o parentesis
        for match in re.findall(r'(?<={|\().*?(?=}|\))', decodedMessage, flags=re.S):
            texts.append(match)
            
        return texts
         
    def getTextsFromTask(self, taskID : str , taskMail : str) -> list[str]:
        """
        Obtiene el texto de un correo con el ID de una tarea dado
        
        Args:
            taskID (str): ID de la tarea
            taskMail (str): Correo de la tarea
        """
        messages : dict[str , int | list[dict[str , str]] | str] = self.service.users().messages().list(
                                                        userId="me",
                                                        q=f"subject:{taskID} AND subject:{taskMail} newer_than:7d AND NOT label:En-Proceso OR label:Finalizado",
                                                        ).execute()
        
        if len(messages["messages"]) > 1:
            raise Exception(f"El mensaje {taskID} tiene mas de un mensaje")
        
        message = self.service.users().messages().get(userId="me",
                                                   id=messages["messages"][0]["id"]).execute()
        
        
        print(f"[WORKER][GMAIL]   MimeType del mensaje: {message['payload']['mimeType']}\n")
        
        
        if not message["payload"]["mimeType"] in ["text/plain", "text/html"]:  # noqa: E713
            
            if message["payload"]["mimeType"] == "multipart/alternative":
                decodedMessage = Gmail.handleMultipart(message["payload"])
                texts = Gmail.parseDecodedMessage(decodedMessage)
                
                return texts
                
            
            raise Exception(f"El mensaje {taskID} no es de tipo texto plano")
            
            
        decodedMessage = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")
        
        texts = Gmail.parseDecodedMessage(decodedMessage)
        
        return texts
if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv(".env")
    
    r = Gmail().getTextsFromTask("testxd" , "americabelen2440@gmail.com")
    
    print(r)