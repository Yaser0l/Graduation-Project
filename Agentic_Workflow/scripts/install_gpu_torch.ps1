# Install CUDA-enabled PyTorch + BGE-M3 deps into .venv310 (RTX 20xx / CUDA 12.x)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv310"
$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
    py -3.10 -m venv $Venv
}
& $Py -m pip install -U pip
& $Py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
& $Py -m pip install sentence-transformers
& $Py -c @"
import torch
from sentence_transformers import SentenceTransformer
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    m = SentenceTransformer('BAAI/bge-large-en-v1.5', device='cuda')
    v = m.encode(['smoke test'], normalize_embeddings=True)
    print('BGE-large dim:', len(v[0]), '- GPU embeddings OK')
"@
