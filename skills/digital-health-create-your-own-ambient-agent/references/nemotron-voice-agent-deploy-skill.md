# Nemotron Voice Agent — Deployment Skill Reference

Source: https://github.com/NVIDIA/skills/blob/main/skills/nemotron-voice-agent/nemotron-voice-agent-deploy/SKILL.md

This document summarizes the deployment skill for the NVIDIA Nemotron Voice
Agent. Use it when the developer asks about hardware-specific deployment,
choosing between GPU tiers, or running on Jetson.

---

## Deployment Targets

### Cloud NIMs (No Local GPU)

Suitable when `nvidia-smi` returns no GPU, or the developer wants zero
infrastructure.

1. `git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent`
2. `cd nemotron-voice-agent && git submodule update --init --recursive`
3. `cp config/env.example config/.env`
4. Set `NVIDIA_API_KEY` from https://build.nvidia.com
5. Set `NVIDIA_LLM_MODEL=nvidia/nemotron-3-nano-30b-a3b` (or your chosen model)
6. `docker compose up`
7. Access the Docker-published WebRTC UI at http://<machine-ip>:9000

For WebSocket mode, add `TRANSPORT=WEBSOCKET` to `config/.env` before step 6.
Access the WebSocket UI at http://localhost:7860/static/index.html.

**Multilingual mode** (WebRTC + Workstation only):
Set `ENABLE_MULTILINGUAL=true` and configure `ASR_CLOUD_FUNCTION_ID` and
`ASR_MODEL_NAME` for the multilingual Parakeet model.

---

### Workstation (x86_64, 2× GPU 24 GB+ VRAM)

Requires: Two NVIDIA GPUs with ≥24 GB VRAM each, NIM containers.

See `references/workstation-deployment.md` in the nemotron-voice-agent repo for
the full setup guide including local NIM container startup commands.

Key differences from cloud:
- `ASR_SERVER_URL=localhost:50151` (local Parakeet NIM)
- `TTS_SERVER_URL=localhost:50151` (local Magpie TTS NIM)
- `NVIDIA_LLM_URL=http://localhost:18000/v1` (local Nemotron NIM)

---

### Jetson Thor (aarch64)

Requires: JetPack 7.0, Nemotron Speech ASR/TTS, vLLM.

See `references/jetson-deployment.md` in the nemotron-voice-agent repo.

Key differences:
- Uses Nemotron Speech (not Magpie) for TTS
- LLM served via vLLM on-device

---

## Detection Commands

```bash
# Check for GPU
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Detect architecture
uname -m                              # x86_64 or aarch64

# Detect Jetson
cat /etc/nv_tegra_release 2>/dev/null
```

---

## Integration with the Custom Agent Backend

When combining with a custom `my-custom-ambient-healthcare-agent` backend:

1. The custom agent's `docker-compose.yml` includes the `nemotron-voice-agent`
   service, built from `../nemotron-voice-agent`.
2. Set `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT}/v1` in the
   `nemotron-voice-agent` service environment.
3. All ASR/TTS/port settings from the deployment guides above apply unchanged.
4. The custom agent's Dockerfile and the nemotron-voice-agent Dockerfile are
   built independently; no files from one repo need to be copied into the other.
