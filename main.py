import asyncio

from voice.wake_word import WakeWordDetector
from core.voice_conversation import VoiceConversation


async def main():

    print("\n==============================")
    print("       ZORIN AI ASSISTANT")
    print("==============================")

    wake_detector = WakeWordDetector()

    while True:

        await wake_detector.listen()

        print("\nZORIN IS READY TO TALK!")

        conversation = VoiceConversation()

        await conversation.start()


if __name__ == "__main__":

    asyncio.run(main())