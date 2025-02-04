import asyncio, re
from typing import Dict
from googletrans import Translator

from ...common.config import cfg
from ..entities import LANGUAGES
from ..utils.logger import setup_logger

async def googleTranslate(original_subtitle: Dict[int,str], callback = None):
    glogger = setup_logger("GoogleTranslate")
    glogger.info("===========Google Translate Starts==========")
    gTranslator = Translator()
    # From lanuage
    src = LANGUAGES[cfg.transcribe_language.value.value]
    dest = LANGUAGES[cfg.target_language.value.value]
    
    translate_result = {}
    
    batch_num = 50
    text, i, j  = "", 0, 1
    length = len( original_subtitle )
    translated = ""
        
    for key, value in original_subtitle.items():
        # text += "#" + str(key)+ " " +value +"\n"
        text += value +"\n"
        i += 1
        if i % batch_num == 0 or i >= length:
            # Translate every 50 lines or at the end
            glogger.info(f"Translating up to line {i}")
            try:
                # Doing translate.
                task = asyncio.create_task( gTranslator.translate(text, src=src, dest=dest ))
                await task
                if task.result()._response.is_success:
                    translated += task.result().text + "\n"
                else:
                    raise Exception("Getting error result from Google Translate")
            except Exception as e:
                glogger.error(f"Error doing google translate. {e}")
                return

            chunk = translated.split("\n")
            chunk.pop() # Remove the last empty line
            partial_result = {}
            for value in chunk:
                line: Dict = {str(j): value}
                j += 1
                if callback:
                    callback(line)
                partial_result.update(line) # Add line to partial result
            # Add partial result to total result
            translate_result.update(partial_result)
            # reset the text for next round
            text, translated = "",""
            partial_result.clear()
    
    return translate_result

if __name__ == "__main__":
    test = {1: "This is my testing sentence 1.", 2: "this is my second test sentence"}
    loop = asyncio.get_event_loop()
    task = loop.create_task(googleTranslate(test))
    text = loop.run_until_complete(task)
    print(text)

    