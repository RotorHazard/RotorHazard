#!/usr/bin/env bash
# Build and push all RotorHazard Docker images to Docker Hub.
# Usage: ./build-and-push.sh [OPTIONS]
#
# Options:
#   --no-push     Build only, don't push to Docker Hub
#   --only=NAME   Build only one image (rotorhazard, pi, nuclearpi)
#
# Examples:
#   ./build-and-push.sh                    # Build and push all
#   ./build-and-push.sh --no-push          # Build all without pushing
#   ./build-and-push.sh --only=nuclearpi   # Build and push only NuclearHazard

set -e

# Determine repo root (script can be run from docker/scripts/, docker/, or repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$(basename "$SCRIPT_DIR")" in
    scripts) REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")" ;;
    docker)  REPO_ROOT="$(dirname "$SCRIPT_DIR")" ;;
    *)       REPO_ROOT="$SCRIPT_DIR" ;;
esac

cd "$REPO_ROOT"
echo "Building from: $REPO_ROOT"

# Parse arguments
PUSH=true
ONLY=""

for arg in "$@"; do
    case $arg in
        --no-push)
            PUSH=false
            ;;
        --only=*)
            ONLY="${arg#*=}"
            ;;
    esac
done

# Set up buildx builder if not exists
if ! docker buildx inspect multi >/dev/null 2>&1; then
    echo "Creating buildx builder 'multi'..."
    docker buildx create --use --name multi
else
    docker buildx use multi
fi

# Build flags
if [ "$PUSH" = true ]; then
    PUSH_FLAG="--push"
    echo "Mode: Build and push"
else
    PUSH_FLAG="--load"
    echo "Mode: Build only (no push)"
fi

echo ""

# Image definitions
# Format: name:dockerfile:platforms:tag
# base is built first when pi or nuclearpi is needed (see below).
IMAGES=(
    "rotorhazard:Dockerfile:linux/amd64:racefpv/rotorhazard:latest"
    "pi:Dockerfile.pi:linux/arm64:racefpv/rotorhazard-pi:latest"
    "nuclearpi:Dockerfile.nuclearpi:linux/arm64:racefpv/rotorhazard-nuclearpi:latest"
)

# Build base image when building pi or nuclearpi. Dockerfile.pi and Dockerfile.nuclearpi
# use this as their FROM image. Push: both amd64 and arm64 so Mac/PC devs can pull.
# Load (--no-push): arm64 only so local pi/nuclearpi builds have the base.
build_base_if_needed() {
    local need_pi_or_nuclearpi=false
    if [ -z "$ONLY" ] || [ "$ONLY" = "pi" ] || [ "$ONLY" = "nuclearpi" ]; then
        need_pi_or_nuclearpi=true
    fi
    if [ "$need_pi_or_nuclearpi" = false ]; then
        return 0
    fi
    echo "=============================================="
    echo "Building: base (required for pi/nuclearpi)"
    echo "  Dockerfile: docker/Dockerfile (target: base)"
    if [ "$PUSH" = true ]; then
        echo "  Platform:   linux/amd64, linux/arm64"
    else
        echo "  Platform:   linux/arm64 (load only)"
    fi
    echo "  Tag:        racefpv/rotorhazard:base"
    echo "=============================================="
    if [ "$PUSH" = true ]; then
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            -f docker/Dockerfile \
            --target base \
            -t racefpv/rotorhazard:base \
            --push \
            .
    else
        docker buildx build \
            --platform linux/arm64 \
            -f docker/Dockerfile \
            --target base \
            -t racefpv/rotorhazard:base \
            --load \
            .
    fi
    echo ""
    echo "✓ base complete"
    echo ""
}

build_image() {
    local name="$1"
    local dockerfile="$2"
    local platforms="$3"
    local tag="$4"

    echo "=============================================="
    echo "Building: $name"
    echo "  Dockerfile: docker/$dockerfile"
    echo "  Platform:   $platforms"
    echo "  Tag:        $tag"
    echo "=============================================="

    # For single platform with --load, we can't use --push
    # For multi-platform or --push, use the appropriate flag
    if [ "$PUSH" = true ]; then
        docker buildx build \
            --platform "$platforms" \
            -f "docker/$dockerfile" \
            -t "$tag" \
            --push \
            .
    else
        # --load only works with single platform
        docker buildx build \
            --platform "$platforms" \
            -f "docker/$dockerfile" \
            -t "$tag" \
            --load \
            .
    fi

    echo ""
    echo "✓ $name complete"
    echo ""
}

# Build base first when pi or nuclearpi will be built (they FROM base)
build_base_if_needed

# When building only nuclearpi, build pi first (nuclearpi FROM pi)
if [ "$ONLY" = "nuclearpi" ]; then
    build_image "pi" "Dockerfile.pi" "linux/arm64" "racefpv/rotorhazard-pi:latest"
fi

# Build images
for img in "${IMAGES[@]}"; do
    IFS=':' read -r name dockerfile platforms tag <<< "$img"
    
    # Skip if --only specified and doesn't match
    if [ -n "$ONLY" ] && [ "$ONLY" != "$name" ]; then
        continue
    fi

    build_image "$name" "$dockerfile" "$platforms" "$tag"
done

echo "=============================================="
echo "All builds complete!"
echo ""
echo "Images:"
echo "  racefpv/rotorhazard:base           (amd64 + arm64, base for pi/nuclearpi)"
echo "  racefpv/rotorhazard:latest         (amd64)"
echo "  racefpv/rotorhazard-pi:latest      (arm64)"
echo "  racefpv/rotorhazard-nuclearpi:latest (arm64)"
if [ "$PUSH" = true ]; then
    echo ""
    echo "All images pushed to Docker Hub."
fi
echo "=============================================="
