#!/bin/bash
echo "Installing Node.js via NVM..."
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

echo "Installing Frontend Dependencies and Building..."
cd frontend
npm install
npm install react-router-dom lucide-react
npm run build
cd ..

echo "Installing Backend Dependencies..."
pip install -r requirements.txt

echo "Building C++ Builder Engine..."
cd engine
curl -L -o json.hpp https://github.com/nlohmann/json/releases/download/v3.11.2/json.hpp
make
cd ..

echo "Setup Complete!"
