import sounddevice as sd
import numpy as np

DEVICE = 1
SAMPLE_RATE = 44100

count = 0


def callback(indata, frames, time, status):
	global count

	if status:
		print("Status:", status)

	samples = indata.astype(np.int32)

	peak = int(np.max(np.abs(samples)))
	rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

	if count < 10:
		print(
			f"Chunk {count + 1} | "
			f"Peak: {peak} | RMS: {rms:.2f} | "
			f"Dtype: {indata.dtype}"
		)

	count += 1


print("Testing microphone at native sample rate...")
print("Speak continuously for 5 seconds!")

with sd.InputStream(
	device=DEVICE,
	samplerate=SAMPLE_RATE,
	channels=1,
	dtype="int16",
	blocksize=1024,
	callback=callback,
):
	sd.sleep(5000)

print("\nMicrophone stream test completed.")
