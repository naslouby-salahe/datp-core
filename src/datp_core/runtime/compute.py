import torch

# Training and scoring run on CPU unconditionally. Every detector in this repository is a
# small reconstruction autoencoder (<40k parameters), so GPU kernel-launch overhead dominates
# compute and the GPU buys nothing while exposing a WSL2 dxgkrnl passthrough host-crash risk.
LEARNING_DEVICE: torch.device = torch.device("cpu")
