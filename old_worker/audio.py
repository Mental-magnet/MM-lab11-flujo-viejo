import utils.path as path
import os
import elevenlabs
import anyio

class Audio():
    def __init__(self) -> None:
        self.elevenlabs = elevenlabs.AsyncElevenLabs(
            api_key= os.environ.get("ELEVENLABS_API_KEY"),
        )
        
        self.voice = os.environ.get("ELEVENLABS_VOICE_NAME")
        self.model = os.environ.get("ELEVENLABS_VOICE_MODEL")
        self.stability = os.environ.get("ELEVENLABS_STABILITY")
        self.similarity = os.environ.get("ELEVENLABS_SIMILARITY")
        self.style = os.environ.get("ELEVENLABS_STYLE")
        self.speaker_boost = bool(os.environ.get("ELEVENLABS_SPEAKER_BOOST"))
    
    
    async def getVoices(self):
        """
        Obtiene las voces disponibles
        """
        
        voices = await self.elevenlabs.voices.get_all()
        
        for voice in voices.voices:
            if self.voice.lower() in voice.name.lower():
                return voice.voice_id
            anyio.sleep(0)
        
                                            
        
    async def generateAudio(self, text : str , voiceID : str):
        """
        Genera un archivo de audio a partir de un texto
        
        Args:
            text (str): Texto a convertir en audio
        """
        audio = await self.elevenlabs.generate(
            text = text,
            voice= voiceID,
            model= self.model,
            stream= False,
            output_format= "mp3_44100_192",
            voice_settings= elevenlabs.VoiceSettings(
                stability= self.stability,
                similarity_boost= self.similarity,
                style= self.style,
                use_speaker_boost= self.speaker_boost
            )
        )
        
        return audio
    
    async def saveAudio(self, clientID , obj : dict[str , int | str],  listToSave : list[str] | None = None):
        """
        Guarda un archivo de audio a partir de un texto
        
        Args:
            text (str): Texto a convertir en audio
            path (str): Ruta donde guardar el archivo
        """
        voiceID = await self.getVoices()
        
        print(f"[WORKER]   Voz seleccionada: {voiceID}")
        
        audio = await self.generateAudio(obj["text"] , voiceID)
        
        print(f"[WORKER]   Audio generado {clientID}({obj['fileID']})")
        
        pathToSave = path.findFile(f"audios/{clientID}({obj['fileID']}).mp3")
        
        async with await anyio.open_file(pathToSave, "wb") as file:
            async for chunk in audio:
                await file.write(chunk)
        
        print(f"[WORKER]   Audio guardado en {pathToSave}\n")
        
        if listToSave is not None:
            listToSave.append({
                **obj,
                "path" : pathToSave
            })
            
        return pathToSave
    
    
if __name__ == "__main__":
    
    import dotenv
    
    dotenv.load_dotenv(".env")
    
    async def main():
        audio = Audio()
    
        async with anyio.create_task_group() as tg:
            tg.start_soon(audio.saveAudio , "test" , "00" , "Hola, este es un mensaje de prueba")
    
    anyio.run(main)