#!/usr/bin/env bash
# Build (and optionally push) RotorHazard Docker images.
# Usage: ./build-and-push.sh [OPTIONS]
#
# Options:
#   --push        Push images after building (default is build-only, so the script works without registry access)
#   --only=NAME   Build only one image (rotorhazard, pi, nuclearpi)
#
# Environment:
#   IMAGE_PREFIX  Registry/namespace for image tags (e.g. myuser or myorg/rotorhazard).
#                 Unset = local tags only (rotorhazard:latest, etc.). Set when pushing to your registry.
#
# Examples:
#   ./build-and-push.sh                      # Build all, load locally (no push)
#   ./build-and-push.sh --push                # Build and push (requires IMAGE_PREFIX and registry login)
#   IMAGE_PREFIX=myuser ./build-and-push.sh --push
#   ./build-and-push.sh --only=nuclearpi      # Build only NuclearHazard image

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

# Parse arguments (default: build only, no push — safe for contributors without registry access)
PUSH=false
ONLY=""

for arg in "$@"; do
    case $arg in
        --push)
            PUSH=true
            ;;
        --only=*)
            ONLY="${arg#*=}"
            ;;
    esac
done

# Image tags: use IMAGE_PREFIX if set (e.g. myuser/rotorhazard:latest), else local tags (rotorhazard:latest)
if [ -n "${IMAGE_PREFIX:-}" ]; then
    BASE_TAG="${IMAGE_PREFIX}/rotorhazard:base"
    RH_TAG="${IMAGE_PREFIX}/rotorhazard:latest"
    PI_TAG="${IMAGE_PREFIX}/rotorhazard-pi:latest"
    NUCLEARPI_TAG="${IMAGE_PREFIX}/rotorhazard-nuclearpi:latest"
else
    BASE_TAG="rotorhazard:base"
    RH_TAG="rotorhazard:latest"
    PI_TAG="rotorhazard-pi:latest"
    NUCLEARPI_TAG="rotorhazard-nuclearpi:latest"
fi

# Builder: for local builds (no push) use the default/docker driver so the base image
# we build is visible to the next build (pi/nuclearpi FROM base). The container driver
# can't see host-loaded images, so FROM would try to pull from Docker Hub and fail.
if [ "$PUSH" = true ]; then
    if ! docker buildx inspect multi >/dev/null 2>&1; then
        echo "Creating buildx builder 'multi'..."
        docker buildx create --use --name multi
    else
        docker buildx use multi
    fi
else
    docker buildx use default 2>/dev/null || true
fi

# For local builds, use host architecture so we don't cross-compile (avoids "exec format error").
# When pushing, we use the fixed platforms per image (amd64 for default, arm64 for pi/nuclearpi).
case "$(uname -m)" in
    x86_64|amd64)  HOST_PLATFORM="linux/amd64" ;;
    aarch64|arm64) HOST_PLATFORM="linux/arm64" ;;
    *)             HOST_PLATFORM="linux/amd64" ;;
esac

# Build flags
if [ "$PUSH" = true ]; then
    PUSH_FLAG="--push"
    echo "Mode: Build and push"
    if [ -z "${IMAGE_PREFIX:-}" ]; then
        echo "Note: IMAGE_PREFIX is unset; pushing with local-style tags (e.g. rotorhazard:latest). Set IMAGE_PREFIX for a registry (e.g. myuser)."
    fi
else
    PUSH_FLAG="--load"
    echo "Mode: Build only (no push)"
fi
echo ""

# Image definitions: name:dockerfile:platforms:tag (base is built first when pi/nuclearpi needed)
IMAGES=(
    "rotorhazard:Dockerfile:linux/amd64:${RH_TAG}"
    "pi:Dockerfile.pi:linux/arm64:${PI_TAG}"
    "nuclearpi:Dockerfile.nuclearpi:linux/arm64:${NUCLEARPI_TAG}"
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
        echo "  Platform:   $HOST_PLATFORM (host, load only)"
    fi
    echo "  Tag:        $BASE_TAG"
    echo "=============================================="
    if [ "$PUSH" = true ]; then
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            -f docker/Dockerfile \
            --target base \
            -t "$BASE_TAG" \
            --push \
            .
    else
        docker buildx build \
            --platform "$HOST_PLATFORM" \
            -f docker/Dockerfile \
            --target base \
            -t "$BASE_TAG" \
            --load \
            .
    fi
    echo ""
    echo "✓ base complete"
    echo ""
}

# Optional build-args for FROM in child images (pi needs BASE_IMAGE, nuclearpi needs PI_IMAGE)
get_build_args() {
    local name="$1"
    case "$name" in
        pi)        echo "--build-arg" "BASE_IMAGE=$BASE_TAG" ;;
        nuclearpi) echo "--build-arg" "PI_IMAGE=$PI_TAG" ;;
        *)         ;;
    esac
}

build_image() {
    local name="$1"
    local dockerfile="$2"
    local platforms="$3"
    local tag="$4"
    local extra_args=()
    read -ra extra_args <<< "$(get_build_args "$name")"

    echo "=============================================="
    echo "Building: $name"
    echo "  Dockerfile: docker/$dockerfile"
    echo "  Platform:   $platforms"
    echo "  Tag:        $tag"
    echo "=============================================="

    if [ "$PUSH" = true ]; then
        docker buildx build \
            --platform "$platforms" \
            -f "docker/$dockerfile" \
            "${extra_args[@]}" \
            -t "$tag" \
            --push \
            .
    else
        docker buildx build \
            --platform "$platforms" \
            -f "docker/$dockerfile" \
            "${extra_args[@]}" \
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
    _platforms="$([ "$PUSH" = true ] && echo "linux/arm64" || echo "$HOST_PLATFORM")"
    build_image "pi" "Dockerfile.pi" "$_platforms" "$PI_TAG"
fi

# Build images
for img in "${IMAGES[@]}"; do
    IFS=':' read -r name dockerfile platforms tag <<< "$img"
    # Local build: use host platform so we don't cross-compile (avoids exec format error)
    [ "$PUSH" = false ] && platforms="$HOST_PLATFORM"

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
echo "  $BASE_TAG"
echo "  $RH_TAG"
echo "  $PI_TAG"
echo "  $NUCLEARPI_TAG"
if [ "$PUSH" = true ]; then
    echo ""
    echo "Images pushed to registry."
fi
echo "=============================================="
