import torch
import torch.nn.functional as F
from architecture import LATENT_DIM
from utils.helpers import (
    graph_spectrogram,
    save_model,
    scale_data_to_range,
)

# Constants
N_EPOCHS = 2
VALIDATION_INTERVAL = int(N_EPOCHS / N_EPOCHS)
SAVE_INTERVAL = int(N_EPOCHS / 1)


# Train Utility
def smooth_labels(tensor):
    amount = 0.02

    if tensor[0] == 1:
        return tensor + amount * torch.rand_like(tensor)
    else:
        return tensor - amount * torch.rand_like(tensor)


# Generator Loss Metrics
# Feature matching
# Spectral centroid
# Spectral rolloff
# Global sample diversity


# Discriminator Loss Metrics
def calculate_spectral_diff(real_audio_data, fake_audio_data):
    spectral_diff = torch.mean(torch.abs(real_audio_data - fake_audio_data))

    return torch.mean(spectral_diff)


def calculate_spectral_convergence(real_audio_data, fake_audio_data):
    return torch.norm(fake_audio_data - real_audio_data, p=2) / (
        torch.norm(real_audio_data, p=2) + 1e-8
    )


def compute_discrim_loss(
    criterion,
    discriminator,
    real_audio_data,
    fake_audio_data,
    real_labels,
    fake_labels,
):
    # Adv Loss
    real_loss = criterion(discriminator(real_audio_data).view(-1, 1), real_labels)
    fake_loss = criterion(discriminator(fake_audio_data).view(-1, 1), fake_labels)
    d_adv_loss = (real_loss + fake_loss) / 2

    # Extra metrics
    spectral_diff = 0.2 * calculate_spectral_diff(real_audio_data, fake_audio_data)
    spectral_convergence = 0.1 * calculate_spectral_convergence(
        real_audio_data, fake_audio_data
    )

    d_loss = d_adv_loss + spectral_diff + spectral_convergence
    return d_loss


# Training
def train_epoch(
    generator,
    discriminator,
    dataloader,
    criterion,
    optimizer_G,
    optimizer_D,
    scheduler_G,
    scheduler_D,
    training_audio_data,
    device,
):
    generator.train()
    discriminator.train()
    total_g_loss, total_d_loss = 0, 0

    for i, (real_audio_data,) in enumerate(dataloader):
        batch_size = real_audio_data.size(0)
        real_audio_data = real_audio_data.to(device)

        real_labels = smooth_labels((torch.ones(batch_size, 1)).to(device))
        fake_labels = smooth_labels((torch.zeros(batch_size, 1)).to(device))

        # Train generator
        optimizer_G.zero_grad()
        z = torch.randn(batch_size, LATENT_DIM, 1, 1).to(device)
        fake_audio_data = generator(z)

        # Generator Loss
        g_adv_loss = criterion(discriminator(fake_audio_data).view(-1, 1), real_labels)

        g_loss = g_adv_loss

        g_loss.backward(retain_graph=True)
        optimizer_G.step()
        scheduler_G.step()
        total_g_loss += g_loss.item()

        # Train discriminator
        optimizer_D.zero_grad()
        fake_audio_data = fake_audio_data.detach()
        d_loss = compute_discrim_loss(
            criterion,
            discriminator,
            real_audio_data,
            fake_audio_data,
            real_labels,
            fake_labels,
        )

        d_loss.backward()
        optimizer_D.step()
        scheduler_D.step()
        total_d_loss += d_loss.item()

    return total_g_loss / len(dataloader), total_d_loss / len(dataloader)


def validate(generator, discriminator, dataloader, criterion, device):
    generator.eval()
    discriminator.eval()
    total_g_loss, total_d_loss = 0, 0

    with torch.no_grad():
        for (real_audio_data,) in dataloader:
            batch_size = real_audio_data.size(0)
            real_audio_data = real_audio_data.to(device)

            real_labels = torch.ones(batch_size, 1).to(device)
            fake_labels = torch.zeros(batch_size, 1).to(device)

            z = torch.randn(batch_size, LATENT_DIM, 1, 1).to(device)
            fake_audio_data = generator(z)

            g_loss = criterion(discriminator(fake_audio_data), real_labels)
            total_g_loss += g_loss.item()
            d_loss = compute_discrim_loss(
                criterion,
                discriminator,
                real_audio_data,
                fake_audio_data,
                real_labels,
                fake_labels,
            )
            total_d_loss += d_loss.item()

    return total_g_loss / len(dataloader), total_d_loss / len(dataloader)


def training_loop(
    generator,
    discriminator,
    train_loader,
    val_loader,
    criterion,
    optimizer_G,
    optimizer_D,
    scheduler_G,
    scheduler_D,
    training_audio_data,
    device,
):
    for epoch in range(N_EPOCHS):
        train_g_loss, train_d_loss = train_epoch(
            generator,
            discriminator,
            train_loader,
            criterion,
            optimizer_G,
            optimizer_D,
            scheduler_G,
            scheduler_D,
            training_audio_data,
            device,
        )

        print(
            f"[{epoch+1}/{N_EPOCHS}] Train - G Loss: {train_g_loss:.6f}, D Loss: {train_d_loss:.6f}"
        )

        # Validate periodically
        if (epoch + 1) % VALIDATION_INTERVAL == 0:
            val_g_loss, val_d_loss = validate(
                generator, discriminator, val_loader, criterion, device
            )
            print(
                f"------ Val ------ G Loss: {val_g_loss:.6f}, D Loss: {val_d_loss:.6f}"
            )

            examples_to_generate = 3
            z = torch.randn(examples_to_generate, LATENT_DIM, 1, 1).to(device)
            generated_audio = generator(z).squeeze()
            for i in range(examples_to_generate):
                generated_audio_np = generated_audio[i].cpu().detach().numpy()
                graph_spectrogram(
                    scale_data_to_range(generated_audio_np, -120, 40),
                    f"Generated Audio {i + 1} epoch {epoch + 1}",
                )

        # Save models periodically
        if (epoch + 1) % SAVE_INTERVAL == 0:
            save_model(generator, "DCGAN")
