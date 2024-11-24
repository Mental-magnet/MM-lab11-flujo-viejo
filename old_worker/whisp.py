import fuzzywuzzy.fuzz
import whisper
import os
import utils.path as path
import fuzzywuzzy

class Whisp():
    def __init__(self):
        self.whisperModel = whisper.load_model(
            name= os.environ.get("WHISPER_MODEL"),
            download_root= path.findFile("whisper"),
            in_memory= False
        )

    
    async def whisperThis(self , audioPath : str , originalText : str) -> int:
        """
        Transcribe un audio a partir de un texto
        Y compara el texto con el texto original
        """
        
        transcription = whisper.transcribe(
            model= self.whisperModel,
            audio=whisper.load_audio(audioPath)
        )
        
        modifiedOriginalText = originalText.lower().replace("\r\n" , " ").replace("." , "").replace("-" , "").replace("," , "")
        modifiedTranscriptionText = transcription["text"].lower().replace("\r\n" , " ").replace("." , "").replace("-" , "").replace("," , "")
        
        ratio = fuzzywuzzy.fuzz.WRatio(modifiedOriginalText , modifiedTranscriptionText)
        
        print(f"[WORKER][WHISP]   Transcripción completada | {modifiedOriginalText} -> {modifiedTranscriptionText} | Ratio: {ratio}\n")
        
        return {
            "original" : originalText,
            "transcription" : transcription["text"],
            "ratio" : ratio
        }