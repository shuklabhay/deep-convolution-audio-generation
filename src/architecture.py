import torch
import torch.nn as nn
from utils.helpers import N_CHANNELS, N_FRAMES, N_FREQ_BINS
import torch.nn.functional as F
from torch.nn.utils import spectral_norm

# Constants Constants
BATCH_SIZE = 16
LATENT_DIM = 128
N_EPOCHS = 10

VALIDATION_INTERVAL = int(N_EPOCHS / 2)
SAVE_INTERVAL = int(N_EPOCHS / 1)


# Model Components
class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.conv_transpose_blocks = nn.Sequential(
            nn.ConvTranspose2d(LATENT_DIM, 256, kernel_size=4, stride=1, padding=0),
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
        x = self.conv_transpose_blocks(z)
        return x


class SelfAttention(nn.Module):
    def __init__(self, in_channels):
        super(SelfAttention, self).__init__()
        self.query = spectral_norm(nn.Conv2d(in_channels, in_channels // 8, 1))
        self.key = spectral_norm(nn.Conv2d(in_channels, in_channels // 8, 1))
        self.value = spectral_norm(nn.Conv2d(in_channels, in_channels, 1))
        self.gamma = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        batch_size, C, width, height = x.size()
        proj_query = self.query(x).view(batch_size, -1, width * height).permute(0, 2, 1)
        proj_key = self.key(x).view(batch_size, -1, width * height)
        energy = torch.bmm(proj_query, proj_key)
        attention = F.softmax(energy, dim=-1)
        proj_value = self.value(x).view(batch_size, -1, width * height)
        out = torch.bmm(proj_value, attention.permute(0, 2, 1))
        out = out.view(batch_size, C, width, height)
        out = self.gamma * out + x
        return out


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
            SelfAttention(8),
            spectral_norm(nn.Conv2d(8, 16, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(16),
            SelfAttention(16),
            spectral_norm(nn.Conv2d(16, 32, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(32),
            SelfAttention(32),
            spectral_norm(nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(64),
            SelfAttention(64),
            spectral_norm(nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(128),
            SelfAttention(128),
            spectral_norm(nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.BatchNorm2d(256),
            SelfAttention(256),
            nn.Conv2d(256, 1, kernel_size=4, stride=2, padding=1),
            nn.Flatten(),
            nn.Sigmoid(),
        )

    def get_features(self, x):
        features = []
        for layer in self.conv_blocks:
            x = layer(x)
            features.append(x)
        return features

    def add_noise(self, x, noise_factor=0.1):
        noise = torch.randn_like(x) * noise_factor
        return x + noise

    def forward(self, x):
        x = self.conv_blocks(x)
        return x
