---
name: "riva-nim-setup"
license: "Apache-2.0"
description: "Use when getting started with NVIDIA Riva Speech NIMs: NGC access, Docker login for nvcr.io, NVIDIA Container Toolkit, GPU verification, Riva Python client."
metadata:
  author: "Mayank Jain <mayjain@nvidia.com>"
  team: riva
  tags:
    - nvidia
    - riva
    - nim
    - setup
    - ngc
    - docker
    - prerequisites
  domain: ml
  version: "1.0.0"
---

# Riva NIM Setup

> **Agent:** Announce each step before presenting it: **Step N/7 — Step Title** (e.g., "**Step 1/7 — Install NVIDIA Drivers**").

## Purpose

A first-pass machine preparation: bring a Linux x86_64 host up to the point where it can pull and execute Riva Speech NIM containers. The work below is one-time per host.

## Prerequisites

Up-to-date GPU compatibility, minimum driver versions, VRAM thresholds, and supported operating systems are all maintained at https://docs.nvidia.com/nim/speech/latest/get-started/prerequisites.html — consult that page before installing anything.

A few invariants worth knowing without clicking through:
- The host CPU must be x86_64; ARM is not supported.
- Self-hosting Riva NIMs requires an active NVIDIA AI Enterprise license.
- Install the **driver alone** — the CUDA toolkit ships inside the NIM container, so installing it separately at the host level is redundant (and a common source of version-skew bugs).

## Instructions

The setup is seven sequential steps. The first three need root or `sudo`; the remaining four can run as your normal user. Knock them off in order; don't try to pull a NIM container before Step 7 is done.

| # | What | Why it's first |
|---|---|---|
| 1 | NVIDIA driver (no CUDA toolkit) | The host has to be able to talk to the GPU at all |
| 2 | Docker Engine | Container runtime |
| 3 | NVIDIA Container Toolkit | Bridges Docker to the GPU |
| 4 | NGC API key | Auth artifact for pulling images |
| 5 | `docker login nvcr.io` | Activates the key against the registry |
| 6 | `nvidia-riva-client` (pip) | Lets you exercise the running NIM from Python |
| 7 | (optional) clone client sample repos | Source for the example scripts |


## Step 1 — Install NVIDIA Drivers

Use your distro's package manager to install the driver only. Don't add the CUDA toolkit at the host level — the NIM container ships with its own bundled CUDA stack.

```bash
# Verify installed driver version
nvidia-smi
```

Cross-check the version `nvidia-smi` prints against the per-model minimum at https://docs.nvidia.com/nim/speech/latest/get-started/prerequisites.html before continuing. If you do need a fresh install, the [CUDA installation guide for Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux) walks through the distro-specific package manager steps (you'll only follow the driver portion, not the toolkit portion).

## Step 2 — Install Docker

Pick the Docker Engine flavor for your distribution from the official matrix: https://docs.docker.com/engine/install/

Once installed, add your user to the `docker` group so subsequent commands don't need `sudo`:

```bash
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

## Step 3 — Install NVIDIA Container Toolkit

The Container Toolkit lets Docker containers access the host GPU. Full reference: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

```bash
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Smoke-test that a container can actually see the GPU:

```bash
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

A successful run prints the same driver version and GPU listing you'd see on the host. If you get an error or empty output, something in Steps 1–3 didn't take — revisit before moving on.

## Step 4 — NGC API Key

Three short steps to generate a key and load it into your shell:

1. Navigate to https://org.ngc.nvidia.com/setup/api-keys in a browser.
2. Click **Generate API Key** and grant it at least the **NGC Catalog** service scope.
3. Copy the key value and export it:

```bash
export NGC_API_KEY=${your-key-value}
```

To persist across sessions:

```bash
# Bash
echo "export NGC_API_KEY=${your-key-value}" >> ~/.bashrc

# Zsh
echo "export NGC_API_KEY=${your-key-value}" >> ~/.zshrc
```
> **Security note:** Storing credentials in `~/.bashrc` or `~/.zshrc` saves
> them in plaintext. Any process with read access to those files can extract the
> key. For production, use a credential manager or a dedicated `.env` file with
> `chmod 600` permissions and `source` it instead.


## Step 5 — Docker Login to nvcr.io

```bash
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
```

Two non-obvious points often missed:

- The `--username` argument is the literal four-character string `$oauthtoken`. It is **not** your NGC display name or email — copy it verbatim.
- The actual credential is the API key from Step 4, piped to stdin.

A successful login unlocks every `docker pull nvcr.io/nim/nvidia/<image>:<tag>` invocation.

## Step 6 — Install Riva Python Client

The example client scripts in `python-clients/` depend on the `nvidia-riva-client` package — install it now:

```bash
pip install nvidia-riva-client
```

Confirm the install:

```bash
python3 -c "import riva.client; print('Riva client OK')"
```

## Step 7 — Clone Client Repos (Optional)

Open-source sample scripts live in three public repos; clone whichever match the protocol you'll exercise:

```bash
# Python clients and sample scripts
git clone https://github.com/nvidia-riva/python-clients

# C++ clients (requires Bazel)
git clone https://github.com/nvidia-riva/cpp-clients

# WebSocket bridge (AudioCodes / telephony)
git clone https://github.com/nvidia-riva/websocket-bridge
```

## Examples

Three quick sanity checks anyone can rerun later to confirm the environment hasn't drifted.

**After Step 3 — container-level GPU visibility:**
```bash
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

**After Step 6 — Python client import test:**
```bash
python3 -c "import riva.client; print('Riva client OK')"
```

**Step 5 reproduced — re-authenticate against `nvcr.io` after a key rotation:**
```bash
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
```


## Troubleshooting

- **`docker login` fails authentication** → the `--username` value must be the literal `$oauthtoken` string. Many users instinctively type their NGC email or display name here; that's the most common cause of 401 on this step.
- **CUDA library version mismatches at container start** → check that you didn't install the CUDA toolkit at the host level. The NIM container ships its own toolkit; a parallel host install will fight it.
- **`docker run` still wants sudo after `usermod -aG docker`** → group membership only applies to new login sessions. Log out and back in (or open a new shell with `newgrp docker`) and the membership takes effect.
- **`nvidia-container-cli` reports `version: GLIBC_X.YY not found`** → host glibc is older than what the NIM expects. Confirm via `ld -v` against the minimum listed at https://docs.nvidia.com/nim/speech/latest/get-started/prerequisites.html — older Ubuntu LTS releases may need an upgrade.
- **Running inside WSL2 on Windows** → swap Docker for Podman, ensure your NVIDIA driver is ≥ 570, use Ubuntu 24.04 inside WSL, and note that only specific Parakeet models are currently supported under WSL2.


## Limitations

- Host architecture is x86_64 only. WSL2 on Windows is a partially supported path with Podman replacing Docker and a narrower model catalog (Parakeet subset).
- Self-hosting a Riva NIM is gated behind an active NVIDIA AI Enterprise license.
- The host should not carry a separate CUDA toolkit install — the NIM container brings the toolkit it expects. Parallel installs at the host level are a frequent source of breakage.
- Adding a user to the `docker` group requires re-logging in before that user can run Docker commands without `sudo`.

## Next Steps

Once Steps 1–7 are green, route to the deployment skill that matches the modality you want:

- **Model choice undecided** → `riva-model-selection`
- **Speech-to-text deployments** → `riva-asr`
- **Text-to-speech deployments** → `riva-tts`
- **Translation deployments** → `riva-nmt`

