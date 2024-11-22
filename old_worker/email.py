from google.oauth2 import service_account
import googleapiclient.discovery as google_discovery
import utils.path as path
import os
# import to decode base64
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
            print("Credentials not found")
            
        print("Credentials found")
        
    def getTextsFromTask(self, taskID : str) -> list[str]:
        """
        Obtiene el texto de un correo con el ID de una tarea dado
        
        Args:
            taskID (str): ID de la tarea
        """
        messages : dict[str , int | list[dict[str , str]] | str] = self.service.users().messages().list(userId="me",
                                                        q=f"subject:{taskID}").execute()
        
        message = self.service.users().messages().get(userId="me",
                                                   id=messages["messages"][0]["id"],
                                                   format="raw").execute()
        
        decodedMessage = base64.urlsafe_b64decode(message["raw"].encode("ASCII")).decode("utf-8")
        
        texts = []
        
        # Encuentra los textos entre llaves o parentesis
        for match in re.findall(r'(?<={|\().*?(?=}|\))', decodedMessage, flags=re.S):
            texts.append(match)
        
        return texts
if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv(".env")
    
    r = Gmail().getTextsFromTask("JXll5r-9643aedb-1ac0-4dac-b5bf-c222b3e9edaa")
    
    print(r)