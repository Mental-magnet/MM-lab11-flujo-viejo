import utils.path as path
import os
import anyio
import asyncio

import httpx

class Audio():
    def __init__(self) -> None:
        
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        
        
        # Usamos httpx para hacer las peticiones, no el sdk de elevenlabs,
        # ya que.... habian problemas con httpx dentro de asyncio
        # * https://github.com/encode/httpx/discussions/2959 -> Issue
        self.connection = httpx.AsyncClient(
            base_url= "https://api.elevenlabs.io/v1",
            headers= {
                "Connection" : "close", # * Ultra importante
                "Content-Type" : "application/json",
                "xi-api-key" : self.api_key
            },
            verify= False,
            timeout= httpx.Timeout(
                timeout= None,
            )
        )
        
        self.voice = os.environ.get("ELEVENLABS_VOICE_NAME")
        self.model = os.environ.get("ELEVENLABS_VOICE_MODEL")
        self.stability = os.environ.get("ELEVENLABS_STABILITY")
        self.similarity = os.environ.get("ELEVENLABS_SIMILARITY")
        self.style = os.environ.get("ELEVENLABS_STYLE")
        self.speaker_boost = bool(os.environ.get("ELEVENLABS_SPEAKER_BOOST"))
        self.voiceID = None

    async def getVoices(self):
        """
        Obtiene las voces disponibles
        """
        
        response = await self.connection.get("/voices",
                                           headers= httpx.Headers({
                                               "xi-api-key" : self.api_key,
                                               "Connection" : "close"
                                           }, encoding="utf-8")
                                           )
        
        data = response.json()
        
        for voice in data["voices"]:
            if self.voice.lower() in voice["name"].lower():
                return voice["voice_id"]
            await asyncio.sleep(0)
                                            
        
    async def generateAudio(self, text : str , voiceID : str):
        """
        Genera un archivo de audio a partir de un texto
        
        Args:
            text (str): Texto a convertir en audio
        """
        
        response = await self.connection.post(f"text-to-speech/{voiceID}?output_format=mp3_44100_192",
                                              headers= httpx.Headers({
                                                  "xi-api-key" : self.api_key,
                                                  "Connection" : "close"
                                              }),
                                              json={
                                                  "text" : text,
                                                  "model_id" : self.model,
                                                  "voice_settings" : {
                                                        "stability" : self.stability,
                                                        "similarity_boost" : self.similarity,
                                                        "style" : self.style,
                                                        "use_speaker_boost" : self.speaker_boost
                                                  }
                                              })
        
        audio = response.iter_bytes()
        
        return audio
    
    
    async def saveAudio(self, clientID , obj : dict[str , int | str],  listToSave : list[str] | None = None):
        """
        Guarda un archivo de audio a partir de un texto
        
        Args:
            text (str): Texto a convertir en audio
            path (str): Ruta donde guardar el archivo
        """
        
        if not self.voiceID:
            self.voiceID = await self.getVoices()
        
        print(f"[WORKER][AUDIO]   Voz seleccionada: {self.voiceID}")
        
        audio = await self.generateAudio(obj["text"] , self.voiceID)
        
        print(f"[WORKER][AUDIO]   Audio generado {clientID}({obj['fileID']})")
        
        pathToSave = path.findFile(f"audios/{clientID}({obj['fileID']}).mp3")
        
        async with await anyio.open_file(pathToSave, "wb") as file:
            for chunk in audio:
                await file.write(chunk)
        
        print(f"[WORKER][AUDIO]   Audio guardado en {pathToSave}\n")
        
        if listToSave is not None:
            listToSave.append({
                **obj,
                "path" : pathToSave
            })
            
        return {
            **obj,
            "path" : pathToSave
        }
    
    
if __name__ == "__main__":
    
    import dotenv
    
    dotenv.load_dotenv(".env")
    
    async def main():
        audio = Audio()
    
        async with anyio.create_task_group() as tg:
            tg.start_soon(audio.saveAudio,
                          "test", {
                              "text" : "Hola mundo",
                              "fileID" : 1
                              })
    
    anyio.run(main)