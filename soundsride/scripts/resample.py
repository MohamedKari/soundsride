import torchaudio
from pydub import AudioSegment
import numpy as np
import matplotlib.pyplot as plt
import torch

import time

path = "/Users/mo/code/soundsride-internal/tests/data/underground.mp3"

segment = AudioSegment.from_mp3(path)
waveform = (np.array(segment.get_array_of_samples())[::segment.channels] / 255).astype(np.float32)
tensor = torch.tensor(waveform)

# tensor, sample_rate = torchaudio.load(path)

def plot_tensor(tensor: torch.Tensor):
    plt.plot((tensor * 255).type(torch.int16).numpy().flatten())
    plt.show()

print("loaded")

start = time.time()
# must be float32 and mono in order to be fast (otherwise factor 20 slower!)
resampled = torchaudio.transforms.Resample(44100.0, 20.0, 'sinc_interpolation')(tensor)
duration = time.time() - start
print("took", duration)

plot_tensor(resampled)



