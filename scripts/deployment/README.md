# Deployment Scripts

This directory contains scripts for deploying the Industry AI Flow system to various environments.

## Available Scripts

### `build_data_analysis_docker.sh`
Builds Docker images for the data analysis components of the system.

**Usage:**
```bash
./build_data_analysis_docker.sh
```

**Prerequisites:**
- Docker installed and running
- Sufficient disk space for Docker images

## Environment Variables

- `DOCKER_REGISTRY`: Docker registry URL (optional)
- `IMAGE_TAG`: Tag for Docker images (default: latest)

## Deployment Environments

- **Development**: Local development setup
- **Staging**: Pre-production testing environment
- **Production**: Production deployment

## Security Notes

- Ensure sensitive configuration is properly managed
- Use environment variables for secrets
- Follow Docker security best practices