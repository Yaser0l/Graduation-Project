#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=false
TARGETS=()

usage() {
    echo "Usage: $0 [--dry-run] [--all] [TARGETS...]"
    echo ""
    echo "Clean build artifacts, dependencies, caches, and data volumes."
    echo ""
    echo "Options:"
    echo "  --dry-run    Show what would be deleted without deleting"
    echo "  --all        Clean everything"
    echo ""
    echo "Targets:"
    echo "  python       venvs, __pycache__, *.pyc, .pytest_cache, .mypy_cache, .tox, .eggs, *.egg-info"
    echo "  node         node_modules/"
    echo "  build        build/, dist/"
    echo "  data         postgres_data/, mosquitto_data/, mosquitto_log/, chroma_db/"
    echo "  output       Agentic_Workflow/output/"
    echo "  logs         *.log, npm-debug.log*, yarn-*.log*"
    echo "  all          Everything above"
}

clean_one() {
    local path="$1"
    if [[ -e "$path" ]]; then
        if $DRY_RUN; then
            echo "  [dry-run] would remove: $path"
        else
            rm -rf "$path"
            echo "  removed: $path"
        fi
    fi
}

clean_dirs() {
    local name="$1"
    while IFS= read -r -d '' p; do
        clean_one "$p"
    done < <(find "$ROOT" \
        -not \( -path '*/node_modules/*' -prune \) \
        -not \( -path '*/.venv/*' -prune \) \
        -not \( -path '*/venv/*' -prune \) \
        -not \( -path '*/env/*' -prune \) \
        -name "$name" -prune -print0 2>/dev/null || true)
}

clean_files() {
    local name="$1"
    while IFS= read -r -d '' p; do
        clean_one "$p"
    done < <(find "$ROOT" \
        -not \( -path '*/node_modules/*' -prune \) \
        -not \( -path '*/.venv/*' -prune \) \
        -not \( -path '*/venv/*' -prune \) \
        -not \( -path '*/env/*' -prune \) \
        -name "$name" -print0 2>/dev/null || true)
}

# ── Parsing ──────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --all) TARGETS+=(python node build data output logs) ;;
        python|node|build|data|output|logs) TARGETS+=("$arg") ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown: $arg"; usage; exit 1 ;;
    esac
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    usage
    exit 1
fi

if $DRY_RUN; then
    echo "=== DRY RUN (nothing will be deleted) ==="
fi

for target in "${TARGETS[@]}"; do
    echo "--- $target ---"

    case "$target" in
        python)
            clean_dirs '__pycache__'
            clean_files '*.pyc'
            clean_dirs '.venv*'
            clean_dirs 'venv'
            clean_dirs 'env'
            clean_dirs '.Python'
            clean_dirs '.pytest_cache'
            clean_dirs '.mypy_cache'
            clean_dirs '.tox'
            clean_dirs '.eggs'
            clean_dirs '*.egg-info'
            clean_dirs 'coverage'
            clean_dirs 'htmlcov'
            clean_files '.coverage'
            ;;

        node)
            clean_dirs 'node_modules'
            ;;

        build)
            clean_dirs 'build'
            clean_dirs 'dist'
            ;;

        data)
            clean_one "$ROOT/postgres_data"
            clean_one "$ROOT/mosquitto_data"
            clean_one "$ROOT/mosquitto_log"
            clean_dirs 'chroma_db'
            ;;

        output)
            clean_one "$ROOT/Agentic_Workflow/output"
            ;;

        logs)
            clean_files '*.log'
            clean_files 'npm-debug.log*'
            clean_files 'yarn-debug.log*'
            clean_files 'yarn-error.log*'
            ;;
    esac
done

echo "Done."
