#!/bin/bash
set -e

echo "Creating Lambda Layer for TEN VAD model..."

# Create layer directory structure
LAYER_DIR="lambda_layer"
rm -rf $LAYER_DIR
mkdir -p $LAYER_DIR/python/lib/python3.11/site-packages
mkdir -p $LAYER_DIR/model

# Install Python dependencies (LIGHTWEIGHT - no librosa!)
echo "Installing onnxruntime and numpy for Lambda Python 3.11..."
pip install \
    onnxruntime==1.16.3 \
    numpy==1.24.3 \
    -t $LAYER_DIR/python \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade

# Copy Silero VAD model
echo "Copying Silero VAD model..."
cp ../../model/silero_vad.onnx $LAYER_DIR/model/

# Create zip file
echo "Creating layer zip..."
cd $LAYER_DIR
zip -r ../ten-vad-layer.zip . -q
cd ..

echo "✓ Lambda layer created: ten-vad-layer.zip"
echo "  Size: $(du -h ten-vad-layer.zip | cut -f1)"
echo ""
echo "Next step: Deploy stack with updated CDK code"
