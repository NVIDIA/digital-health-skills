---
name: "riva-asr-custom"
license: "Apache-2.0"
description: "Use when the user wants to deploy a custom-trained ASR model as a Riva NIM, or convert a NeMo model via nemo2riva / riva-build / riva-deploy / RMIR."
metadata:
  author: "Mayank Jain <mayjain@nvidia.com>"
  team: riva
  tags:
    - nvidia
    - riva
    - nim
    - asr
    - custom-model
    - nemo2riva
    - riva-build
    - riva-deploy
    - rmir
    - fine-tuning
  domain: ml
  version: "1.0.0"
---

# Riva ASR Custom Model Deployment

> **Agent:** Announce each phase before presenting it: **Phase N/4 — Phase Title** (e.g., "**Phase 1/4 — Obtain a .riva File**").

## Purpose

Deploy a custom NeMo-trained ASR model as a Riva NIM when pre-built NIMs do not meet accuracy requirements or need domain-specific vocabulary.

## Prerequisites

- Complete `riva-nim-setup`: NVIDIA Container Toolkit, `NGC_API_KEY` exported (driver minimum: see prerequisites page)
- A trained NeMo model checkpoint (`.nemo` file)
- `nemo2riva` PyPI package (installed on host, not inside container)

## Instructions

1. **Phase 1**: Obtain a `.riva` file (download from NGC or convert `.nemo` via `nemo2riva`).
2. **Phase 2**: Build an RMIR with `riva-build` (run inside the NIM container).
3. **Phase 3**: Deploy the model repository with `riva-deploy`.
4. **Phase 4**: Launch the custom NIM and run inference.

Run `riva-build` and `riva-deploy` inside the NIM container (enter with `--entrypoint /bin/bash`). All paths like `/riva_build_deploy/` refer to the mounted directory inside the container.

## Phase 1 — Obtain a `.riva` File

Two sources:

**Option A — Download a pre-built artifact from NGC** (recommended if you haven't fine-tuned):

```bash
ngc registry model download-version \
  nim/nvidia/<model-name>_finetune:<version> \
  --dest /path/to/artifacts/
```

Use `deployable_vX.Y` versions — these contain the `.riva` file ready for `riva-build`. `trainable_vX.Y` versions are for NeMo fine-tuning, not deployment.

See `riva-pipelines` → NGC Model Artifacts for the full table of available models and versions.

**Option B — Export your own NeMo checkpoint**:

```bash
pip install nemo2riva
nemo2riva --out /path/to/artifacts/model.riva /path/to/model.nemo

# With encryption key (optional):
nemo2riva --out /path/to/artifacts/model.riva \
  --key <encryption_key> \
  /path/to/model.nemo
```

Refer to the [nemo2riva README](https://github.com/nvidia-riva/nemo2riva) for architecture-specific export options.

---

## Phase 2 — Build RMIR with `riva-build`

Run `riva-build` inside the NIM container. This creates the RMIR (Riva Model Intermediate Representation) file.

```bash
# Set the container image matching the model type you're deploying
export CONTAINER_ID=parakeet-1-1b-ctc-en-us   # use the base NIM that matches your model arch
export NIM_EXPORT_PATH=~/nim_export
export ARTIFACT_DIR=/path/to/artifacts         # directory containing your .riva file

mkdir -p $NIM_EXPORT_PATH && chmod 700 $NIM_EXPORT_PATH

# Launch interactive shell inside the NIM container
docker run --gpus all -it --rm \
  -v $ARTIFACT_DIR:/riva_build_deploy \
  -v $NIM_EXPORT_PATH:/model_tar \
  --entrypoint="/bin/bash" \
  --name riva-build-deploy \
  nvcr.io/nim/nvidia/$CONTAINER_ID:latest
```

Inside the container, run `riva-build`:

```bash
# Basic speech recognition pipeline
riva-build speech_recognition \
  /riva_build_deploy/custom_model.rmir \
  /riva_build_deploy/model.riva

# With encryption key
riva-build speech_recognition \
  /riva_build_deploy/custom_model.rmir:<encryption_key> \
  /riva_build_deploy/model.riva:<encryption_key>

# Force overwrite if .rmir already exists
riva-build speech_recognition -f \
  /riva_build_deploy/custom_model.rmir \
  /riva_build_deploy/model.riva
```

Available `<pipeline>` values:
- `speech_recognition` — ASR transcription pipeline
- `punctuation` — punctuation restoration

For pipeline configuration options (streaming, offline, VAD, language model, etc.), see `riva-pipelines`.

---

## Phase 3 — Deploy Model Repository with `riva-deploy`

Still inside the container (or re-enter it), run `riva-deploy` to build the Triton model repository:

```bash
riva-deploy /riva_build_deploy/custom_model.rmir /data/models

# Force overwrite
riva-deploy -f /riva_build_deploy/custom_model.rmir /data/models
```

**Important:** Always deploy to `/data/models` inside the container. Deploying elsewhere requires manual path fixes in Triton config files.

After deploy completes, create the tar archive:

```bash
cd /data/models
tar -czf /model_tar/custom_model.tar.gz *
```

Exit and remove the container:

```bash
exit
docker stop riva-build-deploy 2>/dev/null; docker rm riva-build-deploy 2>/dev/null
```

Your `custom_model.tar.gz` is now in `$NIM_EXPORT_PATH` on the host.

---

## Phase 4 — Launch the Custom NIM

```bash
docker run -it --rm --name=$CONTAINER_ID \
  --runtime=nvidia \
  --gpus '"device=0"' \
  --shm-size=8GB \
  -e NGC_API_KEY \
  -e NIM_TAGS_SELECTOR \
  -e NIM_DISABLE_MODEL_DOWNLOAD=true \
  -e NIM_HTTP_API_PORT=9000 \
  -e NIM_GRPC_API_PORT=50051 \
  -p 9000:9000 \
  -p 50051:50051 \
  -v $NIM_EXPORT_PATH:/opt/nim/export \
  -e NIM_EXPORT_PATH=/opt/nim/export \
  nvcr.io/nim/nvidia/$CONTAINER_ID:latest
```
> **Security note:** Environment variables passed via `-e` to Docker are visible
> in `docker inspect` output and process listings. For production, use Docker
> secrets or a secrets manager instead of passing credentials as env vars.


`NIM_DISABLE_MODEL_DOWNLOAD=true` prevents the container from downloading pre-trained models from NGC and uses the custom repository from `NIM_EXPORT_PATH` instead.

## Verify Readiness

```bash
curl -X GET http://localhost:9000/v1/health/ready
# Expected: {"status":"ready"}
```

## Run Inference on the Custom Model

```bash
python3 python-clients/scripts/asr/transcribe_file_offline.py \
  --server 0.0.0.0:50051 \
  --input-file /path/to/audio.wav \
  --language-code en-US
```

---

## Examples

These are variations on the canonical phase commands above; for the standard flow follow Phases 1–4 directly.

**Export an encrypted `.riva` from NeMo (Phase 1, Option B variant):**
```bash
nemo2riva --out /artifacts/model.riva --key my-secret /path/to/model.nemo
```

**Build a punctuation pipeline instead of speech recognition (Phase 2 variant):**
```bash
riva-build punctuation \
  /riva_build_deploy/punct_model.rmir \
  /riva_build_deploy/punct_model.riva
```

**Re-deploy after editing `.rmir` (Phase 3 variant — force overwrite):**
```bash
riva-deploy -f /riva_build_deploy/custom_model.rmir /data/models
```


## Troubleshooting

- **Match container to model architecture** — use the NIM container image that matches your model family (e.g., `parakeet-1-1b-ctc-en-us` for CTC Parakeet-based models).
- **Deploy to `/data/models` only** — other paths break Triton config references without manual edits.
- **`NIM_DISABLE_MODEL_DOWNLOAD=true` is required** — without it, the container ignores the custom model and downloads the default pre-trained model.
- **Encryption key consistency** — if you used an encryption key in `nemo2riva`, use the same key in `riva-build` and `riva-deploy`.
- **`-f` flag for rebuilds** — `riva-build` and `riva-deploy` skip existing files by default; add `-f` to force a rebuild.
- **Phase 3 runs on target GPU** — `riva-deploy` optimizes TensorRT engines for the deployment GPU; run it on the same GPU class you'll use in production.
- **nemo2riva vs. architecture** — not all NeMo model architectures are supported by every NIM image; check the nemo2riva README for compatibility.


## Limitations

- x86_64 architecture only — `nemo2riva` and the NIM container must run on the same architecture
- NVIDIA AI Enterprise license required for self-hosting
- `nemo2riva` compatibility is version-locked to the NeMo training version — check compatibility before converting

## Next Steps

- Configure pipeline details (VAD, diarization, language model, streaming): see `riva-pipelines`
- Check system requirements: see `riva-ops`

