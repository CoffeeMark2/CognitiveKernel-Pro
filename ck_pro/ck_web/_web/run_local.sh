#!/bin/bash
set -e
cd "$(dirname "$0")"

# use these to run it locally without docker

# apt-get install npm
# --
#package.json:
#{
#    "name": "playwright-express-app",
#    "version": "1.0.0",
#    "description": "A simple Express server to navigate and interact with web pages using Playwright.",
#    "main": "server.js",
#    "scripts": {
#      "start": "node server.js"
#    },
#    "keywords": [
#      "express",
#      "playwright",
#      "automation"
#    ],
#    "author": "",
#    "license": "ISC",
#    "dependencies": {
#      "express": "^4.17.1",
#      "playwright": "^1.28.1"
#    }
#}
# --
# npm install
# --
# update node.js according to "https://nodejs.org/en/download/package-manager"
# installs fnm (Fast Node Manager)
# curl -fsSL https://fnm.vercel.app/install | bash

# # activate fnm
# source ~/.bashrc

# # download and install Node.js
# fnm use --install-if-missing 22

# # verifies the right Node.js version is in the environment
# node -v # should print `v22.11.0`

# # verifies the right npm version is in the environment
# npm -v # should print `10.9.0`
# --- 新的、更可靠的 Node.js 安装方式 ---
echo ">>> 正在配置 Node.js v22 安装源..."
apt-get update
apt-get install -y ca-certificates curl gnupg
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

NODE_MAJOR=22
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

echo ">>> 正在安装 Node.js v22..."
apt-get update
apt-get remove -y libnode-dev nodejs npm  # 移除冲突包和所有相关旧包
apt-get autoremove -y                    # 自动清理所有不再需要的依赖，确保环境干净
# --- 大扫除结束 ---

apt-get install -y nodejs # <--- 现在安装，道路已经畅通无阻

echo ">>> 安装完成，检查版本："
node -v
npm -v

# --- Node.js 安装完成 ---
# --
npx playwright install
npx playwright install-deps
npm install uuid
npm install js-yaml
npm install playwright-extra puppeteer-extra-plugin-stealth
npm install async-mutex

# --
# simply run it with

npm start
