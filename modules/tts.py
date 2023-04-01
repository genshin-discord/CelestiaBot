from gtts import gTTS
from googletrans import Translator
from io import BytesIO


class TTS:
    def __init__(self):
        self.t = Translator()

    @classmethod
    async def create(cls):
        return cls()

    async def speak(self, text):
        try:
            lang = self.t.detect(text)
            lang = lang.lang
        except Exception as e:
            lang = 'en'
        g = gTTS(text, lang=lang)
        b = BytesIO()
        g.write_to_fp(b)
        b.seek(0)
        return b

# import asyncio
# async def test():
#     t = await TTS.create()
#     b = await t.speak('你不行')
#     with open('test.mp3', 'wb') as f:
#         f.write(b.read())
#
#
# asyncio.run(test())
