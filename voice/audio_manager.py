import sounddevice as sd


class AudioManager:

    @staticmethod
    def get_devices():

        devices = sd.query_devices()

        microphones = []
        speakers = []

        for index, device in enumerate(devices):

            if device["max_input_channels"] > 0:

                microphones.append({
                    "id": index,
                    "name": device["name"]
                })

            if device["max_output_channels"] > 0:

                speakers.append({
                    "id": index,
                    "name": device["name"]
                })

        return microphones, speakers

    @staticmethod
    def show_devices():

        microphones, speakers = AudioManager.get_devices()

        print("\n===== ZORIN AUDIO DEVICES =====")

        print("\nAVAILABLE MICROPHONES:")

        for mic in microphones:

            print(f"{mic['id']}: {mic['name']}")

        print("\nAVAILABLE SPEAKERS:")

        for speaker in speakers:

            print(f"{speaker['id']}: {speaker['name']}")

        print("\n===============================")

    @staticmethod
    def get_default_devices():

        microphone = sd.default.device[0]
        speaker = sd.default.device[1]

        return microphone, speaker


if __name__ == "__main__":

    AudioManager.show_devices()