import asyncio
from googletrans import Translator

async def main():
    gTranslator = Translator()

    task = asyncio.create_task(gTranslator.translate("This is a test", dest = "zh-cn", src="en"))
    await task
    if task.result()._response.is_success:
        print (task._result.text)

asyncio.run(main())