import sounddevice as sd
import numpy as np
import time

count = 0

def callback(indata, frames, time_info, status):
    global count

    samples = indata.astype(np.int32)
    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

    if count % 10 == 0:
        print(f"Peak: {peak} | RMS: {rms:.2f}")

    count += 1

print("\nGET READY!")
time.sleep(3)

print("\nSPEAK NOW! YOU HAVE 15 SECONDS!\n")

with sd.InputStream(
    device=1,
    samplerate=44100,
    channels=2,
    dtype="int16",
    blocksize=1024,
    callback=callback
):
    sd.sleep(15000)

print("\nTEST COMPLETED!")
