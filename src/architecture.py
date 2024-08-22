import torch
import torch.nn as nn
from utils.helpers import N_CHANNELS, N_FRAMES, N_FREQ_BINS
from torch.nn.utils import spectral_norm

# Constants Constants
BATCH_SIZE = 16
LATENT_DIM = 100
N_EPOCHS = 10

VALIDATION_INTERVAL = int(N_EPOCHS / 2)
SAVE_INTERVAL = int(N_EPOCHS / 1)


# Model Components
class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.deconv_blocks = nn.Sequential(
            nn.ConvTranspose2d(LATENT_DIM, 256, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(32, 16, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(16, 8, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(8, 4, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(4),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(4, N_CHANNELS, kernel_size=4, stride=2, padding=1),
            nn.Upsample(
                size=(N_FRAMES, N_FREQ_BINS), mode="bilinear", align_corners=False
            ),
            nn.Tanh(),
        )

    def forward(self, z):
        x = self.deconv_blocks(z)
        return x


class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        self.conv_blocks = nn.Sequential(
            nn.Upsample(size=(256, 256), mode="bilinear", align_corners=False),
            spectral_norm(nn.Conv2d(N_CHANNELS, 4, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(4, 8, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(8),
            spectral_norm(nn.Conv2d(8, 16, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(16),
            spectral_norm(nn.Conv2d(16, 32, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(32),
            spectral_norm(nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(64),
            spectral_norm(nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(128),
            spectral_norm(nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(256),
            nn.Conv2d(256, 1, kernel_size=4, stride=2, padding=1),
            nn.Flatten(),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = self.conv_blocks(x)
        return x
